//
//  game/systems.h
//  List of game ECS systems
//  Copyright (c) 2025 Carlos Camacho. All rights reserved.
//

#ifndef CORGO_GAME_SYSTEMS_H
#define CORGO_GAME_SYSTEMS_H

#include "ecs/core/system.h"

/**
 * How to define a system:
 * 
 * 1. Declare dependencies using a macro like this (Don't forget the backslash at the end):
 *      #define CE_MY_SYSTEM_NAME_DEPENDENCIES \
 *          REQUIRE_COMPONENT(CE_TEXT_LABEL_COMPONENT, textLabelComponent)\
 *          REQUIRE_RELATIONSHIP(CE_RELATIONSHIP_PARENT, parentEntity)
 * 
 * 2. Add the system to the system description macro below:
 *    
 *      #define CE_SYSTEM_DESC_GAME(CE_SYSTEM_DESC) \
 *          CE_SYSTEM_DESC(CE_MY_SYSTEM_NAME, <Run Order>, <Run Phase>, <Run Frequency>, CE_MY_SYSTEM_NAME_DEPENDENCIES)
 * 
 *    <Run Order>: Determines what entity order the system runs on. Options are:
 *       - CE_ECS_SYSTEM_RUN_ORDER_AUTO: System runs on automatic order that maximizes performance, use this unless you have special requirements.
 *       - CE_ECS_SYSTEM_RUN_ORDER_SCENETREE: System runs in scene tree order, from root to leaves, breadth-first. Use this for systems that depend on parent-child relationships.
 *       - CE_ECS_SYSTEM_RUN_ORDER_RENDER: System runs in render order (Z index), from back to front. Use this for systems that render to screen.
 *    
 *    <Run Phase>: Determines when the system runs relative to other systems. Systems of the same phase have no guaranteed order. In general
 *      use the default phase unless you have special requirements. Options are:
 *       - CE_ECS_SYSTEM_RUN_PHASE_EARLY: System runs first.
 *       - CE_ECS_SYSTEM_RUN_PHASE_DEFAULT: System runs after all early systems.
 *       - CE_ECS_SYSTEM_RUN_PHASE_LATE: System runs after all default systems.
 *    
 *    <Run Frequency>: Determines how often the system runs. Running more often can impact performance. Options are:
 *       - CE_ECS_SYSTEM_RUN_FREQUENCY_DISPLAY: System runs every display frame (for example: input).
 *       - CE_ECS_SYSTEM_RUN_FREQUENCY_HALF_DISPLAY: System runs every other frame (less critical gameplay tasks).
 *       - CE_ECS_SYSTEM_RUN_FREQUENCY_ONCE_PER_SECOND: System runs once per second. Run times may vary slightly to accommodate frame timing (time related tasks).
 *  
 *    Note: CE_ECS_SYSTEM_RUN_ORDER_RENDER ignores frequency, systems will always run once per frame. Use CE_ECS_SYSTEM_RUN_FREQUENCY_DISPLAY or the system won't run at all.
 *      <Run Phase> for Render systems only affects the order they run relative to other render systems.
 *      In general you want to use CE_ECS_SYSTEM_RUN_PHASE_DEFAULT, however CE_ECS_SYSTEM_RUN_PHASE_LATE can be used to render things on top of everything or 
 *      CE_ECS_SYSTEM_RUN_PHASE_EARLY can be used to render things behind everything (like tileset backgrounds).
 *      
 *    These systems should only be used for rendering-related tasks, avoid loading resources or heavy computations.
 * 
 * 3. Implement the system in a .c file using the CE_START_SYSTEM_IMPLEMENTATION and CE_END_SYSTEM_IMPLEMENTATION macros:
 * 
 *      CE_START_SYSTEM_IMPLEMENTATION(CE_MY_SYSTEM_NAME, CE_MY_SYSTEM_NAME_DEPENDENCIES)
 *      {
 *         // System logic here
 *      }
 *      CE_END_SYSTEM_IMPLEMENTATION
 */

#define CE_SYSTEM_DESC_GAME(CE_SYSTEM_DESC) \
/**
    CE_SYSTEM_DESC(CE_MY_SYSTEM_NAME, <Run Order>, <Run Phase>, <Run Frequency>, CE_MY_SYSTEM_NAME_DEPENDENCIES) \

**/

/**
 * How to define a global system:
 * Global systems are systems that tick independently of entities at most once per frame.
 * They have no dependencies on components or relationships and area always active.
 * 
 * 1. Add the global system to the global system description macro below, <Run Phase>, <Run Frequency> are the same as above.
 * 2. Implement the global system in a .c file using the CE_START_GLOBAL_SYSTEM_IMPLEMENTATION and CE_END_GLOBAL_SYSTEM_IMPLEMENTATION macros
 */

#define CE_GLOBAL_SYSTEM_DESC_GAME(CE_GLOBAL_SYSTEM_DESC) \
/**
    CE_GLOBAL_SYSTEM_DESC(CE_MY_GLOBAL_SYSTEM_NAME, <Run Phase>, <Run Frequency>) \

**/

#endif // CORGO_GAME_SYSTEMS_H
