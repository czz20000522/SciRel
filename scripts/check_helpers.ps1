function Get-SciRelCatalogCoverage {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$RepositoryRoot,
        [string]$Python = "python"
    )
    Push-Location $RepositoryRoot
    try {
        $result = & $Python -c @'
import json
from pathlib import Path
from scripts.validate_asset_documents import load_document_set
from scripts.select_affected_tests import _load_assets
included = len(load_document_set(Path('catalog/examples')))
declared = len(_load_assets())
if not included or included > declared:
    raise SystemExit('invalid current catalog coverage')
print(json.dumps({'status': 'complete' if included == declared else 'partial',
                  'included': included, 'declared': declared}))
'@
        if ($LASTEXITCODE -ne 0) {
            throw "Cannot determine current catalog coverage."
        }
        return ($result | ConvertFrom-Json)
    }
    finally { Pop-Location }
}

function Resolve-SciRelVenvPython {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvironmentPath,

        [ValidateSet("Windows", "Posix")]
        [string]$Platform = $(if ($IsWindows) { "Windows" } else { "Posix" })
    )

    $relativePath = if ($Platform -eq "Windows") {
        "Scripts/python.exe"
    }
    else {
        "bin/python"
    }
    $candidate = Join-Path $EnvironmentPath $relativePath
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "Virtual environment Python was not created at $candidate"
    }
    return (Get-Item -LiteralPath $candidate).FullName
}
