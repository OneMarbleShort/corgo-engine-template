import fs from "node:fs/promises";
import path from "node:path";

function stripComments(rawText) {
  return rawText
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|\s)\/\/.*$/gm, "$1");
}

export function parseScenesHeader(rawText) {
  const cleanedText = stripComments(rawText);
  const sceneNamesArray = [];
  const sceneRegex = /CE_DECLARE_SCENE\(([^)]+)\)/g;

  let regexMatch = sceneRegex.exec(cleanedText);
  while (regexMatch) {
    sceneNamesArray.push(regexMatch[1].trim());
    regexMatch = sceneRegex.exec(cleanedText);
  }

  const startSceneMatch = cleanedText.match(/#define\s+CE_ENGINE_SET_START_SCENE\s+([A-Za-z0-9_]+)/);

  return {
    declaredScenesArray: sceneNamesArray,
    defaultStartScene: startSceneMatch ? startSceneMatch[1] : null,
  };
}

export async function getGamesAndScenes(workspacePath) {
  const gamesRootPath = path.join(workspacePath, "corgogame", "src");
  const entriesArray = await fs.readdir(gamesRootPath, { withFileTypes: true });
  const gamesArray = [];

  for (const entryItem of entriesArray) {
    if (!entryItem.isDirectory()) {
      continue;
    }

    const gameName = entryItem.name;
    const scenesHeaderPath = path.join(gamesRootPath, gameName, "scenes.h");

    try {
      const headerText = await fs.readFile(scenesHeaderPath, "utf8");
      const parsedData = parseScenesHeader(headerText);
      gamesArray.push({
        gameName,
        scenesHeaderPath,
        declaredScenesArray: parsedData.declaredScenesArray,
        defaultStartScene: parsedData.defaultStartScene,
      });
    } catch {
      // Ignore directories that are not game folders.
    }
  }

  gamesArray.sort((leftValue, rightValue) => leftValue.gameName.localeCompare(rightValue.gameName));
  return gamesArray;
}

function mergeCacheVariables(baseObject, patchObject) {
  return {
    ...(baseObject || {}),
    ...(patchObject || {}),
  };
}

function toArray(value) {
  if (value === undefined || value === null) {
    return [];
  }

  if (Array.isArray(value)) {
    return value;
  }

  return [value];
}

export function resolveConfigurePreset(configurePresetsArray, presetName) {
  const byNameMap = new Map(configurePresetsArray.map((presetObject) => [presetObject.name, presetObject]));
  const seenNamesSet = new Set();

  function resolveOne(name) {
    if (seenNamesSet.has(name)) {
      throw new Error(`Cycle detected in configure preset inheritance at '${name}'`);
    }

    const presetObject = byNameMap.get(name);
    if (!presetObject) {
      throw new Error(`Missing configure preset '${name}'`);
    }

    seenNamesSet.add(name);

    let mergedCacheVariables = {};
    const inheritedNamesArray = toArray(presetObject.inherits);
    for (const parentName of inheritedNamesArray) {
      const parentResolved = resolveOne(parentName);
      mergedCacheVariables = mergeCacheVariables(mergedCacheVariables, parentResolved.cacheVariables);
    }

    mergedCacheVariables = mergeCacheVariables(mergedCacheVariables, presetObject.cacheVariables);

    seenNamesSet.delete(name);

    return {
      name: presetObject.name,
      cacheVariables: mergedCacheVariables,
      binaryDir: presetObject.binaryDir || null,
      hidden: Boolean(presetObject.hidden),
      displayName: presetObject.displayName || null,
    };
  }

  return resolveOne(presetName);
}

export async function readPresets(workspacePath) {
  const presetsPath = path.join(workspacePath, "corgogame", "CMakePresets.json");
  const presetsText = await fs.readFile(presetsPath, "utf8");
  const presetsObject = JSON.parse(presetsText);
  return {
    presetsPath,
    presetsObject,
  };
}

export async function validatePresetSceneConsistency(workspacePath) {
  const gamesArray = await getGamesAndScenes(workspacePath);
  const gameByNameMap = new Map(gamesArray.map((gameItem) => [gameItem.gameName, gameItem]));

  const { presetsPath, presetsObject } = await readPresets(workspacePath);
  const configurePresetsArray = presetsObject.configurePresets || [];
  const buildPresetsArray = presetsObject.buildPresets || [];

  const issuesArray = [];
  const resolvedArray = [];

  for (const presetObject of configurePresetsArray) {
    let resolvedObject;
    try {
      resolvedObject = resolveConfigurePreset(configurePresetsArray, presetObject.name);
    } catch (error) {
      issuesArray.push({
        severity: "error",
        code: "CONFIGURE_PRESET_RESOLUTION_FAILED",
        presetName: presetObject.name,
        message: String(error.message || error),
      });
      continue;
    }

    const gameNameValue = resolvedObject.cacheVariables.CE_GAME_NAME;
    const startSceneValue = resolvedObject.cacheVariables.CE_ENGINE_START_SCENE;

    resolvedArray.push({
      presetName: presetObject.name,
      gameName: gameNameValue || null,
      startScene: startSceneValue || null,
      binaryDir: resolvedObject.binaryDir,
    });

    if (gameNameValue) {
      const gameObject = gameByNameMap.get(gameNameValue);
      if (!gameObject) {
        issuesArray.push({
          severity: "error",
          code: "MISSING_GAME_DIRECTORY",
          presetName: presetObject.name,
          message: `Preset references game '${gameNameValue}', but no matching folder exists under corgogame/src`,
        });
        continue;
      }

      if (startSceneValue && !gameObject.declaredScenesArray.includes(startSceneValue)) {
        issuesArray.push({
          severity: "error",
          code: "MISSING_SCENE_DECLARATION",
          presetName: presetObject.name,
          message: `Preset start scene '${startSceneValue}' is not declared in ${path.relative(workspacePath, gameObject.scenesHeaderPath)}`,
        });
      }
    }
  }

  const configurePresetNamesSet = new Set(configurePresetsArray.map((item) => item.name));
  for (const buildPresetObject of buildPresetsArray) {
    if (!configurePresetNamesSet.has(buildPresetObject.configurePreset)) {
      issuesArray.push({
        severity: "error",
        code: "BUILD_PRESET_MISSING_CONFIGURE",
        presetName: buildPresetObject.name,
        message: `Build preset references missing configure preset '${buildPresetObject.configurePreset}'`,
      });
    }
  }

  return {
    workspacePath,
    presetsPath,
    gamesCount: gamesArray.length,
    configurePresetsCount: configurePresetsArray.length,
    buildPresetsCount: buildPresetsArray.length,
    resolvedPresetsArray: resolvedArray,
    issuesArray,
  };
}
