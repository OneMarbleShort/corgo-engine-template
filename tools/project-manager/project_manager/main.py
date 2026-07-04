import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def EnsureDependencyInstalled(packageName: str) -> None:
    if getattr(sys, "frozen", False):
        return

    if packageName == "kivy" and sys.version_info >= (3, 14):
        raise RuntimeError(
            "Kivy is not currently supported in this tool on Python 3.14 on Windows. "
            "How to fix: run this tool with Python 3.11, 3.12, or 3.13."
        )

    _moduleName = packageName.split("==")[0].replace("-", "_")
    _moduleFound = importlib.util.find_spec(_moduleName) is not None
    if _moduleFound:
        return

    _commandArray = [sys.executable, "-m", "pip", "install", packageName]
    _result = subprocess.run(_commandArray, check=False, capture_output=True, text=True)
    if _result.returncode != 0:
        raise RuntimeError(
            f"Failed to install dependency {packageName}. "
            f"How to fix: run {' '.join(_commandArray)} using Python 3.11, 3.12, or 3.13. "
            f"Details: {_result.stderr}"
        )


def _LooksLikeWorkspaceRoot(candidatePath: Path) -> bool:
    if not (candidatePath / "tools" / "project-manager").exists():
        return False

    for _childPath in candidatePath.iterdir():
        if not _childPath.is_dir():
            continue
        if (_childPath / "src").exists() and (_childPath / "CMakePresets.json").exists():
            return True

    return False


def _FindWorkspaceRoot() -> Path:
    _explicitRoot = os.environ.get("CORGO_WORKSPACE_ROOT", "").strip()
    if _explicitRoot:
        _explicitPath = Path(_explicitRoot).resolve()
        if _LooksLikeWorkspaceRoot(_explicitPath):
            return _explicitPath

    _candidatesArray = [Path.cwd().resolve()]

    if getattr(sys, "frozen", False):
        _exePath = Path(sys.executable).resolve()
        _candidatesArray.append(_exePath.parent)
        _candidatesArray.extend(_exePath.parents)
    else:
        _sourcePath = Path(__file__).resolve()
        _candidatesArray.append(_sourcePath.parent.parent)
        _candidatesArray.extend(_sourcePath.parents)

    _visitedSet = set()
    for _candidate in _candidatesArray:
        _key = str(_candidate)
        if _key in _visitedSet:
            continue
        _visitedSet.add(_key)
        if _LooksLikeWorkspaceRoot(_candidate):
            return _candidate

    raise RuntimeError(
        "Could not detect workspace root. "
        "How to fix: launch the tool from your repo root or set CORGO_WORKSPACE_ROOT to the workspace path."
    )


def BootstrapAndRun() -> None:
    EnsureDependencyInstalled("kivy")

    from .app import ProjectManagerApp
    from .core import ProjectManagerService

    _workspaceRoot = _FindWorkspaceRoot()
    _configPath = _workspaceRoot / "tools" / "project-manager" / "project_manager_config.json"
    _service = ProjectManagerService(_workspaceRoot, _configPath)
    _application = ProjectManagerApp(service=_service)
    _application.run()


if __name__ == "__main__":
    BootstrapAndRun()
