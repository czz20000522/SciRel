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
included = len(load_document_set(Path('catalog/examples')))
if not included:
    raise SystemExit('invalid current catalog coverage')
print(json.dumps({'status': 'complete', 'included': included,
                  'declared': included}))
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
