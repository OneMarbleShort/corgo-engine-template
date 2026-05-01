//
//  game/scenes.h
//  Main include for game demo scenes.
//  Copyright (c) 2026 Carlos Camacho. All rights reserved.
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


// #define CE_ENGINE_SET_START_SCENE MyScene

// Sample Hello World Scene
CE_DECLARE_SCENE(HelloCorgo)

// Set this to the scene you want to load first
#define CE_ENGINE_SET_START_SCENE HelloCorgo

#endif // CORGO_GAME_SCENES_H
