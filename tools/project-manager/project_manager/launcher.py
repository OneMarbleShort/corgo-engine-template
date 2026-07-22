import os
import subprocess
import sys
from pathlib import Path


def BuildProjectManagerLaunchArguments(workspaceRoot: Path) -> tuple[list[str], str, dict[str, str]]:
    _workspaceRoot = workspaceRoot.resolve()
    _env = os.environ.copy()
    _env["CORGO_WORKSPACE_ROOT"] = str(_workspaceRoot)

    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())], str(_workspaceRoot), _env

    _scriptPath = _workspaceRoot / "tools" / "project-manager" / "run_project_manager.py"
    if not _scriptPath.exists():
        raise RuntimeError(
            f"Project manager launcher script was not found at {_scriptPath}. "
            "How to fix: ensure the cloned repo includes tools/project-manager/run_project_manager.py."
        )

    return [sys.executable, str(_scriptPath)], str(_scriptPath.parent), _env


def LaunchProjectManager(workspaceRoot: Path) -> None:
    _commandArray, _cwd, _env = BuildProjectManagerLaunchArguments(workspaceRoot)
    subprocess.Popen(_commandArray, cwd=_cwd, env=_env)