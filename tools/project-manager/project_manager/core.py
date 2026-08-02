import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProjectManagerError(Exception):
    pass


@dataclass
class ProjectPaths:
    workspaceRoot: Path
    projectRoot: Path
    srcRoot: Path
    vscodeRoot: Path


class ProjectManagerService:
    def __init__(self, workspaceRoot: Path, configPath: Path, projectRootOverride: Optional[Path] = None):
        self._workspaceRoot = workspaceRoot.resolve()
        self._configPath = configPath.resolve()
        self._paths = self._DetectPaths(self._workspaceRoot, projectRootOverride)
        self._config = self._LoadConfig()

    def _DetectPaths(self, workspaceRoot: Path, projectRootOverride: Optional[Path]) -> ProjectPaths:
        _vscodeRoot = workspaceRoot / ".vscode"
        if projectRootOverride is not None:
            _projectRoot = projectRootOverride.resolve()
        else:
            _settingsPath = _vscodeRoot / "settings.json"
            _projectRoot = workspaceRoot / "corgogame"

            if _settingsPath.exists():
                _settings = self._LoadJson(_settingsPath)
                _sourceDirectory = str(_settings.get("cmake.sourceDirectory", "")).strip()
                _match = re.search(r"\$\{workspaceFolder\}/([^/]+)/?", _sourceDirectory)
                if _match:
                    _candidate = workspaceRoot / _match.group(1)
                    if _candidate.exists():
                        _projectRoot = _candidate

        _srcRoot = _projectRoot / "src"
        if not _srcRoot.exists():
            raise ProjectManagerError(
                "Could not find game source folder. How to fix: ensure <workspace>/corgogame/src exists or update .vscode/settings.json cmake.sourceDirectory."
            )

        return ProjectPaths(
            workspaceRoot=workspaceRoot,
            projectRoot=_projectRoot,
            srcRoot=_srcRoot,
            vscodeRoot=_vscodeRoot,
        )

    def _LoadConfig(self) -> Dict[str, Any]:
        if self._configPath.exists():
            try:
                return self._LoadJson(self._configPath)
            except Exception as _error:
                raise ProjectManagerError(
                    f"Config file is invalid JSON. How to fix: repair {self._configPath}. Error: {_error}"
                ) from _error

        _defaultConfig = {
            "currentGame": "",
            "projectFolder": self._paths.projectRoot.name,
        }
        self._SaveConfig(_defaultConfig)
        return _defaultConfig

    def _SaveConfig(self, configMap: Dict[str, Any]) -> None:
        self._configPath.parent.mkdir(parents=True, exist_ok=True)
        self._configPath.write_text(json.dumps(configMap, indent=2), encoding="utf-8")

    def _LoadJson(self, filePath: Path) -> Dict[str, Any]:
        return json.loads(filePath.read_text(encoding="utf-8"))

    def _SaveJson(self, filePath: Path, dataMap: Dict[str, Any]) -> None:
        filePath.write_text(json.dumps(dataMap, indent=2), encoding="utf-8")

    def _ReplaceWorkspaceProjectPath(self, value: Any, oldProjectName: str, newProjectName: str) -> Any:
        if isinstance(value, str):
            _pattern = re.compile(rf"(\$\{{workspaceFolder\}}/){re.escape(oldProjectName)}(?=[/\\]|$)")
            return _pattern.sub(rf"\1{newProjectName}", value)

        if isinstance(value, list):
            return [self._ReplaceWorkspaceProjectPath(_item, oldProjectName, newProjectName) for _item in value]

        if isinstance(value, dict):
            return {
                _key: self._ReplaceWorkspaceProjectPath(_item, oldProjectName, newProjectName)
                for _key, _item in value.items()
            }

        return value

    def _ProjectCloneIgnore(self, directoryPath: str, namesArray: List[str]) -> set[str]:
        _ignoredNames = set(
            shutil.ignore_patterns(
                "build*",
                "*.pdx",
                "*_DEVICE.pdx",
                "__pycache__",
            )(directoryPath, namesArray)
        )

        if Path(directoryPath).name == "Source" and "pdex.dll" in namesArray:
            _ignoredNames.add("pdex.dll")

        return _ignoredNames

    def _ValidateGameName(self, gameName: str) -> None:
        if not re.match(r"^[a-z][a-z0-9_]*$", gameName):
            raise ProjectManagerError(
                "Game name must be lowercase snake case (for example mygame or my_game). How to fix: use letters, numbers, and underscore only."
            )

    def _ValidateSceneName(self, sceneName: str) -> None:
        if not re.match(r"^[A-Z][A-Za-z0-9_]*$", sceneName):
            raise ProjectManagerError(
                "Scene name must start with uppercase and be alphanumeric (for example MainMenuScene). How to fix: rename scene to PascalCase."
            )

    def _ValidateProjectName(self, projectName: str) -> None:
        if not re.match(r"^[a-zA-Z0-9_-]+$", projectName):
            raise ProjectManagerError(
                "Project name allows letters, numbers, dash and underscore only. How to fix: remove spaces and special characters."
            )

    def _GetCMakePresetsPath(self) -> Path:
        _filePath = self._paths.projectRoot / "CMakePresets.json"
        if not _filePath.exists():
            raise ProjectManagerError(
                "Missing CMakePresets.json. How to fix: ensure project root contains CMakePresets.json."
            )
        return _filePath

    def _GetLaunchPath(self) -> Path:
        _filePath = self._paths.vscodeRoot / "launch.json"
        if not _filePath.exists():
            raise ProjectManagerError(
                "Missing .vscode/launch.json. How to fix: open workspace root and ensure launch.json exists."
            )
        return _filePath

    def _GetSettingsPath(self) -> Path:
        _filePath = self._paths.vscodeRoot / "settings.json"
        if not _filePath.exists():
            raise ProjectManagerError(
                "Missing .vscode/settings.json. How to fix: ensure VS Code workspace files are present."
            )
        return _filePath

    def ListGames(self) -> List[str]:
        _gamesArray = [
            _path.name
            for _path in self._paths.srcRoot.iterdir()
            if _path.is_dir() and not _path.name.startswith(".")
        ]
        _gamesArray.sort()
        return _gamesArray

    def _GetScenesHeaderPath(self, gameName: str) -> Path:
        return self._paths.srcRoot / gameName / "scenes.h"

    def _GetScenesFolderPath(self, gameName: str) -> Path:
        return self._paths.srcRoot / gameName / "scenes"

    def _ListScenesFromHeader(self, gameName: str) -> List[str]:
        _scenesHeaderPath = self._GetScenesHeaderPath(gameName)
        if not _scenesHeaderPath.exists():
            raise ProjectManagerError(
                f"Missing scenes.h for game {gameName}. How to fix: create {gameName}/scenes.h in src."
            )

        _content = _scenesHeaderPath.read_text(encoding="utf-8")
        _contentNoBlockComments = re.sub(r"/\*.*?\*/", "", _content, flags=re.DOTALL)
        _contentNoComments = re.sub(r"//.*$", "", _contentNoBlockComments, flags=re.MULTILINE)
        return re.findall(r"CE_DECLARE_SCENE\((\w+)\)", _contentNoComments)

    def _GetSceneNameFromFile(self, sceneFilePath: Path) -> str:
        _content = sceneFilePath.read_text(encoding="utf-8")
        _match = re.search(r"CE_DECLARE_SCENE_CREATE_FUNCTION\((\w+)\)", _content)
        if _match:
            return _match.group(1)

        _stem = sceneFilePath.stem
        _pascal = "".join(_piece.capitalize() for _piece in re.split(r"[_\-\s]+", _stem) if _piece)
        if _pascal and re.match(r"^[A-Z][A-Za-z0-9_]*$", _pascal):
            return _pascal
        return _stem

    def _ListScenesFromFiles(self, gameName: str) -> List[str]:
        _sceneFolderPath = self._GetScenesFolderPath(gameName)
        if not _sceneFolderPath.exists():
            raise ProjectManagerError(
                f"Missing scenes folder for game {gameName}. How to fix: create src/{gameName}/scenes and add scene .c files."
            )

        _sceneNamesArray = []
        for _path in sorted(_sceneFolderPath.glob("*.c"), key=lambda _item: _item.name.lower()):
            _sceneName = self._GetSceneNameFromFile(_path)
            if _sceneName not in _sceneNamesArray:
                _sceneNamesArray.append(_sceneName)
        return _sceneNamesArray

    def ListScenes(self, gameName: str) -> List[str]:
        self._ValidateGameName(gameName)
        return self._ListScenesFromFiles(gameName)

    def GetSceneFilePath(self, gameName: str, sceneName: str) -> Path:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(sceneName)

        _scenePath = self._FindSceneFilePath(gameName, sceneName)
        if _scenePath is None:
            raise ProjectManagerError(
                f"Scene file for {sceneName} is missing in game {gameName}. "
                f"How to fix: add {sceneName.lower()}.c under src/{gameName}/scenes or update scenes.h declarations."
            )
        return _scenePath

    def ListMissingSceneFiles(self, gameName: str) -> List[str]:
        self._ValidateGameName(gameName)
        _missingArray: List[str] = []
        for _sceneName in self._ListScenesFromHeader(gameName):
            if self._FindSceneFilePath(gameName, _sceneName) is None:
                _missingArray.append(_sceneName)
        return _missingArray

    def GetSceneHeaderFileMismatch(self, gameName: str) -> Dict[str, List[str]]:
        self._ValidateGameName(gameName)
        _headerScenes = self._ListScenesFromHeader(gameName)
        _fileScenes = self._ListScenesFromFiles(gameName)

        _headerOnly = sorted(_scene for _scene in _headerScenes if _scene not in _fileScenes)
        _filesOnly = sorted(_scene for _scene in _fileScenes if _scene not in _headerScenes)
        return {
            "headerOnly": _headerOnly,
            "filesOnly": _filesOnly,
        }

    def SyncSceneHeaderToFiles(self, gameName: str) -> str:
        self._ValidateGameName(gameName)

        _mismatch = self.GetSceneHeaderFileMismatch(gameName)
        _headerOnly = _mismatch["headerOnly"]
        _filesOnly = _mismatch["filesOnly"]

        _headerPath = self._GetScenesHeaderPath(gameName)
        for _sceneName in _headerOnly:
            self._RemoveSceneDeclarationFromHeader(_headerPath, _sceneName)
        for _sceneName in _filesOnly:
            self._AddSceneDeclarationToHeader(_headerPath, _sceneName)

        _headerContent = _headerPath.read_text(encoding="utf-8")
        _startScenePattern = re.compile(r"#define\s+CE_ENGINE_SET_START_SCENE\s+(\w+)")
        _startSceneGuardBlockPattern = re.compile(
            r"\n#ifndef\s+CE_ENGINE_SET_START_SCENE\s*\n"
            r"#define\s+CE_ENGINE_SET_START_SCENE\s+\w+\s*\n"
            r"#endif\s*\n?",
            flags=re.MULTILINE,
        )
        _startSceneMatch = _startScenePattern.search(_headerContent)
        _fileScenes = self._ListScenesFromFiles(gameName)

        if _fileScenes:
            if _startSceneMatch:
                if _startSceneMatch.group(1) not in _fileScenes:
                    self.SetStartScene(gameName, _fileScenes[0])
            else:
                self.SetStartScene(gameName, _fileScenes[0])
        elif _startSceneMatch:
            _headerContent = _startSceneGuardBlockPattern.sub("\n", _headerContent)
            _headerPath.write_text(_headerContent, encoding="utf-8")

        if not _headerOnly and not _filesOnly:
            return f"Scene header already matches scene files for game {gameName}."
        return (
            f"Updated scene header for game {gameName}. "
            f"Removed {len(_headerOnly)} stale declaration(s) and added {len(_filesOnly)} missing declaration(s)."
        )

    def _SaveCurrentGame(self, gameName: str) -> None:
        self._config["currentGame"] = gameName
        self._SaveConfig(self._config)

    def GetConfiguredProjectFolder(self) -> str:
        return str(self._config.get("projectFolder", "")).strip()

    def SaveConfiguredProjectFolder(self, projectFolderName: str) -> None:
        self._config["projectFolder"] = projectFolderName
        self._SaveConfig(self._config)

    def ClearConfiguredProjectFolder(self) -> None:
        self._config["projectFolder"] = ""
        self._SaveConfig(self._config)

    def GetConfiguredCurrentGame(self) -> str:
        return str(self._config.get("currentGame", "")).strip()

    def ClearConfiguredCurrentGame(self) -> None:
        self._SaveCurrentGame("")

    def GetCurrentGame(self) -> str:
        _saved = str(self._config.get("currentGame", "")).strip()
        if _saved and _saved in self.ListGames():
            return _saved

        _gamesArray = self.ListGames()
        if not _gamesArray:
            raise ProjectManagerError(
                "No games found under project src folder. How to fix: add a game folder under project/src."
            )

        _currentGame = _gamesArray[0]
        self._SaveCurrentGame(_currentGame)
        return _currentGame

    def GetStartScene(self, gameName: str) -> str:
        self._ValidateGameName(gameName)

        _headerPath = self._GetScenesHeaderPath(gameName)
        if not _headerPath.exists():
            raise ProjectManagerError(
                f"Missing scenes.h for game {gameName}. How to fix: create {gameName}/scenes.h in src."
            )

        _headerContent = _headerPath.read_text(encoding="utf-8")
        _match = re.search(r"#define\s+CE_ENGINE_SET_START_SCENE\s+(\w+)", _headerContent)
        if _match:
            return _match.group(1)

        _scenesArray = self.ListScenes(gameName)
        if not _scenesArray:
            raise ProjectManagerError(
                f"Game {gameName} has no scenes. How to fix: add a scene before running."
            )
        return _scenesArray[0]

    def GetBuildPresetForGame(self, gameName: str) -> str:
        self._ValidateGameName(gameName)

        _presetsMap = self._LoadJson(self._GetCMakePresetsPath())
        _configurePresetName = self.GetConfigurePresetForGame(gameName)

        _buildPresetName = ""
        for _preset in _presetsMap.get("buildPresets", []):
            if _preset.get("configurePreset") == _configurePresetName:
                _buildPresetName = _preset.get("name", "")
                break

        if not _buildPresetName:
            raise ProjectManagerError(
                f"No build preset found for game {gameName}. How to fix: add a build preset for configure preset {_configurePresetName}."
            )
        return _buildPresetName

    def GetConfigurePresetForGame(self, gameName: str) -> str:
        self._ValidateGameName(gameName)

        _presetsMap = self._LoadJson(self._GetCMakePresetsPath())
        _configurePresetName = ""
        for _preset in _presetsMap.get("configurePresets", []):
            _cacheMap = _preset.get("cacheVariables", {})
            if _cacheMap.get("CE_GAME_NAME") == gameName and "CE_ENGINE_START_SCENE" not in _cacheMap:
                _configurePresetName = _preset.get("name", "")
                break

        if not _configurePresetName:
            raise ProjectManagerError(
                f"No configure preset found for game {gameName}. How to fix: create a preset with CE_GAME_NAME={gameName}."
            )
        return _configurePresetName

    def GetSimulatorPath(self) -> Path:
        _sdkPath = str(os.environ.get("PLAYDATE_SDK_PATH", "")).strip()
        if not _sdkPath:
            raise ProjectManagerError(
                "PLAYDATE_SDK_PATH is not set. How to fix: set PLAYDATE_SDK_PATH to your Playdate SDK install folder."
            )

        _simPath = Path(_sdkPath) / "bin" / "PlaydateSimulator.exe"
        if not _simPath.exists():
            raise ProjectManagerError(
                f"Simulator not found at {_simPath}. How to fix: verify PLAYDATE_SDK_PATH points to a valid SDK install."
            )
        return _simPath

    def _RemoveBuildArtifacts(self, gameName: str) -> None:
        _patterns = [
            f"build.*.{gameName}",
            f"{gameName}.pdx",
            f"{gameName}_DEVICE.pdx",
        ]
        for _pattern in _patterns:
            for _path in self._paths.projectRoot.glob(_pattern):
                if _path.is_dir():
                    shutil.rmtree(_path, ignore_errors=True)
                elif _path.exists():
                    _path.unlink(missing_ok=True)

    def _UpdateLaunchForRename(self, oldGameName: str, newGameName: str) -> None:
        _launchPath = self._GetLaunchPath()
        _launchMap = self._LoadJson(_launchPath)
        _configsArray = _launchMap.get("configurations", [])
        for _config in _configsArray:
            _configText = json.dumps(_config)
            if oldGameName not in _configText:
                continue
            _configString = json.dumps(_config)
            _configString = _configString.replace(oldGameName, newGameName)
            _updatedConfig = json.loads(_configString)
            _config.clear()
            _config.update(_updatedConfig)
        self._SaveJson(_launchPath, _launchMap)

    def _UpdateLaunchForDelete(self, gameName: str) -> None:
        _launchPath = self._GetLaunchPath()
        _launchMap = self._LoadJson(_launchPath)
        _configsArray = _launchMap.get("configurations", [])
        _filteredArray = []
        for _config in _configsArray:
            _configText = json.dumps(_config)
            if gameName not in _configText:
                _filteredArray.append(_config)
        _launchMap["configurations"] = _filteredArray
        self._SaveJson(_launchPath, _launchMap)

    def _CloneLaunchForGame(self, sourceGameName: str, newGameName: str) -> None:
        _launchPath = self._GetLaunchPath()
        _launchMap = self._LoadJson(_launchPath)
        _configsArray = _launchMap.get("configurations", [])
        _newConfigsArray = []

        for _config in _configsArray:
            _configText = json.dumps(_config)
            if sourceGameName not in _configText:
                continue
            _newConfigString = _configText.replace(sourceGameName, newGameName)
            _newConfigsArray.append(json.loads(_newConfigString))

        _configsArray.extend(_newConfigsArray)
        _launchMap["configurations"] = _configsArray
        self._SaveJson(_launchPath, _launchMap)

    def _UpdateCMakeForRename(self, oldGameName: str, newGameName: str) -> None:
        _presetsPath = self._GetCMakePresetsPath()
        _presetsMap = self._LoadJson(_presetsPath)

        for _key in ["configurePresets", "buildPresets"]:
            _presetArray = _presetsMap.get(_key, [])
            for _preset in _presetArray:
                _presetString = json.dumps(_preset)
                if oldGameName not in _presetString:
                    continue
                _updatedString = _presetString.replace(oldGameName, newGameName)
                _updatedPreset = json.loads(_updatedString)
                _preset.clear()
                _preset.update(_updatedPreset)

        self._SaveJson(_presetsPath, _presetsMap)

    def _UpdateCMakeForDelete(self, gameName: str) -> None:
        _presetsPath = self._GetCMakePresetsPath()
        _presetsMap = self._LoadJson(_presetsPath)

        for _key in ["configurePresets", "buildPresets"]:
            _presetArray = _presetsMap.get(_key, [])
            _filteredArray = []
            for _preset in _presetArray:
                _presetText = json.dumps(_preset)
                if gameName not in _presetText:
                    _filteredArray.append(_preset)
            _presetsMap[_key] = _filteredArray

        self._SaveJson(_presetsPath, _presetsMap)

    def _CloneCMakeForGame(self, sourceGameName: str, newGameName: str) -> None:
        _presetsPath = self._GetCMakePresetsPath()
        _presetsMap = self._LoadJson(_presetsPath)

        _newConfigureArray = []
        _newBuildArray = []
        for _preset in _presetsMap.get("configurePresets", []):
            _presetText = json.dumps(_preset)
            if sourceGameName not in _presetText:
                continue
            _newConfigureArray.append(json.loads(_presetText.replace(sourceGameName, newGameName)))

        for _preset in _presetsMap.get("buildPresets", []):
            _presetText = json.dumps(_preset)
            if sourceGameName not in _presetText:
                continue
            _newBuildArray.append(json.loads(_presetText.replace(sourceGameName, newGameName)))

        _presetsMap["configurePresets"].extend(_newConfigureArray)
        _presetsMap["buildPresets"].extend(_newBuildArray)
        self._SaveJson(_presetsPath, _presetsMap)

    def AddNewGame(self, newGameName: str, templateGameName: str) -> str:
        self._ValidateGameName(newGameName)
        self._ValidateGameName(templateGameName)

        _sourcePath = self._paths.srcRoot / templateGameName
        _targetPath = self._paths.srcRoot / newGameName

        if not _sourcePath.exists():
            raise ProjectManagerError(
                f"Template game {templateGameName} does not exist. How to fix: choose an existing game from src."
            )
        if _targetPath.exists():
            raise ProjectManagerError(
                f"Game {newGameName} already exists. How to fix: choose a different game name."
            )

        shutil.copytree(_sourcePath, _targetPath)
        self._CloneCMakeForGame(templateGameName, newGameName)
        self._CloneLaunchForGame(templateGameName, newGameName)
        self._SaveCurrentGame(newGameName)
        return f"Added game {newGameName} from template {templateGameName}."

    def CloneGame(self, sourceGameName: str, newGameName: str) -> str:
        return self.AddNewGame(newGameName, sourceGameName)

    def RenameGame(self, oldGameName: str, newGameName: str) -> str:
        self._ValidateGameName(oldGameName)
        self._ValidateGameName(newGameName)

        _oldPath = self._paths.srcRoot / oldGameName
        _newPath = self._paths.srcRoot / newGameName

        if not _oldPath.exists():
            raise ProjectManagerError(
                f"Game {oldGameName} does not exist. How to fix: select an existing game from the list."
            )
        if _newPath.exists():
            raise ProjectManagerError(
                f"Game {newGameName} already exists. How to fix: select a different game name."
            )

        _oldPath.rename(_newPath)
        self._UpdateCMakeForRename(oldGameName, newGameName)
        self._UpdateLaunchForRename(oldGameName, newGameName)
        self._RemoveBuildArtifacts(oldGameName)

        if self.GetCurrentGame() == oldGameName:
            self._SaveCurrentGame(newGameName)

        return f"Renamed game {oldGameName} to {newGameName}."

    def DeleteGame(self, gameName: str) -> str:
        self._ValidateGameName(gameName)
        _targetPath = self._paths.srcRoot / gameName
        if not _targetPath.exists():
            raise ProjectManagerError(
                f"Game {gameName} does not exist. How to fix: refresh games and try again."
            )

        shutil.rmtree(_targetPath)
        self._UpdateCMakeForDelete(gameName)
        self._UpdateLaunchForDelete(gameName)
        self._RemoveBuildArtifacts(gameName)

        _gamesArray = self.ListGames()
        if _gamesArray:
            self._SaveCurrentGame(_gamesArray[0])
        else:
            self._SaveCurrentGame("")

        return f"Deleted game {gameName}."

    def _SceneFileNameFromScene(self, sceneName: str) -> str:
        return sceneName.lower() + ".c"

    def _FindSceneFilePath(self, gameName: str, sceneName: str) -> Optional[Path]:
        _sceneFolderPath = self._GetScenesFolderPath(gameName)
        _candidatePath = _sceneFolderPath / self._SceneFileNameFromScene(sceneName)
        if _candidatePath.exists():
            return _candidatePath

        _pattern = re.compile(rf"CE_DECLARE_SCENE_CREATE_FUNCTION\({sceneName}\)")
        for _path in _sceneFolderPath.glob("*.c"):
            _content = _path.read_text(encoding="utf-8")
            if _pattern.search(_content):
                return _path
        return None

    def _AddSceneDeclarationToHeader(self, headerPath: Path, sceneName: str) -> None:
        _content = headerPath.read_text(encoding="utf-8")
        _declaration = f"CE_DECLARE_SCENE({sceneName})"
        if _declaration in _content:
            return

        _insertMatch = re.search(r"\n#ifndef\s+CE_ENGINE_SET_START_SCENE", _content)
        if _insertMatch:
            _index = _insertMatch.start()
            _updated = _content[:_index].rstrip() + "\n" + _declaration + "\n\n" + _content[_index:]
            headerPath.write_text(_updated, encoding="utf-8")
            return

        _endifMatch = re.search(r"\n#endif\s*$", _content)
        if _endifMatch:
            _index = _endifMatch.start()
            _updated = _content[:_index].rstrip() + "\n\n" + _declaration + "\n" + _content[_index:]
            headerPath.write_text(_updated, encoding="utf-8")
            return

        raise ProjectManagerError(
            "Could not locate a safe insertion point in scenes.h. How to fix: ensure scenes.h includes #ifndef CE_ENGINE_SET_START_SCENE or a final #endif block."
        )

    def _RemoveSceneDeclarationFromHeader(self, headerPath: Path, sceneName: str) -> None:
        _content = headerPath.read_text(encoding="utf-8")
        _updated = re.sub(rf"^\s*CE_DECLARE_SCENE\({sceneName}\)\s*\n", "", _content, flags=re.MULTILINE)
        headerPath.write_text(_updated, encoding="utf-8")

    def AddScene(self, gameName: str, newSceneName: str, templateSceneName: str = "") -> str:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(newSceneName)

        _sceneFolderPath = self._GetScenesFolderPath(gameName)
        _headerPath = self._GetScenesHeaderPath(gameName)
        _newFilePath = _sceneFolderPath / self._SceneFileNameFromScene(newSceneName)

        if _newFilePath.exists():
            raise ProjectManagerError(
                f"Scene file already exists for {newSceneName}. How to fix: pick a different scene name."
            )

        if templateSceneName:
            self._ValidateSceneName(templateSceneName)
            _templatePath = self._FindSceneFilePath(gameName, templateSceneName)
            if _templatePath is None:
                raise ProjectManagerError(
                    f"Template scene {templateSceneName} does not exist. How to fix: choose a scene from the current game."
                )
            _content = _templatePath.read_text(encoding="utf-8").replace(templateSceneName, newSceneName)
        else:
            _content = (
                "#include \"engine/corgo.h\"\n"
                "#include \"engine/shortcuts/scene.h\"\n\n"
                f"CE_DECLARE_SCENE_CREATE_FUNCTION({newSceneName})\n"
                "{\n"
                "    return CE_OK;\n"
                "}\n\n"
                f"CE_DECLARE_SCENE_RUN_FUNCTION({newSceneName})\n"
                "{\n"
                "    return CE_OK;\n"
                "}\n\n"
                f"CE_GENERATE_SCENE({newSceneName}, CE_INVALID_TYPE_ID)\n"
            )

        _newFilePath.write_text(_content, encoding="utf-8")
        self._AddSceneDeclarationToHeader(_headerPath, newSceneName)
        return f"Added scene {newSceneName} to game {gameName}."

    def SetStartScene(self, gameName: str, sceneName: str) -> str:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(sceneName)

        _scenesArray = self.ListScenes(gameName)
        if sceneName not in _scenesArray:
            raise ProjectManagerError(
                f"Scene {sceneName} does not exist in game {gameName}. How to fix: choose a valid scene from the list."
            )

        if self._FindSceneFilePath(gameName, sceneName) is None:
            raise ProjectManagerError(
                f"Scene {sceneName} is declared but its file is missing in game {gameName}. "
                f"How to fix: add {sceneName.lower()}.c under src/{gameName}/scenes or remove the declaration from scenes.h."
            )

        _headerPath = self._GetScenesHeaderPath(gameName)
        _headerContent = _headerPath.read_text(encoding="utf-8")
        _pattern = re.compile(r"#define\s+CE_ENGINE_SET_START_SCENE\s+\w+")

        if _pattern.search(_headerContent):
            _updated = _pattern.sub(f"#define CE_ENGINE_SET_START_SCENE {sceneName}", _headerContent)
        else:
            _insertMatch = re.search(r"#endif\s*$", _headerContent)
            if not _insertMatch:
                raise ProjectManagerError(
                    "Could not update start scene in scenes.h. How to fix: ensure scenes.h has a trailing #endif block."
                )
            _index = _insertMatch.start()
            _updated = (
                _headerContent[:_index].rstrip()
                + "\n\n#ifndef CE_ENGINE_SET_START_SCENE\n"
                + f"#define CE_ENGINE_SET_START_SCENE {sceneName}\n"
                + "#endif\n\n"
                + _headerContent[_index:]
            )

        _headerPath.write_text(_updated, encoding="utf-8")
        return f"Set start scene to {sceneName} for game {gameName}."

    def RemoveSceneDeclaration(self, gameName: str, sceneName: str) -> str:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(sceneName)

        _headerPath = self._GetScenesHeaderPath(gameName)
        if not _headerPath.exists():
            raise ProjectManagerError(
                f"Missing scenes.h for game {gameName}. How to fix: create {gameName}/scenes.h in src."
            )

        self._RemoveSceneDeclarationFromHeader(_headerPath, sceneName)
        return f"Removed missing scene declaration {sceneName} from game {gameName}."

    def CreateEmptyGame(self, newGameName: str) -> str:
        self._ValidateGameName(newGameName)

        _newGamePath = self._paths.srcRoot / newGameName
        if _newGamePath.exists():
            raise ProjectManagerError(
                f"Game {newGameName} already exists. How to fix: choose a different game name."
            )

        _newGamePath.mkdir(parents=True, exist_ok=False)
        (_newGamePath / "scenes").mkdir(parents=True, exist_ok=True)

        _defaultScene = "MainScene"
        _headerContent = (
            "#ifndef CORGO_GAME_SCENES_H\n"
            "#define CORGO_GAME_SCENES_H\n"
            "#include \"engine/core/scene.h\"\n\n"
            f"CE_DECLARE_SCENE({_defaultScene})\n\n"
            "#ifndef CE_ENGINE_SET_START_SCENE\n"
            f"#define CE_ENGINE_SET_START_SCENE {_defaultScene}\n"
            "#endif\n\n"
            "#endif\n"
        )
        (_newGamePath / "scenes.h").write_text(_headerContent, encoding="utf-8")

        _sceneContent = (
            "#include \"engine/corgo.h\"\n"
            "#include \"engine/shortcuts/scene.h\"\n\n"
            f"CE_DECLARE_SCENE_CREATE_FUNCTION({_defaultScene})\n"
            "{\n"
            "    return CE_OK;\n"
            "}\n\n"
            f"CE_DECLARE_SCENE_RUN_FUNCTION({_defaultScene})\n"
            "{\n"
            "    return CE_OK;\n"
            "}\n\n"
            f"CE_GENERATE_SCENE({_defaultScene}, CE_INVALID_TYPE_ID)\n"
        )
        (_newGamePath / "scenes" / "mainscene.c").write_text(_sceneContent, encoding="utf-8")

        _existingGames = [name for name in self.ListGames() if name != newGameName]
        if _existingGames:
            _templateGameName = _existingGames[0]
            self._CloneCMakeForGame(_templateGameName, newGameName)
            self._CloneLaunchForGame(_templateGameName, newGameName)

        self._SaveCurrentGame(newGameName)
        return f"Created empty game {newGameName}."

    def CloneScene(self, gameName: str, sourceSceneName: str, newSceneName: str) -> str:
        return self.AddScene(gameName, newSceneName, sourceSceneName)

    def RenameScene(self, gameName: str, oldSceneName: str, newSceneName: str) -> str:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(oldSceneName)
        self._ValidateSceneName(newSceneName)

        _scenePath = self._FindSceneFilePath(gameName, oldSceneName)
        if _scenePath is None:
            raise ProjectManagerError(
                f"Scene {oldSceneName} does not exist. How to fix: pick an existing scene from the list."
            )

        _content = _scenePath.read_text(encoding="utf-8").replace(oldSceneName, newSceneName)
        _newScenePath = _scenePath.parent / self._SceneFileNameFromScene(newSceneName)
        _scenePath.unlink(missing_ok=True)
        _newScenePath.write_text(_content, encoding="utf-8")

        _headerPath = self._GetScenesHeaderPath(gameName)
        _headerContent = _headerPath.read_text(encoding="utf-8").replace(oldSceneName, newSceneName)
        _headerPath.write_text(_headerContent, encoding="utf-8")

        _presetsPath = self._GetCMakePresetsPath()
        _presetsMap = self._LoadJson(_presetsPath)
        for _preset in _presetsMap.get("configurePresets", []):
            _cacheMap = _preset.get("cacheVariables", {})
            if _cacheMap.get("CE_GAME_NAME") == gameName and _cacheMap.get("CE_ENGINE_START_SCENE") == oldSceneName:
                _cacheMap["CE_ENGINE_START_SCENE"] = newSceneName
                if "name" in _preset:
                    _preset["name"] = str(_preset["name"]).replace(oldSceneName.lower(), newSceneName.lower())
                if "displayName" in _preset:
                    _preset["displayName"] = str(_preset["displayName"]).replace(oldSceneName, newSceneName)
                if "description" in _preset:
                    _preset["description"] = str(_preset["description"]).replace(oldSceneName, newSceneName)

        for _preset in _presetsMap.get("buildPresets", []):
            if oldSceneName.lower() in str(_preset.get("name", "")):
                _preset["name"] = str(_preset["name"]).replace(oldSceneName.lower(), newSceneName.lower())
            if oldSceneName in str(_preset.get("displayName", "")):
                _preset["displayName"] = str(_preset["displayName"]).replace(oldSceneName, newSceneName)
            if oldSceneName.lower() in str(_preset.get("configurePreset", "")):
                _preset["configurePreset"] = str(_preset["configurePreset"]).replace(oldSceneName.lower(), newSceneName.lower())

        self._SaveJson(_presetsPath, _presetsMap)
        return f"Renamed scene {oldSceneName} to {newSceneName} in game {gameName}."

    def DeleteScene(self, gameName: str, sceneName: str) -> str:
        self._ValidateGameName(gameName)
        self._ValidateSceneName(sceneName)

        _scenePath = self._FindSceneFilePath(gameName, sceneName)
        if _scenePath is None:
            raise ProjectManagerError(
                f"Scene {sceneName} does not exist. How to fix: refresh scenes and try again."
            )

        _scenePath.unlink(missing_ok=True)
        _headerPath = self._GetScenesHeaderPath(gameName)
        self._RemoveSceneDeclarationFromHeader(_headerPath, sceneName)

        _headerContent = _headerPath.read_text(encoding="utf-8")
        _startScenePattern = re.compile(r"#define\s+CE_ENGINE_SET_START_SCENE\s+(\w+)")
        _startSceneGuardBlockPattern = re.compile(
            r"\n#ifndef\s+CE_ENGINE_SET_START_SCENE\s*\n"
            r"#define\s+CE_ENGINE_SET_START_SCENE\s+\w+\s*\n"
            r"#endif\s*\n?",
            flags=re.MULTILINE,
        )
        _startSceneMatch = _startScenePattern.search(_headerContent)
        if _startSceneMatch and _startSceneMatch.group(1) == sceneName:
            _remainingScenes = self.ListScenes(gameName)
            if _remainingScenes:
                _headerContent = _startScenePattern.sub(
                    f"#define CE_ENGINE_SET_START_SCENE {_remainingScenes[0]}", _headerContent
                )
            else:
                _headerContent = _startSceneGuardBlockPattern.sub("\n", _headerContent)
            _headerPath.write_text(_headerContent, encoding="utf-8")

        _presetsPath = self._GetCMakePresetsPath()
        _presetsMap = self._LoadJson(_presetsPath)
        _removedConfigurePresetNames = set()
        _removedConfigureCount = 0
        _filteredConfigureArray = []
        for _preset in _presetsMap.get("configurePresets", []):
            _cacheMap = _preset.get("cacheVariables", {})
            if _cacheMap.get("CE_GAME_NAME") == gameName and _cacheMap.get("CE_ENGINE_START_SCENE") == sceneName:
                _removedConfigurePresetName = str(_preset.get("name", "")).strip()
                if _removedConfigurePresetName:
                    _removedConfigurePresetNames.add(_removedConfigurePresetName)
                _removedConfigureCount += 1
                continue
            _filteredConfigureArray.append(_preset)
        _presetsMap["configurePresets"] = _filteredConfigureArray

        _removedBuildCount = 0
        _filteredBuildArray = []
        for _preset in _presetsMap.get("buildPresets", []):
            _configurePresetName = str(_preset.get("configurePreset", "")).strip()
            _buildPresetText = json.dumps(_preset)
            _isLinkedToRemovedConfigure = _configurePresetName in _removedConfigurePresetNames
            _looksLikeDeletedScenePreset = sceneName.lower() in str(_preset.get("name", "")) and gameName in _buildPresetText
            if _isLinkedToRemovedConfigure or _looksLikeDeletedScenePreset:
                _removedBuildCount += 1
                continue
            _filteredBuildArray.append(_preset)
        _presetsMap["buildPresets"] = _filteredBuildArray

        self._SaveJson(_presetsPath, _presetsMap)
        return (
            f"Deleted scene {sceneName} from game {gameName}. "
            f"Removed {_removedConfigureCount} configure preset(s) and {_removedBuildCount} build preset(s)."
        )

    def SwitchGame(self, gameName: str) -> str:
        self._ValidateGameName(gameName)
        if gameName not in self.ListGames():
            raise ProjectManagerError(
                f"Game {gameName} does not exist. How to fix: add the game first or refresh."
            )

        _settingsPath = self._GetSettingsPath()
        _settingsMap = self._LoadJson(_settingsPath)

        _presetsMap = self._LoadJson(self._GetCMakePresetsPath())
        _configurePresetName = ""
        _buildPresetName = ""

        for _preset in _presetsMap.get("configurePresets", []):
            _cacheMap = _preset.get("cacheVariables", {})
            if _cacheMap.get("CE_GAME_NAME") == gameName and "CE_ENGINE_START_SCENE" not in _cacheMap:
                _configurePresetName = _preset.get("name", "")
                break

        for _preset in _presetsMap.get("buildPresets", []):
            if _preset.get("configurePreset") == _configurePresetName:
                _buildPresetName = _preset.get("name", "")
                break

        if not _configurePresetName:
            raise ProjectManagerError(
                f"No configure preset found for game {gameName}. How to fix: create a preset with CE_GAME_NAME={gameName}."
            )

        _settingsMap["cmake.configurePreset"] = _configurePresetName
        if _buildPresetName:
            _settingsMap["cmake.buildPreset"] = _buildPresetName
        self._SaveJson(_settingsPath, _settingsMap)
        self._SaveCurrentGame(gameName)

        return f"Switched active game to {gameName}."

    def RenameProject(self, newProjectName: str, renameFolder: bool) -> str:
        self._ValidateProjectName(newProjectName)
        _oldProjectName = self._workspaceRoot.name

        self._ReplaceProjectNameInWorkspace(_oldProjectName, newProjectName)

        _workspaceFile = self._workspaceRoot / f"{_oldProjectName}.code-workspace"
        if _workspaceFile.exists():
            _workspaceFile.rename(self._workspaceRoot / f"{newProjectName}.code-workspace")

        if not renameFolder:
            return (
                f"Updated project references from {_oldProjectName} to {newProjectName}. "
                "Workspace folder rename was skipped."
            )

        _targetPath = self._workspaceRoot.parent / newProjectName
        if _targetPath.exists():
            raise ProjectManagerError(
                f"Target folder {_targetPath} already exists. How to fix: choose a different project name or remove the existing folder."
            )

        shutil.move(str(self._workspaceRoot), str(_targetPath))
        return (
            f"Renamed project folder to {newProjectName}. "
            "How to finish: reopen the renamed workspace in VS Code."
        )

    def RenameProjectFolder(self, oldProjectName: str, newProjectName: str) -> str:
        self._ValidateProjectName(oldProjectName)
        self._ValidateProjectName(newProjectName)

        _oldPath = self._workspaceRoot / oldProjectName
        _newPath = self._workspaceRoot / newProjectName
        if not _oldPath.exists():
            raise ProjectManagerError(
                f"Project {oldProjectName} does not exist. How to fix: refresh and try again."
            )
        if _newPath.exists():
            raise ProjectManagerError(
                f"Project {newProjectName} already exists. How to fix: choose a different name."
            )

        _oldPath.rename(_newPath)

        _settingsPath = self._GetSettingsPath()
        _settingsMap = self._LoadJson(_settingsPath)
        _updatedSettings = self._ReplaceWorkspaceProjectPath(_settingsMap, oldProjectName, newProjectName)
        self._SaveJson(_settingsPath, _updatedSettings)

        _launchPath = self._GetLaunchPath()
        _launchMap = self._LoadJson(_launchPath)
        _updatedLaunch = self._ReplaceWorkspaceProjectPath(_launchMap, oldProjectName, newProjectName)
        self._SaveJson(_launchPath, _updatedLaunch)

        _savedProjectFolder = str(self._config.get("projectFolder", "")).strip()
        if not _savedProjectFolder or _savedProjectFolder == oldProjectName or self._paths.projectRoot.name == oldProjectName:
            self._config["projectFolder"] = newProjectName
            self._SaveConfig(self._config)

        return f"Renamed project {oldProjectName} to {newProjectName}."

    def CloneProjectFolder(self, sourceProjectName: str, newProjectName: str) -> str:
        self._ValidateProjectName(sourceProjectName)
        self._ValidateProjectName(newProjectName)

        _sourcePath = self._workspaceRoot / sourceProjectName
        _targetPath = self._workspaceRoot / newProjectName
        if not _sourcePath.exists():
            raise ProjectManagerError(
                f"Project {sourceProjectName} does not exist. How to fix: refresh and choose an existing project."
            )
        if _targetPath.exists():
            raise ProjectManagerError(
                f"Project {newProjectName} already exists. How to fix: choose a different name."
            )

        shutil.copytree(_sourcePath, _targetPath, ignore=self._ProjectCloneIgnore)
        return f"Cloned project {sourceProjectName} to {newProjectName}."

    def _ReplaceProjectNameInWorkspace(self, oldProjectName: str, newProjectName: str) -> None:
        _allowedSuffixes = {
            ".md",
            ".json",
            ".txt",
            ".cmake",
            ".py",
            ".ps1",
            ".yml",
            ".yaml",
            ".c",
            ".h",
            ".code-workspace",
        }
        _skipFolders = {".git", ".vs", ".vscode-test", "build", "build.vs2022.corgogame", "tools/bin", "__pycache__"}

        for _path in self._workspaceRoot.rglob("*"):
            if not _path.is_file():
                continue
            if any(_part in _skipFolders for _part in _path.parts):
                continue
            if _path.suffix not in _allowedSuffixes and _path.name not in {"CMakeLists.txt", "CMakePresets.json"}:
                continue

            _content = _path.read_text(encoding="utf-8", errors="ignore")
            if oldProjectName not in _content:
                continue
            _updated = _content.replace(oldProjectName, newProjectName)
            _path.write_text(_updated, encoding="utf-8")

    def CloneProject(self, destinationFolder: Path, newProjectName: str) -> str:
        self._ValidateProjectName(newProjectName)
        _destinationFolder = destinationFolder.resolve()
        if not _destinationFolder.exists():
            raise ProjectManagerError(
                "Destination folder does not exist. How to fix: choose an existing folder path."
            )

        _targetPath = _destinationFolder / newProjectName
        if _targetPath.exists():
            raise ProjectManagerError(
                f"Target folder {_targetPath} already exists. How to fix: choose a different project name."
            )

        def _IgnoreWorkspaceClone(directoryPath: str, namesArray: List[str]) -> set[str]:
            _ignoredNames = self._ProjectCloneIgnore(directoryPath, namesArray)
            _ignoredNames.update(
                shutil.ignore_patterns(
                    ".git",
                    "tools/bin",
                )(directoryPath, namesArray)
            )
            return _ignoredNames

        shutil.copytree(self._workspaceRoot, _targetPath, ignore=_IgnoreWorkspaceClone)

        _oldProjectName = self._workspaceRoot.name
        _cloneConfigPath = _targetPath / "tools" / "project-manager" / "project_manager_config.json"
        _cloneService = ProjectManagerService(_targetPath, _cloneConfigPath)
        _cloneService._ReplaceProjectNameInWorkspace(_oldProjectName, newProjectName)

        _cloneService._config["projectFolder"] = _cloneService._paths.projectRoot.name
        _cloneService._SaveConfig(_cloneService._config)

        _workspaceFile = _targetPath / f"{_oldProjectName}.code-workspace"
        if _workspaceFile.exists():
            _workspaceFile.rename(_targetPath / f"{newProjectName}.code-workspace")

        return f"Cloned project to {_targetPath}."
