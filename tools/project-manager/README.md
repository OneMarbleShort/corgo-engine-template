# Project Manager Tool

This tool manages Corgo project structure operations from a compact Kivy UI.

## Features
- Rename project references and optionally rename workspace folder
- Clone workspace as a new project
- Add, clone, rename, delete, and switch games
- Add, clone, rename, and delete scenes
- Update CMake presets and VS Code launch/settings files when operations change project state

## Run
1. Open a shell in this folder
2. Run:

```
python run_project_manager.py
```

The launcher auto-installs Kivy if needed.
Use Python 3.11, 3.12, or 3.13 on Windows.

## Build EXE
Run:

```
powershell -ExecutionPolicy Bypass -File .\build_tool.ps1
```

Output goes to tools/bin/project-manager.
The build script auto-selects Python 3.13, 3.12, or 3.11 when available.

## Test
Run:

```
pytest -q
```
