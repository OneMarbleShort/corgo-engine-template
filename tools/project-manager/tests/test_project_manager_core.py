import json
from pathlib import Path

from project_manager.main import _LooksLikeWorkspaceRoot
from project_manager.core import ProjectManagerService


def _WriteJson(filePath: Path, dataMap: dict) -> None:
    filePath.parent.mkdir(parents=True, exist_ok=True)
    filePath.write_text(json.dumps(dataMap, indent=2), encoding="utf-8")


def _WriteText(filePath: Path, content: str) -> None:
    filePath.parent.mkdir(parents=True, exist_ok=True)
    filePath.write_text(content, encoding="utf-8")


def _CreateSceneHeader(defaultSceneName: str, secondSceneName: str) -> str:
    return (
        "#ifndef CORGO_GAME_SCENES_H\n"
        "#define CORGO_GAME_SCENES_H\n"
        "#include \"engine/core/scene.h\"\n\n"
        f"CE_DECLARE_SCENE({defaultSceneName})\n"
        f"CE_DECLARE_SCENE({secondSceneName})\n\n"
        "#ifndef CE_ENGINE_SET_START_SCENE\n"
        f"#define CE_ENGINE_SET_START_SCENE {defaultSceneName}\n"
        "#endif\n\n"
        "#endif\n"
    )


def _CreateSceneFile(sceneName: str) -> str:
    return (
        "#include \"engine/corgo.h\"\n"
        "#include \"engine/shortcuts/scene.h\"\n\n"
        f"CE_DECLARE_SCENE_CREATE_FUNCTION({sceneName})\n"
        "{\n"
        "    return CE_OK;\n"
        "}\n\n"
        f"CE_DECLARE_SCENE_RUN_FUNCTION({sceneName})\n"
        "{\n"
        "    return CE_OK;\n"
        "}\n\n"
        f"CE_GENERATE_SCENE({sceneName}, CE_INVALID_TYPE_ID)\n"
    )


def _CreateFixtureWorkspace(tmpPath: Path) -> Path:
    _workspaceRoot = tmpPath / "corgo-engine-template"
    _projectRoot = _workspaceRoot / "corgogame"
    _srcRoot = _projectRoot / "src"

    _WriteJson(
        _workspaceRoot / ".vscode" / "settings.json",
        {
            "cmake.sourceDirectory": "${workspaceFolder}/corgogame/",
            "cmake.configurePreset": "corgogame-vs2022-sim",
            "cmake.buildPreset": "build-corgogame-vs2022-sim",
        },
    )
    _WriteJson(
        _workspaceRoot / ".vscode" / "launch.json",
        {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Build and Run Simulator (corgogame)",
                    "args": ["${workspaceFolder}/corgogame/corgogame.pdx"],
                },
                {
                    "name": "Build and Run Simulator (corgogame2)",
                    "args": ["${workspaceFolder}/corgogame/corgogame2.pdx"],
                },
            ],
        },
    )
    _WriteJson(
        _projectRoot / "CMakePresets.json",
        {
            "version": 6,
            "configurePresets": [
                {"name": "vs2022-sim", "binaryDir": "${sourceDir}/build.vs2022", "hidden": True},
                {
                    "name": "corgogame-vs2022-sim",
                    "binaryDir": "${sourceDir}/build.vs2022.corgogame",
                    "cacheVariables": {"CE_GAME_NAME": "corgogame"},
                },
                {
                    "name": "corgogame-vs2022-sim-hellocorgo",
                    "binaryDir": "${sourceDir}/build.vs2022.corgogame",
                    "cacheVariables": {"CE_GAME_NAME": "corgogame", "CE_ENGINE_START_SCENE": "HelloCorgo"},
                    "displayName": "VS2022 Simulator (corgogame: HelloCorgo)",
                    "description": "Builds src/corgogame/ with HelloCorgo as start scene.",
                },
                {
                    "name": "corgogame2-vs2022-sim",
                    "binaryDir": "${sourceDir}/build.vs2022.corgogame2",
                    "cacheVariables": {"CE_GAME_NAME": "corgogame2"},
                },
            ],
            "buildPresets": [
                {
                    "name": "build-corgogame-vs2022-sim",
                    "configurePreset": "corgogame-vs2022-sim",
                    "displayName": "Build VS2022 Simulator (corgogame)",
                },
                {
                    "name": "build-corgogame-vs2022-sim-hellocorgo",
                    "configurePreset": "corgogame-vs2022-sim-hellocorgo",
                    "displayName": "Build VS2022 Simulator (corgogame: HelloCorgo)",
                },
                {
                    "name": "build-corgogame2-vs2022-sim",
                    "configurePreset": "corgogame2-vs2022-sim",
                    "displayName": "Build VS2022 Simulator (corgogame2)",
                },
            ],
        },
    )

    _WriteText(_workspaceRoot / "README.md", "# corgo-engine-template\n")
    _WriteText(_workspaceRoot / "corgo-engine-template.code-workspace", "name: corgo-engine-template\n")

    for _gameName, _sceneB in [("corgogame", "HelloCorgoS2"), ("corgogame2", "HelloAlt")]:
        _gameRoot = _srcRoot / _gameName
        _WriteText(_gameRoot / "scenes.h", _CreateSceneHeader("HelloCorgo", _sceneB))
        _WriteText(_gameRoot / "scenes" / "hellocorgo.c", _CreateSceneFile("HelloCorgo"))
        _WriteText(_gameRoot / "scenes" / f"{_sceneB.lower()}.c", _CreateSceneFile(_sceneB))

    return _workspaceRoot


def _CreateService(workspaceRoot: Path) -> ProjectManagerService:
    _configPath = workspaceRoot / "tools" / "project-manager" / "project_manager_config.json"
    _configPath.parent.mkdir(parents=True, exist_ok=True)
    _configPath.write_text('{"currentGame": ""}', encoding="utf-8")
    return ProjectManagerService(workspaceRoot, _configPath)


def test_switch_game_updates_settings(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.SwitchGame("corgogame2")

    _settings = json.loads((_workspaceRoot / ".vscode" / "settings.json").read_text(encoding="utf-8"))
    assert "Switched active game" in _result
    assert _settings["cmake.configurePreset"] == "corgogame2-vs2022-sim"
    assert _settings["cmake.buildPreset"] == "build-corgogame2-vs2022-sim"


def test_add_new_game_clones_structures_and_configs(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.AddNewGame("mygame", "corgogame")

    _presets = json.loads((_workspaceRoot / "corgogame" / "CMakePresets.json").read_text(encoding="utf-8"))
    _launch = json.loads((_workspaceRoot / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    assert "Added game mygame" in _result
    assert (_workspaceRoot / "corgogame" / "src" / "mygame").exists()
    assert any(_preset.get("cacheVariables", {}).get("CE_GAME_NAME") == "mygame" for _preset in _presets["configurePresets"])
    assert any("mygame" in json.dumps(_config) for _config in _launch["configurations"])


def test_clone_game_creates_distinct_copy(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.CloneGame("corgogame2", "myclone")

    assert "Added game myclone" in _result
    assert (_workspaceRoot / "corgogame" / "src" / "myclone").exists()


def test_rename_game_updates_configs_and_folder(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.RenameGame("corgogame2", "renamedgame")

    _presetsText = (_workspaceRoot / "corgogame" / "CMakePresets.json").read_text(encoding="utf-8")
    _launchText = (_workspaceRoot / ".vscode" / "launch.json").read_text(encoding="utf-8")
    assert "Renamed game corgogame2" in _result
    assert (_workspaceRoot / "corgogame" / "src" / "renamedgame").exists()
    assert "corgogame2" not in _presetsText
    assert "corgogame2" not in _launchText


def test_delete_game_removes_configs_and_folder(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.DeleteGame("corgogame2")

    _presetsText = (_workspaceRoot / "corgogame" / "CMakePresets.json").read_text(encoding="utf-8")
    _launchText = (_workspaceRoot / ".vscode" / "launch.json").read_text(encoding="utf-8")
    assert "Deleted game corgogame2" in _result
    assert not (_workspaceRoot / "corgogame" / "src" / "corgogame2").exists()
    assert "corgogame2" not in _presetsText
    assert "corgogame2" not in _launchText


def test_add_scene_updates_header_and_file(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.AddScene("corgogame", "MainMenu")

    _headerText = (_workspaceRoot / "corgogame" / "src" / "corgogame" / "scenes.h").read_text(encoding="utf-8")
    assert "Added scene MainMenu" in _result
    assert "CE_DECLARE_SCENE(MainMenu)" in _headerText
    assert (_workspaceRoot / "corgogame" / "src" / "corgogame" / "scenes" / "mainmenu.c").exists()


def test_clone_scene_copies_content(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.CloneScene("corgogame", "HelloCorgo", "HelloClone")

    _sceneText = (_workspaceRoot / "corgogame" / "src" / "corgogame" / "scenes" / "helloclone.c").read_text(encoding="utf-8")
    assert "Added scene HelloClone" in _result
    assert "HelloClone" in _sceneText
    assert "HelloCorgo" not in _sceneText


def test_rename_scene_updates_header_and_presets(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.RenameScene("corgogame", "HelloCorgo", "MainMenu")

    _headerText = (_workspaceRoot / "corgogame" / "src" / "corgogame" / "scenes.h").read_text(encoding="utf-8")
    _presetsText = (_workspaceRoot / "corgogame" / "CMakePresets.json").read_text(encoding="utf-8")
    assert "Renamed scene HelloCorgo" in _result
    assert "MainMenu" in _headerText
    assert "HelloCorgo" not in _headerText
    assert "MainMenu" in _presetsText


def test_delete_scene_removes_files_and_related_scene_preset(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.DeleteScene("corgogame", "HelloCorgo")

    _headerText = (_workspaceRoot / "corgogame" / "src" / "corgogame" / "scenes.h").read_text(encoding="utf-8")
    _presetsText = (_workspaceRoot / "corgogame" / "CMakePresets.json").read_text(encoding="utf-8")
    assert "Deleted scene HelloCorgo" in _result
    assert "CE_DECLARE_SCENE(HelloCorgo)" not in _headerText
    assert "HelloCorgo" not in _presetsText


def test_rename_project_updates_references_without_folder_move(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.RenameProject("my-renamed-template", False)

    _readmeText = (_workspaceRoot / "README.md").read_text(encoding="utf-8")
    assert "Workspace folder rename was skipped" in _result
    assert "my-renamed-template" in _readmeText
    assert (_workspaceRoot / "my-renamed-template.code-workspace").exists()


def test_rename_project_folder_updates_workspace_paths(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _result = _service.RenameProjectFolder("corgogame", "renamedproject")

    _settings = json.loads((_workspaceRoot / ".vscode" / "settings.json").read_text(encoding="utf-8"))
    _launch = json.loads((_workspaceRoot / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    _config = json.loads(
        (_workspaceRoot / "tools" / "project-manager" / "project_manager_config.json").read_text(encoding="utf-8")
    )
    assert "Renamed project corgogame" in _result
    assert (_workspaceRoot / "renamedproject").exists()
    assert not (_workspaceRoot / "corgogame").exists()
    assert _settings["cmake.sourceDirectory"] == "${workspaceFolder}/renamedproject/"
    assert _launch["configurations"][0]["args"][0] == "${workspaceFolder}/renamedproject/corgogame.pdx"
    assert _config["projectFolder"] == "renamedproject"
    assert _LooksLikeWorkspaceRoot(_workspaceRoot)


def test_clone_project_copies_workspace_with_new_name(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _destination = tmp_path / "clones"
    _destination.mkdir(parents=True, exist_ok=True)
    _result = _service.CloneProject(_destination, "clone-alpha")

    _cloneRoot = _destination / "clone-alpha"
    _cloneReadme = (_cloneRoot / "README.md").read_text(encoding="utf-8")
    _cloneConfig = json.loads((_cloneRoot / "tools" / "project-manager" / "project_manager_config.json").read_text(encoding="utf-8"))
    _cloneWorkspaceText = (_cloneRoot / "clone-alpha.code-workspace").read_text(encoding="utf-8")
    assert "Cloned project" in _result
    assert _cloneRoot.exists()
    assert "clone-alpha" in _cloneReadme
    assert "corgo-engine-template" not in _cloneReadme
    assert _cloneConfig["projectFolder"] == "corgogame"
    assert "clone-alpha" in _cloneWorkspaceText
    assert "corgo-engine-template" not in _cloneWorkspaceText
    assert (_cloneRoot / "clone-alpha.code-workspace").exists()


def test_clone_project_folder_skips_build_outputs(tmp_path: Path) -> None:
    _workspaceRoot = _CreateFixtureWorkspace(tmp_path)
    _service = _CreateService(_workspaceRoot)

    _projectRoot = _workspaceRoot / "corgogame"
    _WriteText(_projectRoot / "build.vs2022.corgogame" / "stale.txt", "stale build")
    _WriteText(_projectRoot / "corgogame.pdx" / "pdxinfo", "stale pdx")
    _WriteText(_projectRoot / "Source" / "pdex.dll", "stale binary")

    _result = _service.CloneProjectFolder("corgogame", "copiedproject")

    _cloneRoot = _workspaceRoot / "copiedproject"
    assert "Cloned project corgogame to copiedproject" in _result
    assert _cloneRoot.exists()
    assert not (_cloneRoot / "build.vs2022.corgogame").exists()
    assert not (_cloneRoot / "corgogame.pdx").exists()
    assert not (_cloneRoot / "Source" / "pdex.dll").exists()
    assert (_cloneRoot / "src").exists()
