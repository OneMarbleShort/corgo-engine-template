# Purpose
This file is used to provide a list of guidelines that should be followed for all tools created in this projet

# Requirements
- All GUI tools need to be able to become an executable that someone can just run without having all the dependencies
- Code should be as compact as possible
- The UI should take up the least amount of screen space as possible
- UI should be written in python, and use Kivy framework
- UI should have high contrast and easy to read
- a build script should be provided that packages the tool into an exe
- the tool should auto install dependencies that aren't installed
- each tool should have it's own folder under tools
- each tool should build it's exe into tools/bin
- For PyInstaller builds that requirement means the final `.exe` itself must be emitted directly into `tools/bin`; avoid `COLLECT`/one-folder layouts that create `tools/bin/<tool-name>/...` unless the script moves and validates the final executable path explicitly.
- when it makes sense store out configurable values into a tool specific json file.
- For Python GUI tools, build scripts should select a supported interpreter version explicitly (for this repo: Python 3.11/3.12/3.13 for Kivy) instead of relying on whatever `python` resolves to.
- Build scripts should fail on non-zero external command exit codes (pip/pyinstaller/etc), not just on PowerShell runtime errors.
- Keep a maintained `.spec` file checked into the tool folder and build from it, instead of regenerating the spec every run.
- Always build and test your code changes

# Standards
- Each feature should have a unit test to validate behavior
- Function names CamelCaseAlways
- In places where you can force a data type do so
- Provide Validation and Error catching with user friendly messages. Should include a potential "how to fix"
- local variables should be start with an underscore and be camel cased
- function parameters should start with a lower case letter but be camel cased
- Avoid variables stored at the global level
- Prefer structs to maintain blocks of related data, reduce the number of arguments for functions
- If you can write a function with a bail out first, or with nested ifs with the same functionality, prefer the bail out first version
- No variables should never be single letters. They should always be named related to the thing they are. In cases where the units or container type are hard to guess add that at the end of the variable name. examples: SomeTimeInSeconds, ContactsArray, ContactsMap
- EXE packaging should include a smoke run validation step after build (start the exe and verify process starts) before marking complete.
