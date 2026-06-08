//
//  game/scenes.h
//  Main include for game demo scenes.
//

#ifndef CORGO_GAME_SCENES_H
#define CORGO_GAME_SCENES_H

#include "engine/core/scene.h"

/***
 * Declare scenes here using the CE_DECLARE_SCENE macro, which takes the scene name as a parameter and generates the necessary function declarations for that scene.
 * For example:
 * CE_DECLARE_SCENE(MyScene)
 * 
 * Then add a .c file and implement the scenes logic. See samples/scenes/ for examples of how to implement scenes. 
 */


// #define CE_ENGINE_SET_START_SCENE HelloCorgoS2

// Sample Hello World Scene
CE_DECLARE_SCENE(HelloCorgo)
CE_DECLARE_SCENE(HelloCorgoS2)

// Set this to the scene you want to load first, using a ifndef to allow overriding via CMake
#ifndef CE_ENGINE_SET_START_SCENE
#define CE_ENGINE_SET_START_SCENE HelloCorgoS2
#endif 

#endif // CORGO_GAME_SCENES_H
