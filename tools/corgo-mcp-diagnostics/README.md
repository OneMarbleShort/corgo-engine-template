# corgo-mcp-diagnostics

Read-only MCP diagnostics for Corgo Engine workspaces.

This server complements the project-manager tool by focusing on analysis and validation rather than mutating project structure.

## Tools

- `corgo_list_games_and_scenes`
  - Lists game folders under `corgogame/src`, declared scenes in each `scenes.h`, and default start scene.
- `corgo_list_presets`
  - Returns configure/build presets from `corgogame/CMakePresets.json`.
- `corgo_validate_preset_scene_consistency`
  - Checks for missing game folders, missing scene declarations, and build presets referencing missing configure presets.

## Install

```powershell
cd tools/corgo-mcp-diagnostics
npm install
```

## Quick check

```powershell
npm run self-check
npm test
```

## Run as MCP server

```powershell
npm start
```

## VS Code MCP config example

```json
{
  "servers": {
    "corgoDiagnostics": {
      "type": "stdio",
      "command": "node",
      "args": [
        "${workspaceFolder:}/tools/corgo-mcp-diagnostics/src/index.mjs"
      ]
    }
  }
}
```
