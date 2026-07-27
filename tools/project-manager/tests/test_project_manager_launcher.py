import ast
import sys
from pathlib import Path

from project_manager.launcher import BuildProjectManagerLaunchArguments


def _CreateLauncherWorkspace(tmp_path: Path) -> Path:
    _workspaceRoot = tmp_path / "clone-alpha"
    _scriptPath = _workspaceRoot / "tools" / "project-manager" / "run_project_manager.py"
    _scriptPath.parent.mkdir(parents=True, exist_ok=True)
    _scriptPath.write_text("# launcher\n", encoding="utf-8")
    return _workspaceRoot


def test_build_launch_arguments_uses_repo_script_when_not_frozen(tmp_path: Path, monkeypatch) -> None:
    _workspaceRoot = _CreateLauncherWorkspace(tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python313\python.exe")

    _commandArray, _cwd, _env = BuildProjectManagerLaunchArguments(_workspaceRoot)

    assert _commandArray == [
        r"C:\Python313\python.exe",
        str(_workspaceRoot / "tools" / "project-manager" / "run_project_manager.py"),
    ]
    assert _cwd == str(_workspaceRoot / "tools" / "project-manager")
    assert _env["CORGO_WORKSPACE_ROOT"] == str(_workspaceRoot.resolve())


def test_build_launch_arguments_reuses_current_exe_when_frozen(tmp_path: Path, monkeypatch) -> None:
    _workspaceRoot = _CreateLauncherWorkspace(tmp_path)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "tools" / "bin" / "project-manager.exe"))

    _commandArray, _cwd, _env = BuildProjectManagerLaunchArguments(_workspaceRoot)

    assert _commandArray == [str((tmp_path / "tools" / "bin" / "project-manager.exe").resolve())]
    assert _cwd == str(_workspaceRoot.resolve())
    assert _env["CORGO_WORKSPACE_ROOT"] == str(_workspaceRoot.resolve())


def test_build_launch_arguments_sets_post_clone_bootstrap_env(tmp_path: Path, monkeypatch) -> None:
    _workspaceRoot = _CreateLauncherWorkspace(tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python313\python.exe")

    _commandArray, _cwd, _env = BuildProjectManagerLaunchArguments(
        _workspaceRoot,
        runPostCloneBootstrap=True,
    )

    assert _commandArray == [
        r"C:\Python313\python.exe",
        str(_workspaceRoot / "tools" / "project-manager" / "run_project_manager.py"),
    ]
    assert _cwd == str(_workspaceRoot / "tools" / "project-manager")
    assert _env["CORGO_WORKSPACE_ROOT"] == str(_workspaceRoot.resolve())
    assert _env["CORGO_POST_CLONE_BOOTSTRAP"] == "1"


def test_clone_workspace_prompts_for_switch() -> None:
    _appPath = Path(__file__).resolve().parents[1] / "project_manager" / "app.py"
    _moduleAst = ast.parse(_appPath.read_text(encoding="utf-8"))
    _layoutNode = next(
        _node for _node in _moduleAst.body if isinstance(_node, ast.ClassDef) and _node.name == "ProjectManagerLayout"
    )
    _cloneMethod = next(
        _item for _item in _layoutNode.body if isinstance(_item, ast.FunctionDef) and _item.name == "_CloneWorkspace"
    )

    _callNames = {
        _node.func.attr
        for _node in ast.walk(_cloneMethod)
        if isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
    }
    assert "_PromptSwitchWorkspace" in _callNames