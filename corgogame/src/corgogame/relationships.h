//
//  game/relationships.h
//  List of game ECS relationships
//  Copyright (c) 2025 Carlos Camacho. All rights reserved.
//

#ifndef CORGO_GAME_RELATIONSHIPS_H
#define CORGO_GAME_RELATIONSHIPS_H

/** 
 * How to define a relationship:
 * 
 * 1. Add the relationship to the relationship description macro below:
 * 
 *   #define CE_RELATIONSHIP_DESC_GAME(CE_RELATIONSHIP_DESC) \
 *    CE_RELATIONSHIP_DESC(CE_RELATIONSHIP_NAME)
 * 
 * 2. Use the relationship in your game systems or components as needed.
 *   See docs for details on defining and using relationships.
 * 
 *  Tips:
 *  - Don't forget the backslash at the end of the line when adding new relationships.
 *  - Add relationships in pairs with their reciprocal (e.g., parent-child). 
 */

#define CE_RELATIONSHIP_DESC_GAME(CE_RELATIONSHIP_DESC) \
/**
    CE_RELATIONSHIP_DESC(CE_RELATIONSHIP_NAME) \

**/


#endif // CORGO_GAME_RELATIONSHIPS_H