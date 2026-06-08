# Purpose
This tool is to allow quick modification to a corgo-engine project without having to manually muck through files.

# Features
- Rename Project - Example this project is called corgo-engine-template, a user should be able to rename it and all files that reference that name to something else.
- Should be able to clone a project into another folder as a new project (with a different name)
- Should be able to add a new game (using another as a template)
- Should be able to clone a game
- Should be able to rename a game
- Should be able to delete a game and all of its scenes
- Should be able to add new scenes to the current game
- Should be able to clone a scene in the current game
- Should be able to rename scenes in a current game
- Should be able to delete scenes in a current game
- Adding a new scene or new
- User should be able to switch between games in the project via this tool
- Underlying build files and configurations should adjust when changed in the tool

# Information
The repo itself is the high level corgo-engine project
Within a corgo-engine project you can have multiple games
Each of those games can have multiple scenes
Each game is in its own folder, and they follow the structure of corgogame (which is the default template game)
Workspace/corgogame/src/ is where all of the current games are located
Workspace/corgogame/Source/ is where the one and only pdxinfo file is.
Check out the main README.md file for more information on the engine

