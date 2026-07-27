import test from "node:test";
import assert from "node:assert/strict";
import {
  parseScenesHeader,
  resolveConfigurePreset,
} from "../src/lib.mjs";

test("parseScenesHeader extracts scenes and start scene", () => {
  const inputText = `
    // CE_DECLARE_SCENE(CommentedOut)
    CE_DECLARE_SCENE(HelloCorgo)
    CE_DECLARE_SCENE(HelloCorgoS2)
    #ifndef CE_ENGINE_SET_START_SCENE
    #define CE_ENGINE_SET_START_SCENE HelloCorgo
    #endif
  `;

  const parsedObject = parseScenesHeader(inputText);
  assert.deepEqual(parsedObject.declaredScenesArray, ["HelloCorgo", "HelloCorgoS2"]);
  assert.equal(parsedObject.defaultStartScene, "HelloCorgo");
});

test("resolveConfigurePreset merges inherited cacheVariables", () => {
  const presetsArray = [
    {
      name: "base",
      cacheVariables: {
        CE_GAME_NAME: "corgogame",
      },
    },
    {
      name: "scene",
      inherits: "base",
      cacheVariables: {
        CE_ENGINE_START_SCENE: "HelloCorgo",
      },
    },
  ];

  const resolvedObject = resolveConfigurePreset(presetsArray, "scene");
  assert.equal(resolvedObject.cacheVariables.CE_GAME_NAME, "corgogame");
  assert.equal(resolvedObject.cacheVariables.CE_ENGINE_START_SCENE, "HelloCorgo");
});
