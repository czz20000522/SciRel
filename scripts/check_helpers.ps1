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
