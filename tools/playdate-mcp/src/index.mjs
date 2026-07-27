import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

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

async function readTextFile(filePath) {
  try {
    return await fs.readFile(filePath, "utf8");
  } catch {
    return null;
  }
}

async function findFilesRecursive(rootPath, predicate) {
  const matchesArray = [];

  async function walk(currentPath) {
    let entriesArray;
    try {
      entriesArray = await fs.readdir(currentPath, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entryItem of entriesArray) {
      const entryPath = path.join(currentPath, entryItem.name);
      if (entryItem.isDirectory()) {
        await walk(entryPath);
      }
      else if (predicate(entryPath)) {
        matchesArray.push(entryPath);
      }
    }
  }

  await walk(rootPath);
  return matchesArray;
}

async function collectSearchLines(rootPath, relativePathsArray, queryText, maxResultsCount = 10) {
  const termsArray = splitQueryIntoTerms(queryText);
  const matchesArray = [];

  for (const relativePath of relativePathsArray) {
    const absolutePath = path.join(rootPath, relativePath);
    let textValue;
    try {
      textValue = await fs.readFile(absolutePath, "utf8");
    } catch {
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
        filePath: relativePath,
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

  if (lowerText.includes("pdxinfo") || lowerText.includes("bundle") || lowerText.includes("package")) {
    return {
      recommendedPath: "corgogame/Source/pdxinfo",
      reason: "The Playdate bundle metadata lives in the per-game Source folder.",
    };
  }

  if (lowerText.includes("graphics") || lowerText.includes("sprite") || lowerText.includes("button") || lowerText.includes("crank") || lowerText.includes("system")) {
    return {
      recommendedPath: "corgo-engine/src/engine/backends/playdate.c",
      reason: "Playdate-only platform glue should stay in the backend and platform source files.",
    };
  }

  if (lowerText.includes("scene") || lowerText.includes("game") || lowerText.includes("example")) {
    return {
      recommendedPath: "corgogame/src/<game>/",
      reason: "Game code that uses the Playdate SDK should usually live in the game source tree.",
    };
  }

  return {
    recommendedPath: "corgo-engine/src/engine/backends/playdate.c or corgogame/src/<game>/",
    reason: "Platform integration code belongs in the backend; game behavior belongs in the game folder.",
  };
}

function resolveSdkPath(sdkPath) {
  const candidatePath = sdkPath || process.env.PLAYDATE_SDK_PATH || "";
  if (!candidatePath.trim()) {
    return null;
  }

  return path.isAbsolute(candidatePath)
    ? path.normalize(candidatePath)
    : path.resolve(process.cwd(), candidatePath);
}

async function collectPlaydateHeaderPaths(sdkRootPath) {
  const cApiRootPath = path.join(sdkRootPath, "C_API");
  const headerPathsArray = [];

  try {
    const entriesArray = await findFilesRecursive(cApiRootPath, (filePath) => filePath.endsWith(".h"));
    for (const filePath of entriesArray) {
      const fileName = path.basename(filePath).toLowerCase();
      if (fileName === "pd_api.h" || fileName.startsWith("pd_api_")) {
        headerPathsArray.push(filePath);
      }
    }
  } catch {
    return [];
  }

  headerPathsArray.sort();
  return headerPathsArray;
}

async function searchPlaydateHeaders(sdkRootPath, queryText, maxResultsCount = 12) {
  const headerPathsArray = await collectPlaydateHeaderPaths(sdkRootPath);
  const termsArray = splitQueryIntoTerms(queryText);
  const matchesArray = [];

  for (const filePath of headerPathsArray) {
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
        filePath: path.relative(sdkRootPath, filePath),
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

async function runSelfCheck() {
  const workspacePath = resolveWorkspacePath(process.argv[3]);
  const sdkPath = resolveSdkPath();
  const sdkExists = sdkPath ? await fileExists(sdkPath) : false;

  const outputObject = {
    workspacePath,
    sdkPath,
    sdkExists,
    placement: suggestPlacement("Playdate API self-check"),
  };

  process.stdout.write(`${JSON.stringify(outputObject, null, 2)}\n`);
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function runServer() {
  const server = new McpServer({
    name: "playdate-knowledge",
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
  ];

  server.registerTool(
    "playdate_query_api",
    {
      description: "Explains Playdate SDK API usage from installed headers and local workspace examples.",
      inputSchema: {
        workspacePath: z.string().optional(),
        sdkPath: z.string().optional(),
        query: z.string().min(1),
      },
    },
    async ({ workspacePath, sdkPath, query }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const resolvedSdkPath = resolveSdkPath(sdkPath);
      const queryText = String(query || "").trim();
      const apiMatchesArray = resolvedSdkPath ? await searchPlaydateHeaders(resolvedSdkPath, queryText, 12) : [];
      const localMatchesArray = await collectSearchLines(resolvedWorkspacePath, knowledgeRootsArray, queryText, 8);

      return textResult({
        workspacePath: resolvedWorkspacePath,
        sdkPath: resolvedSdkPath,
        query: queryText,
        placement: suggestPlacement(queryText),
        apiMatchesArray,
        localMatchesArray,
        sdkAvailable: Boolean(resolvedSdkPath),
      });
    },
  );

  server.registerTool(
    "playdate_search_examples",
    {
      description: "Finds Playdate-related examples and snippets in the workspace.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
        maxResults: z.number().int().positive().optional(),
      },
    },
    async ({ workspacePath, query, maxResults }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();
      const matchesArray = await collectSearchLines(resolvedWorkspacePath, knowledgeRootsArray, queryText, maxResults || 10);

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        matchesArray,
      });
    },
  );

  server.registerTool(
    "playdate_suggest_placement",
    {
      description: "Suggests where Playdate-specific code or data should live in the workspace.",
      inputSchema: {
        workspacePath: z.string().optional(),
        query: z.string().min(1),
      },
    },
    async ({ workspacePath, query }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const queryText = String(query || "").trim();

      return textResult({
        workspacePath: resolvedWorkspacePath,
        query: queryText,
        placement: suggestPlacement(queryText),
      });
    },
  );

  server.registerTool(
    "playdate_validate_integration",
    {
      description: "Checks Playdate SDK availability and bundle/layout assumptions.",
      inputSchema: {
        workspacePath: z.string().optional(),
        sdkPath: z.string().optional(),
      },
    },
    async ({ workspacePath, sdkPath }) => {
      const resolvedWorkspacePath = resolveWorkspacePath(workspacePath);
      const resolvedSdkPath = resolveSdkPath(sdkPath);
      const issuesArray = [];

      if (!resolvedSdkPath) {
        issuesArray.push({
          severity: "warning",
          code: "SDK_PATH_NOT_SET",
          message: "PLAYDATE_SDK_PATH is not set. Set it to your Playdate SDK install path to enable SDK API queries.",
        });
      }
      else if (!(await fileExists(resolvedSdkPath))) {
        issuesArray.push({
          severity: "error",
          code: "SDK_PATH_MISSING",
          message: `Playdate SDK path does not exist: ${resolvedSdkPath}`,
        });
      }

      const pdxInfoPath = path.join(resolvedWorkspacePath, "corgogame", "Source", "pdxinfo");
      if (!(await fileExists(pdxInfoPath))) {
        issuesArray.push({
          severity: "warning",
          code: "PDXINFO_MISSING",
          message: "Expected a per-game pdxinfo file at corgogame/Source/pdxinfo.",
        });
      }

      return textResult({
        workspacePath: resolvedWorkspacePath,
        sdkPath: resolvedSdkPath,
        placement: suggestPlacement("Playdate integration"),
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