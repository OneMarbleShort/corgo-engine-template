# MCP Server Plan

This repository uses MCPs for read/query workflows and keeps creation/modification in the Project Manager tool.

## 1. Project Manager

This is the mutating surface for Corgo project structure changes.

Use it for:
- Renaming projects, games, and scenes
- Cloning projects and games
- Adding or deleting games and scenes
- Rewriting project files when names or paths change

## 2. Corgo MCP

This MCP should understand the Corgo engine codebase and answer questions about how the engine is used.

Primary goals:
- Query engine APIs, ECS types, systems, components, and build helpers
- Search the repository for examples and snippets
- Suggest where new code should live based on existing patterns
- Validate that a proposed change matches the current project structure

Suggested tools:
- `corgo_query_api`
  - Returns documentation-like answers for engine APIs, ECS helpers, game layout, and build entry points.
- `corgo_search_examples`
  - Finds examples, snippets, and nearby call sites in the repo.
- `corgo_suggest_placement`
  - Given a feature or snippet, explains where the code should go and why.
- `corgo_validate_change`
  - Checks a proposed edit against the existing code layout and build conventions.

Example behavior:
- Ask for an API and get a short usage summary plus the closest repository example.
- Ask where code should go and get a suggested module or folder, not a file write.
- Ask for snippets and get the most relevant local examples first.

## 3. Playdate MCP

This MCP should understand the Playdate SDK and platform conventions.

Primary goals:
- Query Playdate C API and SDK usage
- Return examples for `pd_api.h`, `pdc`, `pdxinfo`, simulator/device workflows, and packaging
- Suggest where Playdate-specific code belongs in the repo
- Validate Playdate integration details such as SDK path, bundle layout, and build expectations

Suggested tools:
- `playdate_query_api`
  - Returns Playdate SDK API references and short explanations.
- `playdate_search_examples`
  - Returns Playdate examples and snippets for the requested API or workflow.
- `playdate_suggest_placement`
  - Explains where Playdate-specific code or data should live in the project.
- `playdate_validate_integration`
  - Checks Playdate-specific setup, packaging, and build assumptions.

Example behavior:
- Ask about `PlaydateAPI*` and get a concrete answer with the relevant subsystem and example usage.
- Ask how to package a change and get guidance for source, assets, `pdxinfo`, and simulator/device outputs.

## 4. Intended split

- Use Project Manager for writes and structure changes.
- Use Corgo MCP for engine/project knowledge and repository examples.
- Use Playdate MCP for SDK and platform knowledge.
- Keep diagnostics MCPs read-only so they can be safely used in Copilot Agent mode.
