# corgo-engine-template
A game template for building one (or more!) game with Corgo Engine. It is a good starting point and implements some good organization practices.

## License 
This template is licensed under The Unlicense, which means it is free to copy, modify, distribute, etc. without giving attribution. 
None of the files have Copyright headers, feel free to add your own.

This only applies to the source files in this repo. The Engine itself is BSD licensed which requires attribution. However this is only necessary if you are changing
the engine code. Your game remain yours.

Although not necessary, I will always appreciate a mention like "Made with Corgo Engine" somwehere in your game!

## Requirements

- [Playdate SDK](https://play.date/dev/)
-- set `PLAYDATE_SDK_PATH` environment variable to the install path
- [Visual Studio 2022 or 2026 (Version 17.9 or newer)](https://visualstudio.microsoft.com/) with C/C++ development tools. 
-- If using 2026: install VS2022 build tools (https://visualstudio.microsoft.com/vs/older-downloads/)
- [ARM GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) (arm-none-eabi-gcc 12.2) for device builds
- [CMake](https://cmake.org/) 3.14 or higher
- [VSCode](https://code.visualstudio.com/download) Recommended IDE. Install the following Plugins:
-- C/C++ support and DevTools: basic language support
-- CMake Tools: run builds and tests from the IDE
-- ELFInsights: debug the generated ELF images

## Setup

The recommendation is to download the files and add them to a fresh repository. Cloning or forking is not recommended because once you start building a game you won't be able to easily merge changes to the template.

1. Download a copy of the entire repo
2. Extract to a fresh folder and make a new git/perforce/etc repo
3. Install all required tools
4. When installing the ARM toolkit don't forget to add it to the PATH
5. Open the project in VSCode

### IDE Set Up
VSCode is the recommended IDE, although Visual Studio can be used I have not fully tested all the CMake preset functionality and some things may be a little wonky.
VSCode has a C/C++ debugger and can attach to the simulator, as well as run all tests, builds and launchers directly from within the IDE.

1. Install recommendede plugins
2. Open the top level folder as a project

If you have CmMake tools installed, it should pick up the Presets and show an icon on the left bar. If you cannot see it check .vscode/settings.json and update `cmake.sourceDirectory`.

### Device builds

In order to build for the PD device you need a new environment variable: `NMAKE_PATH` pointing to MSbuild nmake.exe
A script is provided: `scripts/set-up-eenv-vars.ps1` that will set the variable by using vswhere to find the correct path.

This only needs to be run once (or if the build tools change)

A VSCode task has been provided to run from the IDE:
1. Click on the Quick Access Bar
2. Type 'task' (without quotes) and a space
3. Select 'Set Up Env Variables'

## Projects, games and scenes
Corgo Engine can be built in different ways depending on your needs. This is less important if you are building a single game, but it helps builds multiple games or prototypes.

There are 3 ways of building games:
1. Multiple projects: A 'project' refers to a self contained game that has its own code and assets. Only the engine code is shared. This is recommended if you want to
have multiple games in the same repo but independent of each other. The template has a single project named 'corgogame'. Each project will generate its own .pdx file in a separate location and using its own pdxinfo.
2. Multiple games: A project can have multiple games inside, all of the games share the same assets but have independent C code. This includes separate components, systems and scenes. This is useful to build multiple prototypes or to have a central asset library. Every game in a project ships with ALL assets, so be careful when packaging your game. The template has 2 games: 'corgogame' and 'corgogame2'. Each game will generate its own .pdx file but will reuse the same pdxinfo file.
3. Multiple scenes: A game can have multiple scenes, technically these are not independent games, but a scene can be seen as an 'entry point' so you could potentially have separate prototypes implemented as separate scenes. All scenes in a game share all assets and code (components and systems). A single pdx is built per game and the starting scene will be the last one enabled when that pdx was built.

Projects are separate CMake targets so you need to point VSCode or the CLI to the correct CMakeLists.txt file in order to switch projects. Games and Scenes are controlled via CMake parameters and can be switched by using presets. More on this later.

## Building
Corgo Engine uses Cmake to configure and build. In particular it uses Presets to automate the steps and provide a quick way to build. The simplest way to build is:

1. Go to the CMake Tools panel
2. Under configure click the pencil and choose 'VS2022 Simulator (corgogame: HelloCorgo)'
3. Wait for the configure step to finish
4. In Build, choose 'Build VS2022 Simulator (corgogame: HelloCorgo)'
5. In the line under it, it should say 'ALL_BUILD', if not, select it from the list
6. Hover over the 'Build' header and click the icon that pops to the right of the word (looks like an arrow pointing down into a box)
7. Wait for the build to finish

CMake Tools and Cmake presets are complicated, you can read more here: https://github.com/microsoft/vscode-cmake-tools/blob/main/docs/cmake-presets.md
However, the process is very similar:

1. Choose a configure preset: device, simulator, game, or scene
2. Choose the build target
3. Build

Note on devide builds: If you get any errors related to Nmake don't forget to run the script and restart VScode. You only need to do it once.
Also, when switching from the device to the simulator or viceversa: the Build target changes name (the second line under the 'Build' header). The simulator uses 'ALL_BUILD' and the device uses 'all'. The previous value will remain and CMake will fail. Just choose the correct target. I am still trying to fix this.

## Running
The template includes a launch.js that simplifies launching and attaching from VSCode. The provided launch options allow running the last built PDX or building and running.

'Build and Run' is a bit brittle at the moment so you may want to build using CMake and just run with the 'Run Simulator' option, choose corgogame or corgogame2 depending on which one you built (probably corgogame).

## Start coding!

The template is yours to modify, open the files within src/corgoengine to start adding systems and components. The engine ships with several samples (find them in corgo-engine/src/samples) that can help you get started.
The following sections deal with customizing the template and adding multiple games.

## Renaming the game and deleting other games/projects/whatever

So you want to build a single game and the template has a lot of cruft, plus, while corgogame is an amazing name, it is not what you are building. Let's clean it up.

### Rename the project
As mentioned before /corgogame is the project, this can be renamed to anything you want:
- Rename the /corgogame directory: no spaces or special characters ('_' and '-' may be ok)
- .vscode/settings.json: update `cmake.sourceDirectory`
- .vscode/launch.json: update the launch arguments. For example: `"${workspaceFolder}/corgogame/corgogame.pdx"` becomes `"${workspaceFolder}/mynewproject/corgogame.pdx"`
- CMakeLists.txt: udpate the following line: `project(CorgoGame C ASM)`

We'll rename the second part of the path in the next step.

### Rename the game and delete the cruft
Within the 'corgogame' project there are 2 games: 'corgogame' and 'corgogame2'. Their purpose is to showcase how to have multiple games. Assuming that you don't want that, you can delete corgogame2:

1. Delete everything under /corgogame/corgogame2
2. Open CMakePresets.json and delete anything referencing corgogame2
3. Open .vscode/launch.json and delete anything referencing corgogame2
4. If you've built corgogame2 before: delete build.*.corgogame2, corgogame2.pdx and corgogame2_DEVICE.pdx

You can rename corgogame to your game's name, the only requirement is that it is a single word in all lowercase. Underscores (_) are probably ok, but dashes (-) may not work. I blame the OS.

1. Rename src/corgoengine to your game's name
2. Open CMakePresets and update any line that says `"CE_GAME_NAME": "corgogame"` to your new game
3. Open .vscode/launch.json and update any references to corgogame (i.e. `"${workspaceFolder}/mynewproject/myawesomegame.pdx"`)
4. Delete all build.*.corgogame folders, corgogame.pdx and corgogame_DEVICE.pdx
5. Select your new config preset in CMake Tools
6. wait for configure to finish and build

### Scene Management
The template ships with 3 scenes: corgogame:HelloCorgo, corgogame:HelloCorgoS2 and corgogame2:HelloCorgo. If you've followed the steps before then there are 2 left. Feel free to edit, delete or change any. Just remember to update scenes.h with the correct names.

The engine has a 'default scene' that is loaded when the game launches. There are 2 ways of controlling it:
- Edit the scenes.h file and change `CE_ENGINE_SET_START_SCENE`
- Make a CMake preset that overrides the default scene

The recommendation is to use `CE_ENGINE_SET_START_SCENE` for the scene that will be shipped in the final version of your game, and use CMake presets to make development presets that let you load other scenes for testing or debugging. CMakePresets.json has examples of how to override the scene.

Please note that the CMake Preset overrides `CE_ENGINE_SET_START_SCENE` and it won't revert until you rebuild the default preset (without the override). The PDX file itself is built with the hardcoded starting scene.

And a final note: scenes are designed to load/unload dynamically. For the final version of your game you should have a 'Main Menu' scene that handles that, CMake overrides are for development only.

## Adding projects and games
Adding a new project or game within a projects is done by copying files and adding CMake presets, in general:

1. Copy an existing project or game (/projectX or /projectX/gameY)
2. Update CMakePresets.json and .vscode/launch.json
3. Configure and build using CMake Tools

## Documentation
Sorry, documentation is WIP. The closest I have are the samples in corgo-engine/src/samples. Unfortunately they cannot be built from this template (or not easily). So you have to clone the engine repo and follow the build instructions there. The process is very similar but the CMake Presets are different.

## Help, my game crashes on the device
Debugging on the PD is hard, especially because there is no interactive debugger and there's no log. However, Corgo Engine ships with a small tool to try to help you debug.

1. After the crash, restart your PD and connect it to the PC
2. Using the simulator, mount the disk
3. In the root, find and copy a file called crashlog.txt
4. Delete the file in the PD: crashes are appended at the end so it can be confusing if there are multiple
5. Unmount your PD
6. Open your favorite CLI and navigate to /corgo-engine
7. Run `python crashcorg.py path/to/crashlog.txt -e path/to/build.pd/mygame.elf
8. Try to understand the output...

Crashcorg.py is a tool that examines the crash and tries to decode where in your code the crash happened as well as the error bits. Hopefully its enough to understand what happened.

## Common problems (and solutions):
- Configure for device fails because it can't find NMake: run the `Set Up Env Vars` task in VsCode.
- Configure for device fails because it can't find the arm compiler: Add the ARM build tools to your path.
- Configure fails because its missing the Playdate SDK: Add the SDK path to the `PLAYDATE_SDK_PATH` env variable
- I did that and still fails: restart VSCode
- Still fails or some other weird error: delete the build.* directory or directories and try again
- Getting a build error related to _Generic and cc.h: You need Visual Studio 17.9 or newer. This is fairly recent, it was released in Nov 2025.
- MSBuild missing, NMake missing, etc: If using VS2026 ensure you have installed the VS2022 build tools. Unfortunately the SDK does not work with the 2026 toolchain yet.
- Build and Launch does not work: still working on this, build using CMake Tools and use 'Run without building'.
- Launch doesn't work, can't find PDX, etc: check your launch.json has the right paths and the PDX exists. Ensure you have built the right preset.
- Configure says there is no 'all' or 'ALL_BUILD' target: when switching between device and simulator the build target is not updated. Unfortunately gcc and msbuild use different names so you have to manually select the right one after switching

Anything else: please open an issue in https://github.com/OneMarbleShort/corgo-engine