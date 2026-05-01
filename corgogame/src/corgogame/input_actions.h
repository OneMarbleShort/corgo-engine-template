//
//  game/input_actions.h
//  Main include for game input actions.
//  Copyright (c) 2026 Carlos Camacho. All rights reserved.
//

#ifndef CORGO_GAME_INPUT_ACTIONS_H
#define CORGO_GAME_INPUT_ACTIONS_H

/**
 * Input actions go here. 
 * An input actions maps to a bit in the m_actionStates field of the CE_InputComponent.
 * They are defined in an enum that is built using the macros in this header.
 * 
 * To add a new input action:
 * 
 * 1. Add a new entry to the CE_INPUT_ACTIONS_GAME(CE_IA_DESC) macro list in this header, with a unique name:
 *      CE_IA_DESC(MY_ACTION)\
 * 2. Don't forget the trailing backslash on all but the last entry in the list.
 * 4. Rebuild.
 * 
 * Input action ids are not stable across builds.
 */

#define CE_INPUT_ACTIONS_GAME(CE_IA_DESC) \

/**
 * Action maps go here, using the CE_DECLARE_ACTION_MAP_FUNCTION macro, which generates the necessary function declarations for that input map.
 * For example:
 * CE_DECLARE_ACTION_MAP_FUNCTION(MyInputMap)
 * 
 * See samples/input/sample.c for examples of how to implement input maps.
 */

#endif // CORGO_GAME_INPUT_ACTIONS_H
