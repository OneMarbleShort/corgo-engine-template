<#
.SYNOPSIS
Installs and configures useful MCP servers for a VS Code workspace on Windows 11.

.DESCRIPTION
Installs prerequisites with WinGet when needed, installs Serena through uv,
and creates or updates .vscode\mcp.json for the selected project.

Configured servers:
- Serena: semantic code navigation and editing
- Context7: current library/API documentation
- Filesystem: restricted to the selected project directory
- Git: repository history, status, diffs, and commits
- Memory: persistent project notes/knowledge graph
- Microsoft Learn: current Microsoft documentation

The script backs up an existing mcp.json before modifying it.

.EXAMPLE
.\Install-TimeBoundMCPs.ps1 -ProjectPath "C:\Projects\TimeBound"

.EXAMPLE
.\Install-TimeBoundMCPs.ps1 -ProjectPath . -SkipPrerequisiteInstall
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$ProjectPath = (Get-Location).Path,

    [switch]$SkipPrerequisiteInstall,

    [switch]$SkipSerena,

    [switch]$SkipReferenceServers,

    [switch]$OpenInVSCode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([Parameter(Mandatory)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WinGetPackage {
    param(
        [Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)][string]$DisplayName
    )

    Write-Step "Installing $DisplayName"
    & winget install --exact --id $Id --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "WinGet failed to install $DisplayName ($Id). Exit code: $LASTEXITCODE"
    }
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function ConvertTo-HashtableRecursive {
    param([Parameter(ValueFromPipeline)]$InputObject)

    if ($null -eq $InputObject) {
        return $null
    }

    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $table = [ordered]@{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $table[$property.Name] = ConvertTo-HashtableRecursive $property.Value
        }
        return $table
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and
        $InputObject -isnot [string] -and
        $InputObject -isnot [System.Collections.IDictionary]) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(ConvertTo-HashtableRecursive $item)
        }
        return $items
    }

    return $InputObject
}

# Resolve and validate the project path.
$projectPathCandidate = if ([System.IO.Path]::IsPathRooted($ProjectPath)) {
    $ProjectPath
}
else {
    Join-Path (Get-Location).Path $ProjectPath
}

$resolvedProjectPath = [System.IO.Path]::GetFullPath($projectPathCandidate)

if (-not (Test-Path -LiteralPath $resolvedProjectPath)) {
    throw "Project path does not exist: '$resolvedProjectPath'. Provide an existing workspace path."
}

$resolvedProjectPath = (Resolve-Path -LiteralPath $resolvedProjectPath).Path
Write-Host "Project: $resolvedProjectPath" -ForegroundColor Green

$requiredCommands = @()

if (-not $SkipReferenceServers) {
    $requiredCommands += @("git", "node", "npx", "uv", "uvx")
}

if (-not $SkipSerena) {
    $requiredCommands += "uv"
}

if ($OpenInVSCode) {
    $requiredCommands += "code"
}

$requiredCommands = @($requiredCommands | Sort-Object -Unique)

if (-not $SkipPrerequisiteInstall) {
    $missingCommands = @($requiredCommands | Where-Object { -not (Test-Command $_) })

    if ($missingCommands.Count -gt 0 -and -not (Test-Command winget)) {
        throw "WinGet is required. Install or update 'App Installer' from the Microsoft Store, then rerun this script."
    }

    if ($requiredCommands -contains "code" -and -not (Test-Command code)) {
        Install-WinGetPackage -Id "Microsoft.VisualStudioCode" -DisplayName "Visual Studio Code"
        Refresh-ProcessPath
    }

    if ($requiredCommands -contains "git" -and -not (Test-Command git)) {
        Install-WinGetPackage -Id "Git.Git" -DisplayName "Git"
        Refresh-ProcessPath
    }

    if (($requiredCommands -contains "node" -or $requiredCommands -contains "npx") -and (-not (Test-Command node) -or -not (Test-Command npx))) {
        Install-WinGetPackage -Id "OpenJS.NodeJS.LTS" -DisplayName "Node.js LTS"
        Refresh-ProcessPath
    }

    if ($requiredCommands -contains "uv" -and -not (Test-Command uv)) {
        Install-WinGetPackage -Id "astral-sh.uv" -DisplayName "Astral uv"
        Refresh-ProcessPath
    }
}

foreach ($requiredCommand in $requiredCommands) {
    if (-not (Test-Command $requiredCommand)) {
        throw "'$requiredCommand' was not found on PATH. Open a new PowerShell window and rerun the script."
    }
}

if (-not $SkipSerena) {
    Write-Step "Installing or upgrading Serena"
    & uv tool install --upgrade -p 3.13 serena-agent
    if ($LASTEXITCODE -ne 0) {
        throw "Serena installation failed. Exit code: $LASTEXITCODE"
    }

    Refresh-ProcessPath

    if (-not (Test-Command serena)) {
        $uvToolBin = Join-Path $env:USERPROFILE ".local\bin"
        if (Test-Path $uvToolBin) {
            $env:Path = "$uvToolBin;$env:Path"
        }
    }

    if (-not (Test-Command serena)) {
        throw "Serena installed, but 'serena' is not yet on PATH. Open a new PowerShell window and rerun the script."
    }

    Write-Step "Initializing Serena"
    & serena init
    if ($LASTEXITCODE -ne 0) {
        throw "Serena initialization failed. Exit code: $LASTEXITCODE"
    }
}

$vscodeDirectory = Join-Path $resolvedProjectPath ".vscode"
$mcpPath = Join-Path $vscodeDirectory "mcp.json"
New-Item -ItemType Directory -Path $vscodeDirectory -Force | Out-Null

$config = [ordered]@{
    servers = [ordered]@{}
}

if (Test-Path -LiteralPath $mcpPath) {
    $backupPath = "$mcpPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -LiteralPath $mcpPath -Destination $backupPath
    Write-Host "Backed up existing configuration to: $backupPath" -ForegroundColor Yellow

    try {
        $existingJson = Get-Content -LiteralPath $mcpPath -Raw | ConvertFrom-Json
        $config = ConvertTo-HashtableRecursive $existingJson

        if (-not $config.Contains("servers")) {
            $config["servers"] = [ordered]@{}
        }
    }
    catch {
        throw "The existing '$mcpPath' is not valid JSON. A backup was created, but the file was not changed. Remove JSON comments or fix the file and rerun."
    }
}

$servers = $config["servers"]

if (-not $SkipSerena) {
    $servers["serena"] = [ordered]@{
        type = "stdio"
        command = "serena"
        args = @(
            "start-mcp-server",
            "--context=vscode",
            "--project",
            '${workspaceFolder}'
        )
    }
}

$servers["context7"] = [ordered]@{
    type = "http"
    url = "https://mcp.context7.com/mcp"
}

$servers["microsoftLearn"] = [ordered]@{
    type = "http"
    url = "https://learn.microsoft.com/api/mcp"
}

if (-not $SkipReferenceServers) {
    $servers["filesystem"] = [ordered]@{
        type = "stdio"
        command = "npx"
        args = @(
            "-y",
            "@modelcontextprotocol/server-filesystem@latest",
            '${workspaceFolder}'
        )
    }

    $servers["git"] = [ordered]@{
        type = "stdio"
        command = "uvx"
        args = @(
            "mcp-server-git",
            "--repository",
            '${workspaceFolder}'
        )
    }

    $memoryDirectory = Join-Path $resolvedProjectPath ".mcp-memory"
    New-Item -ItemType Directory -Path $memoryDirectory -Force | Out-Null

    $servers["memory"] = [ordered]@{
        type = "stdio"
        command = "npx"
        args = @(
            "-y",
            "@modelcontextprotocol/server-memory@latest"
        )
        env = [ordered]@{
            MEMORY_FILE_PATH = '${workspaceFolder}\.mcp-memory\memory.json'
        }
    }
}

$config["servers"] = $servers
$json = $config | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText(
    $mcpPath,
    $json + [Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Step "MCP configuration written"
Write-Host $mcpPath -ForegroundColor Green

Write-Step "Validating installed commands"
if ($requiredCommands -contains "node") {
    & node --version
}
if ($requiredCommands -contains "npx") {
    & npx --version
}
if ($requiredCommands -contains "git") {
    & git --version
}
if ($requiredCommands -contains "uv") {
    & uv --version
}
if (-not $SkipSerena) {
    & serena --version
}

Write-Host @"

Setup complete.

Next steps:
1. Open the project in VS Code.
2. Press Ctrl+Shift+P.
3. Run 'MCP: List Servers'.
4. Start each server and approve the workspace trust prompts.
5. In Copilot Chat, switch to Agent mode and open the Tools menu.
6. Ask: 'Use Serena to activate and inspect this project.'

Notes:
- Filesystem access is restricted to this workspace.
- Existing .vscode\mcp.json content was preserved where possible.
- Context7 works without an API key, but its free authenticated setup can provide higher limits.
- The official filesystem, git, and memory servers are reference implementations; review permissions before allowing write operations.
"@ -ForegroundColor White

if ($OpenInVSCode) {
    Write-Step "Opening project in VS Code"
    & code $resolvedProjectPath
}
