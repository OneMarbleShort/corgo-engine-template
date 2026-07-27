import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  getGamesAndScenes,
  readPresets,
  validatePresetSceneConsistency,
} from "./lib.mjs";

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
    name: "corgo-diagnostics",
    version: "0.1.0",
  });

  server.registerTool(
    "corgo_list_games_and_scenes",
    {
      description: "Lists Corgo game folders with declared scenes and default start scene.",
      inputSchema: {
        workspacePath: z.string().optional(),
      },
    },
    async ({ workspacePath }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const gamesArray = await getGamesAndScenes(resolvedWorkspacePath);

      return textResult({
        workspacePath: resolvedWorkspacePath,
        gamesArray,
      });
    },
  );

  server.registerTool(
    "corgo_list_presets",
    {
      description: "Returns configure/build presets from corgogame/CMakePresets.json.",
      inputSchema: {
        workspacePath: z.string().optional(),
      },
    },
    async ({ workspacePath }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const { presetsPath, presetsObject } = await readPresets(resolvedWorkspacePath);

      return textResult({
        workspacePath: resolvedWorkspacePath,
        presetsPath,
        configurePresetsArray: presetsObject.configurePresets || [],
        buildPresetsArray: presetsObject.buildPresets || [],
      });
    },
  );

  server.registerTool(
    "corgo_validate_preset_scene_consistency",
    {
      description: "Validates that preset game/scene references match available game folders and scene declarations.",
      inputSchema: {
        workspacePath: z.string().optional(),
      },
    },
    async ({ workspacePath }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const validationObject = await validatePresetSceneConsistency(resolvedWorkspacePath);
      return textResult(validationObject);
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
} else {
  runServer().catch((error) => {
    process.stderr.write(`Server failed: ${String(error.message || error)}\n`);
    process.exitCode = 1;
  });
}
