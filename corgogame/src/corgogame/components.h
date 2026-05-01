//
//  game/components.h
//  List of game ECS components
//

#ifndef CORGO_GAME_COMPONENTS_H
#define CORGO_GAME_COMPONENTS_H

#include "ecs/core/component.h"

/**
 * How to define a component:
 * 
 * 1. Define the component data struct, this can be any C struct. 
 *    The CE_* naming convention is not required, but some sort of prefix is recommended to avoid name clashes.
 *    
 *      typedef struct CE_MyComponent {
 *            // Component data here
 *      } CE_MyComponent;
 * 
 *  2. Add the component to the component description macro below:
 *  
 *    #define CE_COMPONENT_DESC_GAME(CE_COMPONENT_DESC) \
 *       CE_COMPONENT_DESC(CE_MY_COMPONENT, <UUID>, CE_MyComponent, <Initial Capacity>)
 * 
 *  UUID starts at 100 to avoid conflicts with core and engine components.
 *  See docs for details on UUID and Initial Capacity.
 * 
 *  3. Implement the component initialization and cleanup functions in a .c file:
 *  
 *      CE_DEFINE_COMPONENT_INIT(CE_MY_COMPONENT)
 *      {
 *          // Initialization logic here
 *          return CE_OK;
 *      }
 * 
 *      CE_DEFINE_COMPONENT_CLEANUP(CE_MY_COMPONENT)
 *      {
 *          // Cleanup logic here
 *          return CE_OK;
 *      }
 * 
 * 
 *  Tips:
 *  - Don't forget the backslash at the end of the line when adding new components.
 */

#define CE_COMPONENT_DESC_GAME(CE_COMPONENT_DESC) \
/**
    CE_COMPONENT_DESC(CE_MY_COMPONENT, <UUID>, CE_MyComponent, <Initial Capacity>) \

**/

/**
 * Global components are similar to regular components but are not attached to entities.
 * They are unique instances that exist globally within the ECS context.
 * They cannot be created or destroyed at runtime.
 * 
 * To define a global component:
 * 
 * 1. Define the global component macro: CE_GLOBAL_COMPONENT_DESC_GAME, similar to regular components.
 *    Only name and struct type are needed, no UUID or capacity.
 * 
 * 2. Implement the global component initialization and cleanup functions in a .c file using the macros:
 *    CE_DEFINE_GLOBAL_COMPONENT_INIT(CE_MY_COMPONENT) and CE_DEFINE_GLOBAL_COMPONENT_CLEANUP(CE_MY_COMPONENT).
 */

#define CE_GLOBAL_COMPONENT_DESC_GAME(CE_GLOBAL_COMPONENT_DESC) \
/**
    CE_GLOBAL_COMPONENT_DESC(CE_MY_COMPONENT, CE_MyGlobalComponent) \

**/

#endif // CORGO_GAME_COMPONENTS_H