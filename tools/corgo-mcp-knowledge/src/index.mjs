import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  getGamesAndScenes,
  readPresets,
  validatePresetSceneConsistency,
} from "../../corgo-mcp-diagnostics/src/lib.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const defaultWorkspacePath = path.resolve(__dirname, "..", "..", "..");

function resolveWorkspacePath(workspacePath) {
  if (!workspacePath || !workspacePath.trim()) {
    return defaultWorkspacePath;
  }

  if (path.isAbsolute(workspacePath)) {
    return path.normalize(workspacePath);
  }

  return path.resolve(process.cwd(), workspacePath);
}

function textResult(payloadObject) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payloadObject, null, 2),
      },
    ],
  };
}

function splitQueryIntoTerms(queryText) {
  return queryText
    .toLowerCase()
    .split(/[^a-z0-9_]+/)
    .map((term) => term.trim())
    .filter((term) => term.length > 2);
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readTextFile(filePath) {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return null;
  }
}

async function collectTextFiles(rootPath, relativePathsArray) {
  const filePathsArray = [];

  for (const relativePath of relativePathsArray) {
    const absolutePath = path.join(rootPath, relativePath);
    try {
      const statsObject = await fs.stat(absolutePath);
      if (statsObject.isFile()) {
        filePathsArray.push(absolutePath);
      }
      else if (statsObject.isDirectory()) {
        const entriesArray = await fs.readdir(absolutePath, { withFileTypes: true });
        for (const entryItem of entriesArray) {
          if (entryItem.isFile()) {
            filePathsArray.push(path.join(absolutePath, entryItem.name));
          }
        }
      }
    } catch {
      // Ignore missing paths.
    }
  }

  return filePathsArray;
}

async function searchFileSnippets(rootPath, relativePathsArray, queryText, maxResultsCount = 8) {
  const termsArray = splitQueryIntoTerms(queryText);
  const filePathsArray = await collectTextFiles(rootPath, relativePathsArray);
  const matchesArray = [];

  for (const filePath of filePathsArray) {
    const textValue = await readTextFile(filePath);
    if (textValue === null) {
      continue;
    }

    const linesArray = textValue.split(/\r?\n/);
    for (let lineIndex = 0; lineIndex < linesArray.length; lineIndex += 1) {
      const lineText = linesArray[lineIndex];
      const lineLower = lineText.toLowerCase();
      const hitCount = termsArray.filter((term) => lineLower.includes(term)).length;
      if (hitCount === 0) {
        continue;
      }

      matchesArray.push({
        filePath: path.relative(rootPath, filePath),
        lineNumber: lineIndex + 1,
        hitCount,
        text: lineText.trim(),
      });
    }
  }

  matchesArray.sort((leftValue, rightValue) => {
    if (rightValue.hitCount !== leftValue.hitCount) {
      return rightValue.hitCount - leftValue.hitCount;
    }
    if (leftValue.filePath !== rightValue.filePath) {
      return leftValue.filePath.localeCompare(rightValue.filePath);
    }
    return leftValue.lineNumber - rightValue.lineNumber;
  });

  return matchesArray.slice(0, maxResultsCount);
}

function suggestPlacement(queryText) {
  const lowerText = queryText.toLowerCase();

  if (lowerText.includes("scene") || lowerText.includes("start scene") || lowerText.includes("scenes.h")) {
    return {
      recommendedPath: "corgogame/src/<game>/scenes.h",
      reason: "Scene declarations and the default start scene are controlled per game in scenes.h.",
    };
  }

  if (lowerText.includes("component") || lowerText.includes("system") || lowerText.includes("engine") || lowerText.includes("backend")) {
    return {
      recommendedPath: "corgo-engine/src/engine/",
      reason: "Engine behavior, components, systems, and backends belong under the engine source tree.",
    };
  }

  if (lowerText.includes("sample") || lowerText.includes("demo")) {
    return {
      recommendedPath: "corgo-engine/src/samples/",
      reason: "Samples and reference code live in the engine samples area.",
    };
  }

  if (lowerText.includes("pdxinfo") || lowerText.includes("bundle") || lowerText.includes("package")) {
    return {
      recommendedPath: "corgogame/Source/pdxinfo",
      reason: "The per-game pdxinfo file and bundle metadata live under the Source folder.",
    };
  }

  if (lowerText.includes("rename") || lowerText.includes("clone") || lowerText.includes("delete") || lowerText.includes("project")) {
    return {
      recommendedPath: "tools/project-manager/",
      reason: "Project structure edits are handled by the Project Manager tool, not by MCP reads.",
    };
  }

  if (lowerText.includes("build") || lowerText.includes("preset") || lowerText.includes("launch")) {
    return {
      recommendedPath: "corgogame/CMakePresets.json and .vscode/launch.json",
      reason: "Build and launch behavior is controlled by presets and VS Code launch configuration.",
    };
  }

  return {
    recommendedPath: "corgogame/src/<game>/ or corgo-engine/src/engine/",
    reason: "If the request is game-specific, put it in the game folder; if it is reusable engine behavior, put it in the engine tree.",
  };
}

async function runSelfCheck() {
  const workspacePath = resolveWorkspacePath(process.argv[3]);
  const gamesArray = await getGamesAndScenes(workspacePath);
  const validationObject = await validatePresetSceneConsistency(workspacePath);

  const outputObject = {
    workspacePath,
    gamesFound: gamesArray.map((item) => item.gameName),
    issuesCount: validationObject.issuesArray.length,
    firstIssues: validationObject.issuesArray.slice(0, 5),
  };

  process.stdout.write(`${JSON.stringify(outputObject, null, 2)}\n`);
}

async function runServer() {
  const server = new McpServer({
    name: "corgo-knowledge",
    version: "0.1.0",
  });

  const knowledgeRootsArray = [
    "README.md",
    "tools/mcp-server-plan.md",
    "corgo-engine/.github/copilot-instructions.md",
    "corgo-engine/README.md",
    "corgo-engine/src",
    "corgogame/CMakeLists.txt",
    "corgogame/CMakePresets.json",
    "corgogame/src",
    "tools/project-manager",
  ];

  server.registerTool(
    "corgo_query_api",
    {
      description: "Explains Corgo engine APIs, repo conventions, games, and build structure.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
      },
    },
    async ({ workspacePath, query }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();
      const searchMatchesArray = await searchFileSnippets(resolvedWorkspacePath, knowledgeRootsArray, queryText, 10);

      const projectFactsObject = {
        games: (await getGamesAndScenes(resolvedWorkspacePath)).map((gameItem) => ({
          gameName: gameItem.gameName,
          defaultStartScene: gameItem.defaultStartScene,
          declaredScenesArray: gameItem.declaredScenesArray,
        })),
        presets: null,
      };

      try {
        const { presetsObject } = await readPresets(resolvedWorkspacePath);
        projectFactsObject.presets = {
          configurePresetsCount: (presetsObject.configurePresets || []).length,
          buildPresetsCount: (presetsObject.buildPresets || []).length,
        };
      } catch {
        projectFactsObject.presets = { configurePresetsCount: 0, buildPresetsCount: 0 };
      }

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        projectFacts: projectFactsObject,
        matchesArray: searchMatchesArray,
      });
    },
  );

  server.registerTool(
    "corgo_search_examples",
    {
      description: "Finds repository examples and snippets that match a Corgo-engine question.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
        maxResults: z.number().int().positive().optional(),
      },
    },
    async ({ workspacePath, query, maxResults }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();
      const matchesArray = await searchFileSnippets(
        resolvedWorkspacePath,
        knowledgeRootsArray,
        queryText,
        maxResults || 8,
      );

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        matchesArray,
      });
    },
  );

  server.registerTool(
    "corgo_suggest_placement",
    {
      description: "Suggests the most likely location for a new Corgo-engine change.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
      },
    },
    async ({ workspacePath, query }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();
      const placementObject = suggestPlacement(queryText);

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        placement: placementObject,
      });
    },
  );

  server.registerTool(
    "corgo_validate_change",
    {
      description: "Checks whether a proposed Corgo-engine edit fits the current project layout.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
        targetPath: z.string().optional(),
      },
    },
    async ({ workspacePath, query, targetPath }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();
      const placementObject = suggestPlacement(queryText);
      const issuesArray = [];

      if (targetPath) {
        const normalizedTargetPath = path.normalize(targetPath).replace(/\\/g, "/").toLowerCase();
        const normalizedRecommendedPath = placementObject.recommendedPath.toLowerCase();
        if (!normalizedTargetPath.includes(normalizedRecommendedPath.split("/")[0])) {
          issuesArray.push({
            severity: "warning",
            code: "TARGET_PATH_DOES_NOT_MATCH_SUGGESTION",
            message: `The requested target '${targetPath}' does not look like the suggested location '${placementObject.recommendedPath}'.`,
          });
        }
      }

      if (queryText.toLowerCase().includes("scene") || queryText.toLowerCase().includes("preset")) {
        try {
          const validationObject = await validatePresetSceneConsistency(resolvedWorkspacePath);
          if (validationObject.issuesArray.length > 0) {
            issuesArray.push(...validationObject.issuesArray.slice(0, 3));
          }
        } catch (error) {
          issuesArray.push({
            severity: "warning",
            code: "VALIDATION_FAILED",
            message: String(error.message || error),
          });
        }
      }

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        targetPath: targetPath || null,
        placement: placementObject,
        issuesArray,
      });
    },
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

if (process.argv[2] === "--self-check") {
  runSelfCheck().catch((error) => {
    process.stderr.write(`Self-check failed: ${String(error.message || error)}\n`);
    process.exitCode = 1;
  });
}
else {
  runServer().catch((error) => {
    process.stderr.write(`Server failed: ${String(error.message || error)}\n`);
    process.exitCode = 1;
  });
}