import json
import shutil
from pathlib import Path
from typing import Callable, Optional

from kivy.app import App
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

from .core import ProjectManagerError
from .core import ProjectManagerService


class InlineRenameInput(TextInput):
    def __init__(
        self,
        initialName: str,
        onCommit: Callable[[str, str], None],
        onError: Callable[[str], None],
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
        self._originalText = initialName
        self.bind(focus=self._OnFocusChanged)
        self.bind(on_text_validate=self._OnTextValidate)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and getattr(touch, "is_double_tap", False):
            self.readonly = False
            self.focus = True
            self.select_all()
            return True
        return super().on_touch_down(touch)

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
        **kwargs,
    ):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(6), **kwargs)

        self._nameInput = InlineRenameInput(itemName, onRename, onError)
        self.add_widget(self._nameInput)

        self._playButton = Button(
            text=">",
            size_hint_x=0.12,
            background_normal="",
            background_color=(0.19, 0.58, 0.77, 1),
            color=(1, 1, 1, 1),
        )
        self._copyButton = Button(
            text="Copy",
            size_hint_x=0.14,
            background_normal="",
            background_color=(0.21, 0.5, 0.82, 1),
            color=(1, 1, 1, 1),
        )
        self._deleteButton = Button(
            text="X",
            size_hint_x=0.1,
            background_normal="",
            background_color=(0.75, 0.23, 0.23, 1),
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

        self._BuildUi()
        self._RefreshProjects()

    def _BuildUi(self) -> None:
        self._titleLabel = Label(
            text="CorgoEngine",
            size_hint_y=None,
            height=dp(40),
            bold=True,
            color=(1, 0.93, 0.22, 1),
        )
        self.add_widget(self._titleLabel)

        self._screenManager = ScreenManager()
        self.add_widget(self._screenManager)

        self._statusLabel = Label(
            text="",
            size_hint_y=None,
            height=dp(28),
            color=(0.92, 0.92, 0.92, 1),
        )
        self.add_widget(self._statusLabel)

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
            background_color=(0.15, 0.62, 0.31, 1),
            color=(1, 1, 1, 1),
        )
        _addButton.bind(on_press=lambda _instance: onAdd())
        _buttonsRow.add_widget(_addButton)

        if screenName != "projects":
            _backButton = Button(
                text="Back",
                background_normal="",
                background_color=(0.33, 0.33, 0.33, 1),
                color=(1, 1, 1, 1),
            )
            _backButton.bind(on_press=lambda _instance: self._GoBack(screenName))
            _buttonsRow.add_widget(_backButton)

        _root.add_widget(_buttonsRow)
        _screen.add_widget(_root)
        self._screenManager.add_widget(_screen)
        return _list

    def _GoBack(self, currentScreen: str) -> None:
        if currentScreen == "scenes":
            self._screenManager.current = "games"
            self._UpdateTitleForGames()
            return

        self._screenManager.current = "projects"
        self._titleLabel.text = "CorgoEngine"

    def _SetStatus(self, messageText: str) -> None:
        self._statusLabel.text = messageText

    def _PromptForName(self, titleText: str, onSubmit: Callable[[str], None], hintText: str = "name") -> None:
        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        _nameInput = TextInput(multiline=False, hint_text=hintText)
        _content.add_widget(_nameInput)

        _buttons = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        _okButton = Button(text="OK", background_normal="", background_color=(0.17, 0.58, 0.3, 1))
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

    def _Confirm(self, titleText: str, bodyText: str, onConfirm: Callable[[], None]) -> None:
        _content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        _content.add_widget(Label(text=bodyText))

        _buttons = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        _yesButton = Button(text="Yes", background_normal="", background_color=(0.75, 0.2, 0.2, 1))
        _noButton = Button(text="No", background_normal="", background_color=(0.35, 0.35, 0.35, 1))
        _buttons.add_widget(_yesButton)
        _buttons.add_widget(_noButton)
        _content.add_widget(_buttons)

        _popup = Popup(title=titleText, content=_content, size_hint=(0.68, 0.32), auto_dismiss=False)

        def _Accept() -> None:
            try:
                onConfirm()
                _popup.dismiss()
            except Exception as _error:
                self._SetStatus(str(_error))

        _yesButton.bind(on_press=lambda _instance: _Accept())
        _noButton.bind(on_press=lambda _instance: _popup.dismiss())
        _popup.open()

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
        self._titleLabel.text = "CorgoEngine"
        self._screenManager.current = "projects"
        self._ClearList(self._projectListContainer)

        _projectsArray = self._ListProjectNames()
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

    def _UpdateTitleForGames(self) -> None:
        self._titleLabel.text = f"CorgoEngine - {self._selectedProjectName}"

    def _UpdateTitleForScenes(self) -> None:
        self._titleLabel.text = f"CorgoEngine - {self._selectedProjectName} - {self._selectedGameName}"

    def _OpenGames(self, projectName: str) -> None:
        self._selectedProjectName = projectName
        self._UpdateTitleForGames()
        self._RefreshGames()
        self._screenManager.current = "games"

    def _RefreshGames(self) -> None:
        self._ClearList(self._gameListContainer)
        _service = self._ServiceForProject(self._selectedProjectName)
        _gamesArray = _service.ListGames()
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

    def _OpenScenes(self, gameName: str) -> None:
        self._selectedGameName = gameName
        self._UpdateTitleForScenes()
        self._RefreshScenes()
        self._screenManager.current = "scenes"

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
            )
            self._sceneListContainer.add_widget(_row)

    def _RenameProjectInline(self, expectedName: str, oldName: str, newName: str) -> None:
        if oldName != expectedName:
            raise ProjectManagerError("Project list changed. How to fix: refresh and try again.")

        _oldPath = self._workspaceRoot / oldName
        _newPath = self._workspaceRoot / newName
        if _newPath.exists():
            raise ProjectManagerError(f"Project {newName} already exists. How to fix: choose a different name.")

        _oldPath.rename(_newPath)
        if self._selectedProjectName == oldName:
            self._selectedProjectName = newName
        self._SetStatus(f"Renamed project {oldName} to {newName}.")
        self._RefreshProjects()

    def _CopyProjectPrompt(self, projectName: str) -> None:
        self._PromptForName(
            f"Copy Project {projectName}",
            lambda _newName: self._CopyProject(projectName, _newName),
            hintText="new project name",
        )

    def _CopyProject(self, projectName: str, newProjectName: str) -> None:
        _sourcePath = self._workspaceRoot / projectName
        _targetPath = self._workspaceRoot / newProjectName
        if _targetPath.exists():
            raise ProjectManagerError(f"Project {newProjectName} already exists. How to fix: choose another name.")

        shutil.copytree(_sourcePath, _targetPath)
        self._SetStatus(f"Copied project {projectName} to {newProjectName}.")
        self._RefreshProjects()

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

    def _CreateEmptyProject(self, projectName: str) -> None:
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

        self._selectedProjectName = projectName
        self._SetStatus(f"Created empty project {projectName}.")
        self._RefreshProjects()

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
        _service = self._ServiceForProject(self._selectedProjectName)
        _result = _service.SetStartScene(self._selectedGameName, sceneName)
        self._SetStatus(_result)


class ProjectManagerApp(App):
    def __init__(self, service: ProjectManagerService, **kwargs):
        super().__init__(**kwargs)
        self._service = service

    def build(self):
        self.title = "CorgoEngine"
        Window.size = (760, 620)
        Window.clearcolor = (0.05, 0.05, 0.05, 1)
        return ProjectManagerLayout(service=self._service)
