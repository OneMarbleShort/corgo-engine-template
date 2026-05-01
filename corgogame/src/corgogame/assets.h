//
//  game/assets.h
//  Custom asset loaders for the game.
//  Copyright (c) 2025 Carlos Camacho. All rights reserved.
//

#ifndef CORGO_GAME_ASSETS_H
#define CORGO_GAME_ASSETS_H

/**
 * This file is used to define custom asset types and their loaders for the game.
 * An Asset is a resource that can be loaded and represented by a pointer type.
 * Using this will let the engine manage asset caching and unloading automatically.
 * 
 * To define an asset:
 * 
 * 1. Add an entry in the CE_ASSET_TYPES_GAME macro below, following the naming convention CE_ASSET_TYPE_<MY_NAME>.
 *    The generated enum is not stable across builds, so do not serialize these values directly.
 *    This is the Asset Type.
 * 
 * 2. Define an asset loader for the asset type using the CE_ASSET_LOADERS_GAME macro below.
 *    Each asset loader requires:
 *    - Asset type (must match one of the types defined above)
 *    - Type returned by the loader, do not add the * here, just the base type.
 *    - Load parameters struct type, or CE_Asset_LoadParams_None if no parameters are needed.
 *      This is a struct that will be passed to the loader function to customize loading.
 * 
 * 3. Implement the asset loader functions in a .c file.
 *    You can define different loaders per platform if needed, but only one loader should be defined at a time or the build will fail.
 *    See engine/assets.h for how to handle different platforms.
 *    Use the macros CE_DEFINE_ASSET_LOADER_LOAD and CE_DEFINE_ASSET_LOADER_FREE to implement the load and free functions for your asset type.
 *    Alternatively use the CE_GENERATE_ASSET_LOADER_STUB macro to generate stub implementations that do nothing (for development purposes, they are intended to error out). 
 *   
 * Assets loaded via Asset loaders are always loaded (unless the underlying platform supports caching internally).
 * Corgo Engine provides a basic asset cache via the asset cache global component, so its recommended to use that instead.
 */


// Custom asset types go here.
// Don't forget the trailing slash.
#define CE_ASSET_TYPES_GAME(CE_ASSET_TYPE) \
/**
    CE_ASSET_TYPE(CE_ASSET_TYPE_<my name>) \

**/

// Asset loaders for custom assets, one per type.
// Don't forget the trailing slash.
#define CE_ASSET_LOADERS_GAME(CE_ASSET_LOADER) \
/**
    CE_ASSET_LOADER(<asset type>, <pointer type>, <load parameters>) \

**/

#endif // CORGO_GAME_ASSETS_H