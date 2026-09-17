[CmdletBinding()]
param(
    [ValidateSet("affected", "focused", "full", "release")]
    [string]$Mode = "focused",

    [string[]]$TestPath = @(),

    [string[]]$ChangedPath = @(),

    [string]$BaseRef,

    [string]$Python = "python",

    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "SciRel checks require pwsh 7 or newer."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourcePath = (Resolve-Path (Join-Path $repoRoot "src")).Path
$testsPath = (Resolve-Path (Join-Path $repoRoot "tests")).Path
$previousPythonPath = $env:PYTHONPATH
$releaseOutputPath = $null

if ($Mode -eq "release") {
    if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
        throw "-OutputRoot is required for release mode and must name a new directory."
    }

    $releaseOutputPath = [IO.Path]::GetFullPath($OutputRoot, $repoRoot)
    if (Test-Path -LiteralPath $releaseOutputPath) {
        throw "Release output already exists: $releaseOutputPath"
    }
}

if ($Mode -eq "affected" -and $TestPath.Count -ne 0) {
    throw "Use -ChangedPath or -BaseRef with affected mode; -TestPath belongs to focused mode."
}

if ($Mode -eq "affected" -and $ChangedPath.Count -ne 0 -and -not [string]::IsNullOrWhiteSpace($BaseRef)) {
    throw "Use either -ChangedPath or -BaseRef with affected mode, not both."
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $Python $($Arguments -join ' ')"
    }
}

try {
    $env:PYTHONPATH = [string]::Join(
        [IO.Path]::PathSeparator,
        @($sourcePath, $testsPath)
    )

    Push-Location $repoRoot
    try {
        if ($Mode -eq "affected") {
            $selectorArguments = @("scripts/select_affected_tests.py", "--format", "json")
            foreach ($path in $ChangedPath) {
                $selectorArguments += @("--changed-path", $path)
            }
            if (-not [string]::IsNullOrWhiteSpace($BaseRef)) {
                $selectorArguments += @("--base-ref", $BaseRef)
            }
            $selectionOutput = & $Python @selectorArguments
            if ($LASTEXITCODE -ne 0) {
                throw "Affected test selection failed with exit code $LASTEXITCODE."
            }
            $selection = $selectionOutput | ConvertFrom-Json
            $selection | ConvertTo-Json -Depth 8
            if ($selection.full_suite_required) {
                Invoke-Python -Arguments @("-m", "pytest")
            }
            elseif ($selection.test_paths.Count -gt 0) {
                Invoke-Python -Arguments (@("-m", "pytest") + @($selection.test_paths))
            }
            else {
                Write-Host "No scientific or engineering tests are required for the selected changes."
            }
        }
        elseif ($Mode -eq "focused") {
            if ($TestPath.Count -eq 0) {
                $TestPath = @(
                    "tests/test_public_surface.py",
                    "tests/test_library_composition.py",
                    "tests/test_admitted_integrations.py",
                    "tests/test_asset_documentation.py"
                )
            }
            Invoke-Python -Arguments (@("-m", "pytest") + $TestPath)
        }
        else {
            Invoke-Python -Arguments @("-m", "pytest")
        }

        if ($Mode -ne "release") {
            return
        }

        New-Item -ItemType Directory -Path $releaseOutputPath | Out-Null
        $stagingPath = Join-Path $releaseOutputPath "staging"
        $wheelDirectory = Join-Path $releaseOutputPath "wheel"
        $buildOutput = & $Python "scripts/build_admitted_distribution.py" `
            "--staging-dir" $stagingPath `
            "--wheel-dir" $wheelDirectory
        if ($LASTEXITCODE -ne 0) {
            throw "Admitted distribution build failed with exit code $LASTEXITCODE."
        }
        $build = $buildOutput | ConvertFrom-Json
        $wheelPath = [IO.Path]::GetFullPath([string]$build.wheel)

        $environmentPath = Join-Path $releaseOutputPath "environment"
        Invoke-Python -Arguments @("-m", "venv", "--system-site-packages", $environmentPath)
        $environmentPython = Join-Path $environmentPath "Scripts/python.exe"
        if (-not (Test-Path -LiteralPath $environmentPython)) {
            throw "Isolated Python was not created at $environmentPython"
        }

        $dependencyRootsJson = & $Python -c @'
import importlib.util
import json
from pathlib import Path

roots = []
for name in ("numpy", "scipy"):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(f"missing release dependency: {name}")
    root = str(Path(spec.origin).resolve().parent.parent)
    if root not in roots:
        roots.append(root)
print(json.dumps(roots))
'@
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to locate release dependencies."
        }
        $dependencyRoots = $dependencyRootsJson | ConvertFrom-Json
        $sitePackages = & $environmentPython -c "import site; print(site.getsitepackages()[0])"
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to locate isolated site-packages."
        }
        $pthPath = Join-Path ([string]$sitePackages).Trim() "scirel-check-dependencies.pth"
        [IO.File]::WriteAllText(
            $pthPath,
            (($dependencyRoots -join [Environment]::NewLine) + [Environment]::NewLine),
            [Text.UTF8Encoding]::new($false)
        )

        & $environmentPython -m pip install --disable-pip-version-check `
            --no-index --no-deps --force-reinstall $wheelPath
        if ($LASTEXITCODE -ne 0) {
            throw "Installing the admitted wheel failed with exit code $LASTEXITCODE."
        }

        $env:PYTHONPATH = $null
        $acceptancePath = Join-Path $releaseOutputPath "acceptance"
        Push-Location $releaseOutputPath
        try {
            & $environmentPython (Join-Path $repoRoot "examples/user_acceptance.py") `
                "--wheel" $wheelPath `
                "--output" $acceptancePath
            if ($LASTEXITCODE -ne 0) {
                throw "Source-free user acceptance failed with exit code $LASTEXITCODE."
            }
        }
        finally {
            Pop-Location
        }

        [ordered]@{
            output_root = $releaseOutputPath
            wheel = $wheelPath
            wheel_sha256 = $build.wheel_sha256
            manifest_digest = $build.manifest_digest
            acceptance_report = (Join-Path $acceptancePath "acceptance.json")
        } | ConvertTo-Json
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
