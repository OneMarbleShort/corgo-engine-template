import json
import os
import subprocess
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from . import __version__
from .core import ProjectManagerError
from .core import ProjectManagerService
from .launcher import LaunchProjectManager


def FormatProjectManagerTitle(workspaceRootName: str, selectedProjectName: str = "", selectedGameName: str = "") -> str:
    _titleParts = [f"CorgoEngine v{__version__}", workspaceRootName]
    if selectedProjectName:
        _titleParts.append(selectedProjectName)
    if selectedGameName:
        _titleParts.append(selectedGameName)
    return " - ".join(_titleParts)


class InlineRenameInput(TextInput):
    def __init__(
        self,
        initialName: str,
        onCommit: Callable[[str, str], None],
        onError: Callable[[str], None],
        onDoubleTapAction: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(
            text=initialName,
            multiline=False,
            readonly=True,
            size_hint_x=0.64,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(0.94, 0.94, 0.94, 1),
            **kwargs,
        )
        self._onCommit = onCommit
        self._onError = onError
        self._onDoubleTapAction = onDoubleTapAction
        self._originalText = initialName
        self.bind(focus=self._OnFocusChanged)
        self.bind(on_text_validate=self._OnTextValidate)

    def on_touch_down(self, touch):
        _handled = super().on_touch_down(touch)
        if self.collide_point(*touch.pos) and getattr(touch, "is_double_tap", False):
            if self._onDoubleTapAction is not None and "shift" not in Window.modifiers:
                Clock.schedule_once(lambda _dt: self._onDoubleTapAction(), 0)
                return True
            Clock.schedule_once(self._BeginRename, 0)
            return True
        return _handled

    def _BeginRename(self, _dt: float) -> None:
        self.readonly = False
        self.focus = True
        self.select_all()

    def _OnTextValidate(self, _instance):
        self._CommitRename()

    def _OnFocusChanged(self, _instance, isFocused: bool):
        if not isFocused and not self.readonly:
            self._CommitRename()

    def _CommitRename(self) -> None:
        self.readonly = True
        _newText = self.text.strip()
        if not _newText or _newText == self._originalText:
            self.text = self._originalText
            return

        try:
            self._onCommit(self._originalText, _newText)
            self._originalText = _newText
            self.text = _newText
        except Exception as _error:
            self.text = self._originalText
            self._onError(str(_error))


class ItemRow(BoxLayout):
    def __init__(
        self,
        itemName: str,
        onPlay: Callable[[], None],
        onCopy: Callable[[], None],
        onDelete: Callable[[], None],
        onRename: Callable[[str, str], None],
        onError: Callable[[str], None],
        onNameDoubleTapAction: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(6), **kwargs)

        self._nameInput = InlineRenameInput(itemName, onRename, onError, onNameDoubleTapAction)
        self.add_widget(self._nameInput)

        self._playButton = Button(
            text=">",
            size_hint_x=0.12,
            background_normal="",
            background_color=(0.2, 0.52, 0.84, 1),
            color=(1, 1, 1, 1),
        )
        self._copyButton = Button(
            text="Copy",
            size_hint_x=0.14,
            background_normal="",
            background_color=(0.35, 0.35, 0.35, 1),
            color=(1, 1, 1, 1),
        )
        self._deleteButton = Button(
            text="X",
            size_hint_x=0.1,
            background_normal="",
            background_color=(0.76, 0.27, 0.27, 1),
            color=(1, 1, 1, 1),
        )

        self._playButton.bind(on_press=lambda _instance: onPlay())
        self._copyButton.bind(on_press=lambda _instance: onCopy())
        self._deleteButton.bind(on_press=lambda _instance: onDelete())

        self.add_widget(self._playButton)
        self.add_widget(self._copyButton)
        self.add_widget(self._deleteButton)


class ProjectManagerLayout(BoxLayout):
    def __init__(self, service: ProjectManagerService, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), padding=dp(8), **kwargs)
        self._bootstrapService = service
        self._workspaceRoot = service._workspaceRoot
        self._configPath = service._configPath

        self._selectedProjectName = service._paths.projectRoot.name
        self._selectedGameName = ""
        self._isBusy = False
        self._missingProjectPromptShown = False
        self._missingGamePromptShown = False
        self._missingScenesPromptKey = ""
        self._buildButton: Optional[Button] = None
        self._runButton: Optional[Button] = None
        self._buildRunButton: Optional[Button] = None
        self._progressPopup: Optional[Popup] = None

        self._BuildUi()
        self._RefreshProjects()

        if self._ShouldRunPostCloneBootstrap():
            Clock.schedule_once(lambda _dt: self._StartPostCloneBootstrap(), 0)

    def _SetTitle(self, selectedProjectName: str = "", selectedGameName: str = "") -> None:
        _titleText = FormatProjectManagerTitle(self._workspaceRoot.name, selectedProjectName, selectedGameName)
        self._titleLabel.text = _titleText

        _app = App.get_running_app()
        if _app is not None:
            _app.title = _titleText

    def _BuildUi(self) -> None:
        self._titleLabel = Label(
            text=FormatProjectManagerTitle(self._workspaceRoot.name),
            size_hint_y=None,
            height=dp(40),
            bold=True,
            color=(0.96, 0.96, 0.96, 1),
        )
        self.add_widget(self._titleLabel)

        self._buildPlanLabel = Label(
            text="Build plan: select a project and game.",
            size_hint_y=None,
            height=dp(44),
            color=(0.84, 0.84, 0.84, 1),
            halign="left",
            valign="middle",
            text_size=(Window.width - dp(16), dp(44)),
        )
        self._buildPlanLabel.bind(size=self._OnBuildPlanLabelSize)
        self.add_widget(self._buildPlanLabel)

        self._screenManager = ScreenManager()
        self.add_widget(self._screenManager)

        self._statusLabel = Label(
            text="",
            size_hint_y=None,
            height=dp(28),
            color=(0.92, 0.92, 0.92, 1),
        )
        self.add_widget(self._statusLabel)

        self._outputText = TextInput(
            text="",
            readonly=True,
            multiline=True,
            size_hint_y=None,
            height=dp(150),
            background_color=(0.08, 0.08, 0.08, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
            cursor_blink=False,
        )
        self.add_widget(self._outputText)

        self._projectListContainer = self._CreateListScreen("projects", "Projects", self._OnAddProject)
        self._gameListContainer = self._CreateListScreen("games", "Games", self._OnAddGame)
        self._sceneListContainer = self._CreateListScreen("scenes", "Scenes", self._OnAddScene)

    def _CreateListScreen(
        self,
        screenName: str,
        headingText: str,
        onAdd: Callable[[], None],
    ) -> BoxLayout:
        _screen = Screen(name=screenName)
        _root = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))

        _heading = Label(text=headingText, size_hint_y=None, height=dp(28), color=(0.95, 0.95, 0.95, 1))
        _root.add_widget(_heading)

        _scroll = ScrollView()
        _list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4), padding=(0, dp(2)))
        _list.bind(minimum_height=_list.setter("height"))
        _scroll.add_widget(_list)
        _root.add_widget(_scroll)

        _buttonsRow = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        _addButton = Button(
            text="Add",
            background_normal="",
            background_color=(0.23, 0.62, 0.35, 1),
            color=(1, 1, 1, 1),
        )
        _addButton.bind(on_press=lambda _instance: onAdd())
        _buttonsRow.add_widget(_addButton)

        if screenName == "projects":
            _cloneRepoButton = Button(
                text="Clone Repo",
                background_normal="",
                background_color=(0.2, 0.52, 0.84, 1),
                color=(1, 1, 1, 1),
            )
            _cloneRepoButton.bind(on_press=lambda _instance: self._OnCloneWorkspace())
            _buttonsRow.add_widget(_cloneRepoButton)

        if screenName != "projects":
            _backButton = Button(
                text="Back",
                background_normal="",
                background_color=(0.33, 0.33, 0.33, 1),
                color=(1, 1, 1, 1),
            )
            _backButton.bind(on_press=lambda _instance: self._GoBack(screenName))
            _buttonsRow.add_widget(_backButton)

        if screenName == "scenes":
            _buildButton = Button(
                text="Build",
                background_normal="",
                background_color=(0.2, 0.52, 0.84, 1),
                color=(1, 1, 1, 1),
            )
            _runButton = Button(
                text="Run",
                background_normal="",
                background_color=(0.23, 0.62, 0.35, 1),
                color=(1, 1, 1, 1),
            )
            _buildRunButton = Button(
                text="Build + Run",
                background_normal="",
                background_color=(0.82, 0.55, 0.2, 1),
                color=(1, 1, 1, 1),
            )
            self._buildButton = _buildButton
            self._runButton = _runButton
            self._buildRunButton = _buildRunButton
            _buildButton.bind(on_press=lambda _instance: self._StartBuildSelectedGame())
            _runButton.bind(on_press=lambda _instance: self._StartRunSelectedGame())
            _buildRunButton.bind(on_press=lambda _instance: self._StartBuildAndRunSelectedGame())
            _buttonsRow.add_widget(_buildButton)
            _buttonsRow.add_widget(_runButton)
            _buttonsRow.add_widget(_buildRunButton)

        _root.add_widget(_buttonsRow)
        _screen.add_widget(_root)
        self._screenManager.add_widget(_screen)
        return _list

    def _OnBuildPlanLabelSize(self, _instance, _size) -> None:
        self._buildPlanLabel.text_size = (self._buildPlanLabel.width, self._buildPlanLabel.height)

    def _GoBack(self, currentScreen: str) -> None:
        if currentScreen == "scenes":
            self._SwitchScreen("games", isForward=False)
            self._UpdateTitleForGames()
            return

        self._SwitchScreen("projects", isForward=False)
        self._titleLabel.text = "CorgoEngine"

    def _SwitchScreen(self, screenName: str, isForward: bool) -> None:
        _direction = "left" if isForward else "right"
        if hasattr(self._screenManager.transition, "direction"):
            self._screenManager.transition.direction = _direction
        self._screenManager.current = screenName

    def _SetStatus(self, messageText: str) -> None:
        self._statusLabel.text = messageText

    def _SetStatusAsync(self, messageText: str) -> None:
        Clock.schedule_once(lambda _dt: self._SetStatus(messageText), 0)

    def _AppendOutput(self, messageText: str) -> None:
        _existing = self._outputText.text
        _append = messageText.strip()
        if not _append:
            return
        self._outputText.text = f"{_existing}\n{_append}\n" if _existing else f"{_append}\n"
        self._outputText.cursor = (0, len(self._outputText._lines))

    def _AppendOutputAsync(self, messageText: str) -> None:
        Clock.schedule_once(lambda _dt: self._AppendOutput(messageText), 0)

    def _SetButtonEnabled(self, button: Optional[Button], isEnabled: bool) -> None:
        if button is None:
            return
        button.disabled = not isEnabled
        button.opacity = 1.0 if isEnabled else 0.45

    def _StartBackgroundAction(self, worker: Callable[[], None], busyMessageText: str = "") -> None:
        if self._isBusy:
            self._SetStatus("Action already in progress.")
            return
        self._isBusy = True
        if busyMessageText:
            self._ShowProgressPopup(busyMessageText)
        self._UpdateActionButtonsState()

        def _RunWorker() -> None:
            try:
                worker()
            finally:
                Clock.schedule_once(lambda _dt: self._FinishBackgroundAction(), 0)

        threading.Thread(target=_RunWorker, daemon=True).start()

    def _ShouldRunPostCloneBootstrap(self) -> bool:
        return str(os.environ.get("CORGO_POST_CLONE_BOOTSTRAP", "")).strip() == "1"

    def _StartPostCloneBootstrap(self) -> None:
        self._StartBackgroundAction(self._RunPostCloneBootstrap)

    def _FormatCommandForOutput(self, commandArray: list[str]) -> str:
        _formattedPartsArray = []
        for _item in commandArray:
            _text = str(_item)
            if " " in _text:
                _formattedPartsArray.append(f'"{_text}"')
            else:
                _formattedPartsArray.append(_text)
        return " ".join(_formattedPartsArray)

    def _RunCommandWithOutput(self, commandArray: list[str], cwdPath: Path, failureTitle: str) -> None:
        self._AppendOutputAsync(f"$ {self._FormatCommandForOutput(commandArray)}")
        _result = subprocess.run(
            commandArray,
            cwd=str(cwdPath),
            capture_output=True,
            text=True,
            check=False,
        )

        if _result.stdout:
            self._AppendOutputAsync(_result.stdout)
        if _result.stderr:
            self._AppendOutputAsync(_result.stderr)

        if _result.returncode != 0:
            _summaryLinesArray = (_result.stderr or _result.stdout or failureTitle).strip().splitlines()
            _summaryText = _summaryLinesArray[-1] if _summaryLinesArray else failureTitle
            raise ProjectManagerError(
                f"{failureTitle}: {_summaryText}. How to fix: review output and run the same command in the cloned workspace."
            )

    def _RunPostCloneBootstrap(self) -> None:
        try:
            self._SetStatusAsync("Running post-clone MCP bootstrap...")
            self._AppendOutputAsync("Post-clone setup: installing MCP config and validating knowledge servers.")

            _workspaceRoot = self._workspaceRoot.resolve()
            _installerPath = _workspaceRoot / "tools" / "Install-TimeBoundMCPs.ps1"
            if not _installerPath.exists():
                raise ProjectManagerError(
                    f"Missing installer at {_installerPath}. How to fix: ensure clone includes tools/Install-TimeBoundMCPs.ps1."
                )

            _installCommandArray = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(_installerPath),
                "-ProjectPath",
                str(_workspaceRoot),
                "-SkipPrerequisiteInstall",
                "-SkipSerena",
            ]
            self._RunCommandWithOutput(_installCommandArray, _workspaceRoot, "MCP installer failed")

            _corgoKnowledgePath = _workspaceRoot / "tools" / "corgo-mcp-knowledge"
            _playdateKnowledgePath = _workspaceRoot / "tools" / "playdate-mcp"
            if not _corgoKnowledgePath.exists() or not _playdateKnowledgePath.exists():
                raise ProjectManagerError(
                    "Knowledge MCP folders are missing. How to fix: ensure tools/corgo-mcp-knowledge and tools/playdate-mcp exist in the clone."
                )

            self._RunCommandWithOutput(["npm", "install"], _corgoKnowledgePath, "corgo-mcp-knowledge install failed")
            self._RunCommandWithOutput(["npm", "run", "self-check"], _corgoKnowledgePath, "corgo-mcp-knowledge self-check failed")
            self._RunCommandWithOutput(["npm", "install"], _playdateKnowledgePath, "playdate-mcp install failed")
            self._RunCommandWithOutput(["npm", "run", "self-check"], _playdateKnowledgePath, "playdate-mcp self-check failed")

            self._SetStatusAsync("Post-clone MCP bootstrap complete.")
        except Exception as _error:
            self._SetStatusAsync(str(_error))

    def _FinishBackgroundAction(self) -> None:
        self._HideProgressPopup()
        self._isBusy = False
        self._UpdateBuildPlanInfo()

    def _ShowProgressPopup(self, messageText: str) -> None:
        if self._progressPopup is not None:
            self._progressPopup.dismiss()

        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        _messageLabel = Label(
            text=messageText,
            color=(0.95, 0.95, 0.95, 1),
            halign="center",
            valign="middle",
        )
        _messageLabel.bind(size=lambda _instance, _size: setattr(_instance, "text_size", _instance.size))
        _content.add_widget(_messageLabel)

        self._progressPopup = Popup(
            title="Working...",
            content=_content,
            size_hint=(0.52, 0.24),
            auto_dismiss=False,
        )
        self._progressPopup.open()

    def _HideProgressPopup(self) -> None:
        if self._progressPopup is None:
            return
        self._progressPopup.dismiss()
        self._progressPopup = None

    def _UpdateActionButtonsState(self) -> None:
        _hasGame = bool(self._selectedProjectName and self._selectedGameName)
        _canRun = False
        if _hasGame:
            try:
                _service = self._ServiceForProject(self._selectedProjectName)
                _pdxPath = _service._paths.projectRoot / f"{self._selectedGameName}.pdx"
                _canRun = _pdxPath.exists()
            except Exception:
                _canRun = False

        _canBuild = _hasGame and (not self._isBusy)
        _canRunNow = _canRun and (not self._isBusy)
        _canBuildRun = _hasGame and (not self._isBusy)

        self._SetButtonEnabled(self._buildButton, _canBuild)
        self._SetButtonEnabled(self._runButton, _canRunNow)
        self._SetButtonEnabled(self._buildRunButton, _canBuildRun)

    def _UpdateBuildPlanInfo(self) -> None:
        if not self._selectedProjectName:
            self._buildPlanLabel.text = "Build plan: select a project and game."
            return

        if not self._selectedGameName:
            self._buildPlanLabel.text = f"Build plan: project={self._selectedProjectName}. Select a game."
            return

        try:
            _service = self._ServiceForProject(self._selectedProjectName)
            _startSceneName = _service.GetStartScene(self._selectedGameName)
            _buildPresetName = _service.GetBuildPresetForGame(self._selectedGameName)
            _pdxPath = _service._paths.projectRoot / f"{self._selectedGameName}.pdx"
            self._buildPlanLabel.text = (
                f"Build preset: {_buildPresetName} | Game: {self._selectedGameName} | "
                f"Start scene: {_startSceneName} | Run target: {_pdxPath.name} ({'ready' if _pdxPath.exists() else 'not built'})"
            )
        except Exception as _error:
            self._buildPlanLabel.text = f"Build plan: unavailable ({_error})"
        self._UpdateActionButtonsState()

    def _PromptForName(self, titleText: str, onSubmit: Callable[[str], None], hintText: str = "name") -> None:
        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        _nameInput = TextInput(multiline=False, hint_text=hintText)
        _content.add_widget(_nameInput)

        _buttons = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        _okButton = Button(text="OK", background_normal="", background_color=(0.2, 0.52, 0.84, 1))
        _cancelButton = Button(text="Cancel", background_normal="", background_color=(0.35, 0.35, 0.35, 1))
        _buttons.add_widget(_okButton)
        _buttons.add_widget(_cancelButton)
        _content.add_widget(_buttons)

        _popup = Popup(title=titleText, content=_content, size_hint=(0.65, 0.3), auto_dismiss=False)

        def _Submit() -> None:
            _name = _nameInput.text.strip()
            if not _name:
                self._SetStatus("Please enter a valid name.")
                return
            try:
                onSubmit(_name)
                _popup.dismiss()
            except Exception as _error:
                self._SetStatus(str(_error))

        _okButton.bind(on_press=lambda _instance: _Submit())
        _cancelButton.bind(on_press=lambda _instance: _popup.dismiss())
        _popup.open()

    def _PromptForCloneWorkspace(self) -> None:
        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        _destinationRow = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        _destinationInput = TextInput(
            multiline=False,
            text=str(self._workspaceRoot.parent),
            hint_text="destination folder",
            readonly=True,
        )
        _browseButton = Button(
            text="Browse...",
            size_hint_x=0.32,
            background_normal="",
            background_color=(0.2, 0.52, 0.84, 1),
            color=(1, 1, 1, 1),
        )
        _browseButton.bind(on_press=lambda _instance: self._PickCloneDestinationFolder(_destinationInput))
        _destinationRow.add_widget(_destinationInput)
        _destinationRow.add_widget(_browseButton)

        _nameInput = TextInput(multiline=False, hint_text="new repo name")
        _content.add_widget(_destinationRow)
        _content.add_widget(_nameInput)

        _buttons = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        _okButton = Button(text="OK", background_normal="", background_color=(0.2, 0.52, 0.84, 1))
        _cancelButton = Button(text="Cancel", background_normal="", background_color=(0.35, 0.35, 0.35, 1))
        _buttons.add_widget(_okButton)
        _buttons.add_widget(_cancelButton)
        _content.add_widget(_buttons)

        _popup = Popup(title="Clone Repo", content=_content, size_hint=(0.72, 0.4), auto_dismiss=False)

        def _Submit() -> None:
            _destinationFolder = _destinationInput.text.strip()
            _newName = _nameInput.text.strip()
            if not _destinationFolder or not _newName:
                self._SetStatus("Please enter both destination folder and new repo name.")
                return
            try:
                self._CloneWorkspace(_destinationFolder, _newName)
                _popup.dismiss()
            except Exception as _error:
                self._SetStatus(str(_error))

        _okButton.bind(on_press=lambda _instance: _Submit())
        _cancelButton.bind(on_press=lambda _instance: _popup.dismiss())
        _popup.open()

    def _PickCloneDestinationFolder(self, destinationInput: TextInput) -> None:
        try:
            import tkinter as _tk
            from tkinter import filedialog as _filedialog
        except Exception as _error:
            raise ProjectManagerError(
                f"Folder picker is unavailable. How to fix: ensure tkinter is available in this Python install. Error: {_error}"
            ) from _error

        _root = _tk.Tk()
        _root.withdraw()
        _root.attributes("-topmost", True)
        try:
            _selectedFolder = _filedialog.askdirectory(
                initialdir=destinationInput.text or str(self._workspaceRoot.parent),
                title="Select clone destination folder",
                mustexist=True,
            )
        finally:
            _root.destroy()

        if _selectedFolder:
            destinationInput.text = _selectedFolder

    def _Confirm(
        self,
        titleText: str,
        bodyText: str,
        onConfirm: Callable[[], None],
        confirmText: str = "Yes",
        cancelText: str = "No",
    ) -> None:
        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        _messageLabel = Label(
            text=bodyText,
            color=(0.95, 0.95, 0.95, 1),
            halign="left",
            valign="top",
            size_hint_y=1,
        )
        _messageLabel.bind(size=lambda _instance, _size: setattr(_instance, "text_size", (_instance.width, None)))
        _content.add_widget(_messageLabel)

        _buttons = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        _yesButton = Button(text=confirmText, background_normal="", background_color=(0.76, 0.27, 0.27, 1))
        _noButton = Button(text=cancelText, background_normal="", background_color=(0.35, 0.35, 0.35, 1))
        _buttons.add_widget(_yesButton)
        _buttons.add_widget(_noButton)
        _content.add_widget(_buttons)

        _popup = Popup(title=titleText, content=_content, size_hint=(0.74, 0.42), auto_dismiss=False)

        def _Accept() -> None:
            try:
                _popup.dismiss()
                onConfirm()
            except Exception as _error:
                self._SetStatus(str(_error))

        _yesButton.bind(on_press=lambda _instance: _Accept())
        _noButton.bind(on_press=lambda _instance: _popup.dismiss())
        _popup.open()

    def _OpenProjectWithFeedback(self, projectName: str, statusText: str) -> None:
        self._selectedProjectName = projectName
        self._SetStatus(statusText)
        self._RefreshProjects()
        self._OpenGames(projectName)

    def _PromptSwitchWorkspace(self, workspaceRoot: Path) -> None:
        self._Confirm(
            "Clone Complete",
            f"Cloned repo to {workspaceRoot}. Switch to the cloned repo now?",
            lambda: self._SwitchWorkspace(workspaceRoot),
            confirmText="Switch",
            cancelText="Stay Here",
        )

    def _SwitchWorkspace(self, workspaceRoot: Path) -> None:
        LaunchProjectManager(workspaceRoot, runPostCloneBootstrap=True)
        _app = App.get_running_app()
        if _app is not None:
            _app.stop()

    def _ListProjectNames(self) -> list[str]:
        _projectsArray = []
        for _path in self._workspaceRoot.iterdir():
            if not _path.is_dir():
                continue
            if _path.name.lower() == "corgo-engine":
                continue
            if (_path / "src").exists() and (_path / "CMakePresets.json").exists():
                _projectsArray.append(_path.name)
        _projectsArray.sort()
        return _projectsArray

    def _ServiceForProject(self, projectName: str) -> ProjectManagerService:
        return ProjectManagerService(
            self._workspaceRoot,
            self._configPath,
            projectRootOverride=self._workspaceRoot / projectName,
        )

    def _ClearList(self, listContainer: BoxLayout) -> None:
        listContainer.clear_widgets()

    def _RefreshProjects(self) -> None:
        self._SetTitle()
        self._screenManager.current = "projects"
        self._ClearList(self._projectListContainer)

        _projectsArray = self._ListProjectNames()
        _configuredProjectName = self._bootstrapService.GetConfiguredProjectFolder()
        if _configuredProjectName and _configuredProjectName not in _projectsArray:
            if not self._missingProjectPromptShown:
                self._missingProjectPromptShown = True
                self._Confirm(
                    "Missing Project",
                    (
                        f"Configured project '{_configuredProjectName}' was not found. "
                        "Remove it from project manager configuration?"
                    ),
                    lambda: self._RemoveMissingProjectConfig(_configuredProjectName),
                )
        else:
            self._missingProjectPromptShown = False

        if self._selectedProjectName not in _projectsArray and _projectsArray:
            self._selectedProjectName = _projectsArray[0]

        for _projectName in _projectsArray:
            _row = ItemRow(
                itemName=_projectName,
                onPlay=lambda _name=_projectName: self._OpenGames(_name),
                onCopy=lambda _name=_projectName: self._CopyProjectPrompt(_name),
                onDelete=lambda _name=_projectName: self._DeleteProjectPrompt(_name),
                onRename=lambda _old, _new, _name=_projectName: self._RenameProjectInline(_name, _old, _new),
                onError=self._SetStatus,
            )
            self._projectListContainer.add_widget(_row)
        self._UpdateBuildPlanInfo()

    def _UpdateTitleForGames(self) -> None:
        self._SetTitle(self._selectedProjectName)

    def _UpdateTitleForScenes(self) -> None:
        self._SetTitle(self._selectedProjectName, self._selectedGameName)

    def _OpenGames(self, projectName: str) -> None:
        self._selectedProjectName = projectName
        self._bootstrapService.SaveConfiguredProjectFolder(projectName)
        self._UpdateTitleForGames()
        self._RefreshGames()
        self._SwitchScreen("games", isForward=True)
        self._UpdateBuildPlanInfo()

    def _RefreshGames(self) -> None:
        self._ClearList(self._gameListContainer)
        _service = self._ServiceForProject(self._selectedProjectName)
        _gamesArray = _service.ListGames()
        _configuredGameName = _service.GetConfiguredCurrentGame()
        if _configuredGameName and _configuredGameName not in _gamesArray:
            if not self._missingGamePromptShown:
                self._missingGamePromptShown = True
                self._Confirm(
                    "Missing Game",
                    (
                        f"Configured game '{_configuredGameName}' was not found in project "
                        f"{self._selectedProjectName}. Remove it from configuration?"
                    ),
                    lambda: self._RemoveMissingGameConfig(_configuredGameName),
                )
        else:
            self._missingGamePromptShown = False

        if _gamesArray and self._selectedGameName not in _gamesArray:
            self._selectedGameName = _gamesArray[0]

        for _gameName in _gamesArray:
            _row = ItemRow(
                itemName=_gameName,
                onPlay=lambda _name=_gameName: self._OpenScenes(_name),
                onCopy=lambda _name=_gameName: self._CopyGamePrompt(_name),
                onDelete=lambda _name=_gameName: self._DeleteGamePrompt(_name),
                onRename=lambda _old, _new, _name=_gameName: self._RenameGameInline(_name, _old, _new),
                onError=self._SetStatus,
            )
            self._gameListContainer.add_widget(_row)
        self._UpdateBuildPlanInfo()

    def _OpenScenes(self, gameName: str) -> None:
        self._selectedGameName = gameName
        _service = self._ServiceForProject(self._selectedProjectName)
        _switchResult = _service.SwitchGame(gameName)
        self._SetStatus(_switchResult)
        self._UpdateTitleForScenes()
        self._RefreshScenes()
        self._SwitchScreen("scenes", isForward=True)
        self._UpdateBuildPlanInfo()

    def _RefreshScenes(self) -> None:
        self._ClearList(self._sceneListContainer)
        _service = self._ServiceForProject(self._selectedProjectName)
        _scenesArray = _service.ListScenes(self._selectedGameName)

        for _sceneName in _scenesArray:
            _row = ItemRow(
                itemName=_sceneName,
                onPlay=lambda _name=_sceneName: self._PlayScene(_name),
                onCopy=lambda _name=_sceneName: self._CopyScenePrompt(_name),
                onDelete=lambda _name=_sceneName: self._DeleteScenePrompt(_name),
                onRename=lambda _old, _new, _name=_sceneName: self._RenameSceneInline(_name, _old, _new),
                onError=self._SetStatus,
                onNameDoubleTapAction=lambda _name=_sceneName: self._OpenSceneInVsCode(_name),
            )
            self._sceneListContainer.add_widget(_row)

        _missingScenesArray = _service.ListMissingSceneFiles(self._selectedGameName)
        if _missingScenesArray:
            _missingText = ", ".join(_missingScenesArray)
            self._SetStatus(
                f"Warning: scenes declared but missing files in {self._selectedGameName}: {_missingText}."
            )

            _missingKey = (
                f"{self._selectedProjectName}|{self._selectedGameName}|{','.join(_missingScenesArray)}"
            )
            if _missingKey != self._missingScenesPromptKey:
                self._missingScenesPromptKey = _missingKey
                self._Confirm(
                    "Missing Scenes",
                    (
                        f"These scenes are declared but missing files: {_missingText}. "
                        "Remove missing declarations from scenes.h?"
                    ),
                    lambda _missing=list(_missingScenesArray): self._RemoveMissingSceneDeclarations(_missing),
                )
        else:
            self._missingScenesPromptKey = ""
            self._SetStatus("Tip: double-click a scene name to open file in VS Code. Shift+double-click to rename.")
        self._UpdateBuildPlanInfo()

    def _RemoveMissingProjectConfig(self, projectName: str) -> None:
        if self._bootstrapService.GetConfiguredProjectFolder() == projectName:
            self._bootstrapService.ClearConfiguredProjectFolder()
            self._SetStatus(f"Removed missing project '{projectName}' from configuration.")
        self._missingProjectPromptShown = False

    def _RemoveMissingGameConfig(self, gameName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        if _service.GetConfiguredCurrentGame() == gameName:
            _service.ClearConfiguredCurrentGame()
            self._SetStatus(f"Removed missing game '{gameName}' from configuration.")
        self._missingGamePromptShown = False

    def _RemoveMissingSceneDeclarations(self, missingScenesArray: list[str]) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        for _sceneName in missingScenesArray:
            _service.RemoveSceneDeclaration(self._selectedGameName, _sceneName)
        self._SetStatus(
            f"Removed {len(missingScenesArray)} missing scene declaration(s) from {self._selectedGameName}."
        )
        self._missingScenesPromptKey = ""
        self._RefreshScenes()

    def _OpenSceneInVsCode(self, sceneName: str) -> None:
        try:
            _service = self._ServiceForProject(self._selectedProjectName)
            _sceneFilePath = _service.GetSceneFilePath(self._selectedGameName, sceneName)

            _codeExe = shutil.which("code")
            if _codeExe is None:
                raise ProjectManagerError(
                    "VS Code command-line tool not found. How to fix: install the 'code' CLI from VS Code command palette."
                )

            subprocess.Popen([
                _codeExe,
                "--reuse-window",
                "--goto",
                f"{_sceneFilePath}:1",
            ])
            self._SetStatus(f"Opened scene file: {_sceneFilePath.name}")
        except Exception as _error:
            self._SetStatus(str(_error))

    def _RenameProjectInline(self, expectedName: str, oldName: str, newName: str) -> None:
        if oldName != expectedName:
            raise ProjectManagerError("Project list changed. How to fix: refresh and try again.")

        _result = self._bootstrapService.RenameProjectFolder(oldName, newName)
        if self._selectedProjectName == oldName:
            self._selectedProjectName = newName
        self._SetStatus(_result)
        self._RefreshProjects()

    def _CopyProjectPrompt(self, projectName: str) -> None:
        self._PromptForName(
            f"Copy Project {projectName}",
            lambda _newName: self._CopyProject(projectName, _newName),
            hintText="new project name",
        )

    def _CopyProject(self, projectName: str, newProjectName: str) -> None:
        _result = self._bootstrapService.CloneProjectFolder(projectName, newProjectName)
        self._OpenProjectWithFeedback(newProjectName, _result)

    def _DeleteProjectPrompt(self, projectName: str) -> None:
        self._Confirm(
            "Delete Project",
            f"Delete project {projectName}?",
            lambda: self._DeleteProject(projectName),
        )

    def _DeleteProject(self, projectName: str) -> None:
        _targetPath = self._workspaceRoot / projectName
        if not _targetPath.exists():
            raise ProjectManagerError(f"Project {projectName} does not exist. How to fix: refresh and try again.")

        shutil.rmtree(_targetPath)
        if self._selectedProjectName == projectName:
            self._selectedProjectName = ""
            self._selectedGameName = ""
        self._SetStatus(f"Deleted project {projectName}.")
        self._RefreshProjects()

    def _OnAddProject(self) -> None:
        self._PromptForName("Add Project", self._CreateEmptyProject, hintText="project name")

    def _OnCloneWorkspace(self) -> None:
        self._PromptForCloneWorkspace()

    def _CloneWorkspace(self, destinationFolderText: str, newProjectName: str) -> None:
        if self._isBusy:
            self._SetStatus("Action already in progress.")
            return

        self._SetStatus("Cloning repository... this may take a moment.")
        self._AppendOutput("Cloning repository and preparing cloned workspace...")
        self._StartBackgroundAction(
            lambda: self._CloneWorkspaceWorker(destinationFolderText, newProjectName),
            busyMessageText="Cloning repository and preparing project...",
        )

    def _CloneWorkspaceWorker(self, destinationFolderText: str, newProjectName: str) -> None:
        try:
            _destinationFolder = Path(destinationFolderText).expanduser()
            _result = self._bootstrapService.CloneProject(_destinationFolder, newProjectName)
            _clonedWorkspaceRoot = _destinationFolder.resolve() / newProjectName
            self._SetStatusAsync(_result)
            self._AppendOutputAsync(_result)
            Clock.schedule_once(
                lambda _dt: self._PromptSwitchWorkspace(_clonedWorkspaceRoot),
                0,
            )
        except Exception as _error:
            self._SetStatusAsync(str(_error))

    def _CreateEmptyProject(self, projectName: str) -> None:
        _templateProjectName = self._selectedProjectName if self._selectedProjectName else ""
        _projectNames = self._ListProjectNames()
        if _templateProjectName not in _projectNames and _projectNames:
            _templateProjectName = _projectNames[0]

        if not _templateProjectName:
            _projectPath = self._workspaceRoot / projectName
            if _projectPath.exists():
                raise ProjectManagerError(f"Project {projectName} already exists. How to fix: choose another name.")

            (_projectPath / "src").mkdir(parents=True, exist_ok=False)
            (_projectPath / "Source").mkdir(parents=True, exist_ok=True)

            (_projectPath / "CMakePresets.json").write_text(
                json.dumps({"version": 6, "configurePresets": [], "buildPresets": []}, indent=2),
                encoding="utf-8",
            )
            (_projectPath / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.14)\n"
                f"project({projectName} C ASM)\n",
                encoding="utf-8",
            )

            self._OpenProjectWithFeedback(projectName, f"Created empty project {projectName}.")
            return

        _result = self._bootstrapService.CloneProjectFolder(_templateProjectName, projectName)
        self._OpenProjectWithFeedback(projectName, _result)

    def _OnAddGame(self) -> None:
        self._PromptForName("Add Game", self._CreateEmptyGame, hintText="game name")

    def _CreateEmptyGame(self, gameName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.CreateEmptyGame(gameName)
        self._selectedGameName = gameName
        self._SetStatus(_result)
        self._RefreshGames()

    def _CopyGamePrompt(self, gameName: str) -> None:
        self._PromptForName(
            f"Copy Game {gameName}",
            lambda _newName: self._CopyGame(gameName, _newName),
            hintText="new game name",
        )

    def _CopyGame(self, gameName: str, newGameName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.CloneGame(gameName, newGameName)
        self._SetStatus(_result)
        self._RefreshGames()

    def _DeleteGamePrompt(self, gameName: str) -> None:
        self._Confirm("Delete Game", f"Delete game {gameName}?", lambda: self._DeleteGame(gameName))

    def _DeleteGame(self, gameName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.DeleteGame(gameName)
        self._SetStatus(_result)
        self._RefreshGames()

    def _RenameGameInline(self, expectedName: str, oldName: str, newName: str) -> None:
        if oldName != expectedName:
            raise ProjectManagerError("Game list changed. How to fix: refresh and try again.")
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.RenameGame(oldName, newName)
        if self._selectedGameName == oldName:
            self._selectedGameName = newName
        self._SetStatus(_result)
        self._RefreshGames()

    def _OnAddScene(self) -> None:
        self._PromptForName("Add Scene", self._AddScene, hintText="scene name (PascalCase)")

    def _AddScene(self, sceneName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.AddScene(self._selectedGameName, sceneName)
        self._SetStatus(_result)
        self._RefreshScenes()

    def _CopyScenePrompt(self, sceneName: str) -> None:
        self._PromptForName(
            f"Copy Scene {sceneName}",
            lambda _newName: self._CopyScene(sceneName, _newName),
            hintText="new scene name",
        )

    def _CopyScene(self, sceneName: str, newSceneName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.CloneScene(self._selectedGameName, sceneName, newSceneName)
        self._SetStatus(_result)
        self._RefreshScenes()

    def _DeleteScenePrompt(self, sceneName: str) -> None:
        self._Confirm("Delete Scene", f"Delete scene {sceneName}?", lambda: self._DeleteScene(sceneName))

    def _DeleteScene(self, sceneName: str) -> None:
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.DeleteScene(self._selectedGameName, sceneName)
        self._SetStatus(_result)
        self._RefreshScenes()

    def _RenameSceneInline(self, expectedName: str, oldName: str, newName: str) -> None:
        if oldName != expectedName:
            raise ProjectManagerError("Scene list changed. How to fix: refresh and try again.")
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.RenameScene(self._selectedGameName, oldName, newName)
        self._SetStatus(_result)
        self._RefreshScenes()

    def _PlayScene(self, sceneName: str) -> None:
        try:
            _service = self._ServiceForProject(self._selectedProjectName)
            _result = _service.SetStartScene(self._selectedGameName, sceneName)
            self._SetStatus(_result)
            self._UpdateBuildPlanInfo()
        except Exception as _error:
            self._SetStatus(str(_error))

    def _BuildSelectedGame(self) -> bool:
        try:
            _service = self._ServiceForProject(self._selectedProjectName)
            _configurePresetName = _service.GetConfigurePresetForGame(self._selectedGameName)
            _buildPresetName = _service.GetBuildPresetForGame(self._selectedGameName)

            _configureCommandArray = ["cmake", "--preset", _configurePresetName]
            self._AppendOutputAsync(f"$ {' '.join(_configureCommandArray)}")
            _configureResult = subprocess.run(
                _configureCommandArray,
                cwd=str(_service._paths.projectRoot),
                capture_output=True,
                text=True,
                check=False,
            )
            if _configureResult.stdout:
                self._AppendOutputAsync(_configureResult.stdout)
            if _configureResult.stderr:
                self._AppendOutputAsync(_configureResult.stderr)
            if _configureResult.returncode != 0:
                _lastLine = (_configureResult.stderr or _configureResult.stdout or "Configure failed.").strip().splitlines()
                _summary = _lastLine[-1] if _lastLine else "Configure failed."
                self._SetStatusAsync(f"Configure failed ({_configurePresetName}): {_summary}")
                return False

            _commandArray = ["cmake", "--build", "--preset", _buildPresetName, "--config", "Debug"]
            self._AppendOutputAsync(f"$ {' '.join(_commandArray)}")
            _result = subprocess.run(
                _commandArray,
                cwd=str(_service._paths.projectRoot),
                capture_output=True,
                text=True,
                check=False,
            )
            if _result.stdout:
                self._AppendOutputAsync(_result.stdout)
            if _result.stderr:
                self._AppendOutputAsync(_result.stderr)
            if _result.returncode != 0:
                _combinedOutput = f"{_result.stdout}\n{_result.stderr}".lower()
                if "pdex.dll" in _combinedOutput and ("errno=13" in _combinedOutput or "file copy" in _combinedOutput):
                    _helpText = (
                        "Build failed: Source/pdex.dll is locked by Playdate Simulator. "
                        "How to fix: close the simulator (or stop PlaydateSimulator process), then click Build again."
                    )
                    self._AppendOutputAsync(_helpText)
                    self._SetStatusAsync(_helpText)
                    return False
                _lastLine = (_result.stderr or _result.stdout or "Build failed.").strip().splitlines()
                _summary = _lastLine[-1] if _lastLine else "Build failed."
                _messageText = f"Build failed ({_buildPresetName}): {_summary}"
                self._AppendOutputAsync(_messageText)
                self._SetStatusAsync(_messageText)
                return False
            self._SetStatusAsync(f"Build finished ({_buildPresetName}).")
            return True
        except Exception as _error:
            self._SetStatusAsync(str(_error))
            return False

    def _RunSelectedGame(self) -> bool:
        try:
            _service = self._ServiceForProject(self._selectedProjectName)
            _simPath = _service.GetSimulatorPath()
            _pdxPath = _service._paths.projectRoot / f"{self._selectedGameName}.pdx"
            if not _pdxPath.exists():
                raise ProjectManagerError(
                    f"PDX not found: {_pdxPath}. How to fix: build the selected game first."
                )

            self._AppendOutputAsync(f"$ \"{_simPath}\" \"{_pdxPath}\"")
            subprocess.Popen([str(_simPath), str(_pdxPath)], cwd=str(_service._paths.projectRoot))
            self._SetStatusAsync(f"Launched simulator with {_pdxPath.name}.")
            return True
        except Exception as _error:
            self._SetStatusAsync(str(_error))
            return False

    def _BuildAndRunSelectedGame(self) -> None:
        if self._BuildSelectedGame():
            self._RunSelectedGame()

    def _StartBuildSelectedGame(self) -> None:
        self._StartBackgroundAction(lambda: self._BuildSelectedGame())

    def _StartRunSelectedGame(self) -> None:
        self._StartBackgroundAction(lambda: self._RunSelectedGame())

    def _StartBuildAndRunSelectedGame(self) -> None:
        self._StartBackgroundAction(self._BuildAndRunSelectedGame)


class ProjectManagerApp(App):
    def __init__(self, service: ProjectManagerService, **kwargs):
        super().__init__(**kwargs)
        self._service = service

    def build(self):
        self.title = FormatProjectManagerTitle(self._service._workspaceRoot.name)
        Window.size = (760, 620)
        Window.clearcolor = (0.11, 0.11, 0.11, 1)
        return ProjectManagerLayout(service=self._service)
