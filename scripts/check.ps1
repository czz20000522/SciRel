[CmdletBinding()]
param(
    [ValidateSet("affected", "focused", "full", "release")]
    [string]$Mode = "focused",

    [string[]]$TestPath = @(),

    [string[]]$ChangedPath = @(),

    [string]$BaseRef,

    [string]$Python = "python",

    [string]$OutputRoot,

    [string]$WorkflowSnapshot,

    [string]$ReleaseId,

    [string]$CatalogId = "scirel-development"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "SciRel checks require pwsh 7 or newer."
}

. (Join-Path $PSScriptRoot "check_helpers.ps1")

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourcePath = (Resolve-Path (Join-Path $repoRoot "src")).Path
$testsPath = (Resolve-Path (Join-Path $repoRoot "tests")).Path
$previousPythonPath = $env:PYTHONPATH
$previousInstalledRuntime = $env:SCIREL_INSTALLED_RUNTIME
$releaseOutputPath = $null
$workflowSnapshotPath = $null

if ($Mode -eq "release") {
    if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
        throw "-OutputRoot is required for release mode and must name a new directory."
    }

    $releaseOutputPath = [IO.Path]::GetFullPath($OutputRoot, $repoRoot)
    if (Test-Path -LiteralPath $releaseOutputPath) {
        throw "Release output already exists: $releaseOutputPath"
    }
    if ([string]::IsNullOrWhiteSpace($WorkflowSnapshot)) {
        throw "-WorkflowSnapshot is required for release mode."
    }
    if ([string]::IsNullOrWhiteSpace($ReleaseId)) {
        throw "-ReleaseId is required for release mode."
    }
    $workflowSnapshotPath = [IO.Path]::GetFullPath($WorkflowSnapshot, $repoRoot)
    if (-not (Test-Path -LiteralPath $workflowSnapshotPath -PathType Leaf)) {
        throw "Approved workflow snapshot does not exist: $workflowSnapshotPath"
    }
    throw "Public release is suspended until a trusted whole-version review gate is implemented; an approved item snapshot does not authorize this wheel."
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

        $workflowValidation = @'
import json
import sys
from pathlib import Path
from scirel_workflow import SciRelWorkflow, WorkflowStatus

workflow = SciRelWorkflow.from_dict(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
if workflow.status is not WorkflowStatus.APPROVED:
    raise SystemExit("release requires an approved workflow snapshot")
'@
        & $Python -c $workflowValidation $workflowSnapshotPath
        if ($LASTEXITCODE -ne 0) {
            throw "Approved workflow snapshot validation failed with exit code $LASTEXITCODE."
        }

        New-Item -ItemType Directory -Path $releaseOutputPath | Out-Null
        $documentValidation = & $Python "scripts/validate_asset_documents.py" `
            "catalog/examples" `
            "--check-runtime" `
            "--execute-examples"
        if ($LASTEXITCODE -ne 0) {
            throw "Source asset-document validation failed with exit code $LASTEXITCODE."
        }

        $wheelDirectory = Join-Path $releaseOutputPath "wheel"
        New-Item -ItemType Directory -Path $wheelDirectory | Out-Null
        & $Python -m pip wheel `
            --disable-pip-version-check `
            --no-deps `
            --no-build-isolation `
            --wheel-dir $wheelDirectory `
            $repoRoot
        if ($LASTEXITCODE -ne 0) {
            throw "SciRel wheel build failed with exit code $LASTEXITCODE."
        }
        $wheels = @(Get-ChildItem -LiteralPath $wheelDirectory -Filter "scirel-*.whl" -File)
        if ($wheels.Count -ne 1) {
            throw "Release build must produce exactly one SciRel wheel; found $($wheels.Count)."
        }
        $wheelPath = $wheels[0].FullName

        $environmentPath = Join-Path $releaseOutputPath "environment"
        Invoke-Python -Arguments @("-m", "venv", $environmentPath)
        $environmentPython = Resolve-SciRelVenvPython -EnvironmentPath $environmentPath

        $dependencyRootsJson = & $Python -c @'
import importlib.util
import json
from pathlib import Path

roots = []
for name in ("numpy", "scipy", "pytest"):
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
            throw "Installing the SciRel wheel failed with exit code $LASTEXITCODE."
        }

        & $environmentPython -I -c "import sys, numpy, scipy, pytest, scirel; from pathlib import Path; assert Path(scirel.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())"
        if ($LASTEXITCODE -ne 0) {
            throw "The wheel or its declared runtime dependencies are unavailable in the release environment."
        }
        $releaseVersion = (& $environmentPython -I -c "import importlib.metadata; print(importlib.metadata.version('scirel'))").Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($releaseVersion)) {
            throw "Failed to read the installed SciRel distribution version."
        }

        $catalogCoverageStatus = "partial"
        $catalogIncludedAssetCount = 23
        $catalogDeclaredTotalAssetCount = 68
        $catalogPath = Join-Path $releaseOutputPath "catalog"
        $catalogOutput = & $Python "scripts/build_catalog.py" `
            "catalog/examples" `
            "--output-dir" $catalogPath `
            "--catalog-id" $CatalogId `
            "--release-version" $releaseVersion `
            "--coverage-status" $catalogCoverageStatus `
            "--declared-total" $catalogDeclaredTotalAssetCount
        if ($LASTEXITCODE -ne 0) {
            throw "Catalog build failed with exit code $LASTEXITCODE."
        }
        $catalogBuild = $catalogOutput | ConvertFrom-Json

        $env:PYTHONPATH = $null
        $env:SCIREL_INSTALLED_RUNTIME = "1"
        $acceptancePath = Join-Path $releaseOutputPath "acceptance"
        Push-Location $releaseOutputPath
        try {
            $installedValidation = & $environmentPython -I `
                (Join-Path $repoRoot "scripts/validate_asset_documents.py") `
                (Join-Path $repoRoot "catalog/examples") `
                "--check-runtime" `
                "--execute-examples" `
                "--installed-runtime"
            if ($LASTEXITCODE -ne 0) {
                throw "Installed asset-document validation failed with exit code $LASTEXITCODE."
            }
            [IO.File]::WriteAllText(
                (Join-Path $releaseOutputPath "installed-asset-validation.json"),
                ([string]$installedValidation + [Environment]::NewLine),
                [Text.UTF8Encoding]::new($false)
            )

            $runtimeBundle = Join-Path $releaseOutputPath "runtime-test-bundle"
            $runtimeTestRoot = Join-Path $runtimeBundle "tests"
            $runtimeCatalogExamples = Join-Path $runtimeBundle "catalog/examples"
            New-Item -ItemType Directory -Path $runtimeTestRoot | Out-Null
            New-Item -ItemType Directory -Path $runtimeCatalogExamples | Out-Null
            Copy-Item -LiteralPath (Join-Path $repoRoot "tests/conftest.py") -Destination $runtimeTestRoot
            Copy-Item -LiteralPath (Join-Path $repoRoot "tests/_review_bindings.py") -Destination $runtimeTestRoot
            foreach ($directory in @("operator_contracts", "graph_contracts", "framework_compositions")) {
                Copy-Item `
                    -LiteralPath (Join-Path $repoRoot "tests/$directory") `
                    -Destination $runtimeTestRoot `
                    -Recurse
            }
            foreach ($file in @("test_library_composition.py", "test_public_surface.py")) {
                Copy-Item -LiteralPath (Join-Path $repoRoot "tests/$file") -Destination $runtimeTestRoot
            }
            Copy-Item `
                -Path (Join-Path $repoRoot "catalog/examples/*.json") `
                -Destination $runtimeCatalogExamples

            $isolatedPytestConfig = Join-Path $releaseOutputPath "pytest-release.ini"
            [IO.File]::WriteAllText(
                $isolatedPytestConfig,
                "[pytest]`naddopts = -p no:cacheprovider`npythonpath = runtime-test-bundle/tests`n",
                [Text.UTF8Encoding]::new($false)
            )
            $runtimeTests = @(
                (Join-Path $runtimeTestRoot "operator_contracts"),
                (Join-Path $runtimeTestRoot "graph_contracts"),
                (Join-Path $runtimeTestRoot "framework_compositions"),
                (Join-Path $runtimeTestRoot "test_library_composition.py"),
                (Join-Path $runtimeTestRoot "test_public_surface.py")
            )
            & $environmentPython -I -m pytest -c $isolatedPytestConfig @runtimeTests
            if ($LASTEXITCODE -ne 0) {
                throw "Installed scientific contract tests failed with exit code $LASTEXITCODE."
            }

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

        $releaseMetadataPath = Join-Path $releaseOutputPath "release"
        $finalizationOutput = & $Python "scripts/finalize_release.py" `
            "--workflow-snapshot" $workflowSnapshotPath `
            "--documents-dir" (Join-Path $repoRoot "catalog/examples") `
            "--catalog-dir" $catalogPath `
            "--wheel" $wheelPath `
            "--output-dir" $releaseMetadataPath `
            "--release-id" $ReleaseId `
            "--expected-coverage-status" $catalogCoverageStatus `
            "--expected-included-asset-count" $catalogIncludedAssetCount `
            "--expected-declared-total-asset-count" $catalogDeclaredTotalAssetCount
        if ($LASTEXITCODE -ne 0) {
            throw "Release finalization failed with exit code $LASTEXITCODE."
        }
        $finalization = $finalizationOutput | ConvertFrom-Json

        [ordered]@{
            output_root = $releaseOutputPath
            wheel = $wheelPath
            wheel_sha256 = $finalization.wheel_digest
            catalog = (Join-Path $catalogPath "release.json")
            catalog_digest = $catalogBuild.root_digest
            release_manifest = $finalization.release_manifest
            release_digest = $finalization.release_digest
            installed_asset_validation = (Join-Path $releaseOutputPath "installed-asset-validation.json")
            acceptance_report = (Join-Path $acceptancePath "acceptance.json")
        } | ConvertTo-Json
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:SCIREL_INSTALLED_RUNTIME = $previousInstalledRuntime
}
