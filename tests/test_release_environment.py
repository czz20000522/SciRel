from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "scripts" / "check_helpers.ps1"
CHECK = ROOT / "scripts" / "check.ps1"


def _resolve(environment: Path, platform: str):
    command = (
        f". '{HELPERS}'; "
        f"Resolve-SciRelVenvPython -EnvironmentPath '{environment}' -Platform {platform}"
    )
    return subprocess.run(
        ["pwsh", "-NoProfile", "-Command", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_release_python_path_is_resolved_for_windows_and_posix(tmp_path):
    windows = tmp_path / "windows"
    windows_python = windows / "Scripts" / "python.exe"
    windows_python.parent.mkdir(parents=True)
    windows_python.touch()

    posix = tmp_path / "posix"
    posix_python = posix / "bin" / "python"
    posix_python.parent.mkdir(parents=True)
    posix_python.touch()

    windows_result = _resolve(windows, "Windows")
    posix_result = _resolve(posix, "Posix")

    assert windows_result.returncode == 0, windows_result.stderr
    assert Path(windows_result.stdout.strip()) == windows_python
    assert posix_result.returncode == 0, posix_result.stderr
    assert Path(posix_result.stdout.strip()) == posix_python


def test_missing_release_python_fails_with_candidate_path(tmp_path):
    result = _resolve(tmp_path / "missing", "Posix")

    assert result.returncode != 0
    assert "Virtual environment Python was not created at" in result.stderr
    assert "bin" in result.stderr and "python" in result.stderr


def test_release_environment_does_not_inherit_system_packages():
    script = CHECK.read_text(encoding="utf-8")

    assert "--system-site-packages" not in script
    assert "--no-index --no-deps --force-reinstall" in script
    assert "import sys, numpy, scipy, pytest, scirel" in script


def test_release_gate_uses_the_current_baseline_and_an_approved_workflow():
    script = CHECK.read_text(encoding="utf-8")

    assert "-WorkflowSnapshot is required for release mode" in script
    assert "release requires an approved workflow snapshot" in script
    assert "scripts/build_admitted_distribution.py" not in script
    assert "-m pip wheel" in script
    assert "scripts/build_catalog.py" in script
    assert "scripts/finalize_release.py" in script
    assert '$catalogCoverageStatus = "partial"' in script
    assert "$catalogIncludedAssetCount = 14" in script
    assert "$catalogDeclaredTotalAssetCount = 62" in script
    assert '"--expected-coverage-status" $catalogCoverageStatus' in script
    assert '"--expected-included-asset-count" $catalogIncludedAssetCount' in script
    assert (
        '"--expected-declared-total-asset-count" '
        "$catalogDeclaredTotalAssetCount"
    ) in script
    assert '"--catalog-ref"' not in script
    assert '"--wheel-ref"' not in script
    assert "CatalogCoverageStatus" not in script
    assert "DeclaredAssetTotal" not in script


def test_release_gate_checks_the_installed_scientific_runtime():
    script = CHECK.read_text(encoding="utf-8")

    assert 'SCIREL_INSTALLED_RUNTIME = "1"' in script
    assert '"--installed-runtime"' in script
    assert '"operator_contracts", "graph_contracts", "framework_compositions"' in script
    assert '"test_library_composition.py", "test_public_surface.py"' in script
    assert '"runtime-test-bundle"' in script
