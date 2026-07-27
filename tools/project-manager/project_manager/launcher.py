import os
import subprocess
import sys
from pathlib import Path


def BuildProjectManagerLaunchArguments(
    workspaceRoot: Path,
    runPostCloneBootstrap: bool = False,
) -> tuple[list[str], str, dict[str, str]]:
    _workspaceRoot = workspaceRoot.resolve()
    _env = os.environ.copy()
    _env["CORGO_WORKSPACE_ROOT"] = str(_workspaceRoot)
    if runPostCloneBootstrap:
        _env["CORGO_POST_CLONE_BOOTSTRAP"] = "1"
    else:
        _env.pop("CORGO_POST_CLONE_BOOTSTRAP", None)

    if getattr(sys, "frozen", False):
        # Relaunching a one-file PyInstaller app from itself must reset the
        # inherited bootloader environment so the child extracts a fresh temp
        # runtime instead of reusing parent extraction paths.
        for _key in list(_env.keys()):
            if _key.startswith("_PYI") or _key == "_MEIPASS2":
                _env.pop(_key, None)
        _env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        return [str(Path(sys.executable).resolve())], str(_workspaceRoot), _env

    _scriptPath = _workspaceRoot / "tools" / "project-manager" / "run_project_manager.py"
    if not _scriptPath.exists():
        raise RuntimeError(
            f"Project manager launcher script was not found at {_scriptPath}. "
            "How to fix: ensure the cloned repo includes tools/project-manager/run_project_manager.py."
        )

    return [sys.executable, str(_scriptPath)], str(_scriptPath.parent), _env


def LaunchProjectManager(workspaceRoot: Path, runPostCloneBootstrap: bool = False) -> None:
    _commandArray, _cwd, _env = BuildProjectManagerLaunchArguments(
        workspaceRoot,
        runPostCloneBootstrap=runPostCloneBootstrap,
    )
    subprocess.Popen(_commandArray, cwd=_cwd, env=_env)