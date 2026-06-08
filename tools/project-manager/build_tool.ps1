param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Split-Path -Parent (Split-Path -Parent $toolRoot)
$outputRoot = Join-Path $workspaceRoot "tools/bin"
$outputName = "project-manager"

function Invoke-ExternalCommand {
    param(
        [string]$Executable,
        [string[]]$ArgumentList,
        [string]$StepName
    )

    & $Executable @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName failed with exit code $LASTEXITCODE"
    }
}

function Resolve-PythonCommand {
    param([string]$RequestedPythonPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPythonPath)) {
        return @($RequestedPythonPath)
    }

    $candidates = @(
        @{ Exe = "py"; Args = @("-3.13") },
        @{ Exe = "py"; Args = @("-3.12") },
        @{ Exe = "py"; Args = @("-3.11") },
        @{ Exe = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $versionArgs = @($candidate.Args + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"))
        $versionOutput = & $candidate.Exe @versionArgs 2>$null
        if ($LASTEXITCODE -ne 0) {
            continue
        }

        $versionText = ($versionOutput | Select-Object -First 1).Trim()
        if ($versionText -match "^3\.(11|12|13)$") {
            return @($candidate.Exe) + $candidate.Args
        }
    }

    throw "No supported Python version found. How to fix: install Python 3.11, 3.12, or 3.13, or pass -PythonPath explicitly."
}

$pythonCommand = Resolve-PythonCommand -RequestedPythonPath $PythonPath
$pythonExe = $pythonCommand[0]
$pythonPrefixArgs = @()
if ($pythonCommand.Count -gt 1) {
    $pythonPrefixArgs = $pythonCommand[1..($pythonCommand.Count - 1)]
}

$selectedVersion = & $pythonExe @pythonPrefixArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to query selected Python version."
}
Write-Host "Using Python: $($pythonCommand -join ' ') ($selectedVersion)"

Write-Host "Installing packaging dependencies..."
Invoke-ExternalCommand -Executable $pythonExe -ArgumentList @($pythonPrefixArgs + @("-m", "pip", "install", "-r", (Join-Path $toolRoot "requirements.txt"))) -StepName "Dependency installation"

Write-Host "Building executable..."
Invoke-ExternalCommand -Executable $pythonExe -ArgumentList @(
    $pythonPrefixArgs + @(
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        $outputRoot,
        "--workpath",
        (Join-Path $toolRoot "build"),
        (Join-Path $toolRoot "project-manager.spec")
    )
) -StepName "PyInstaller build"

Write-Host "Build complete: $(Join-Path $outputRoot $outputName)"
