from pathlib import Path
import json
import os
import subprocess

import pytest

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
    assert "sysconfig.get_path('purelib')" in script
    assert "site.getsitepackages()[0]" not in script
    assert "import sys, numpy, scipy, pytest, scirel" in script


def test_release_gate_builds_from_exact_review_inputs():
    script = CHECK.read_text(encoding="utf-8")

    assert "[string]$ReleaseIndex" in script
    assert "[string]$CandidateEntryId" in script
    assert "[string]$ApprovedResults" in script
    assert "[string]$ReviewArtifactsDir" in script
    assert "--workflow-snapshot" not in script
    assert "scripts/build_admitted_distribution.py" not in script
    assert "-m pip wheel" in script
    assert "scripts/prepare_reviewed_distribution.py" in script
    assert "scripts/build_catalog.py" in script
    assert "scripts/finalize_release.py" in script
    assert '$reviewedDocuments = $preparation.documents_dir' in script
    assert '"--declared-total" $preparation.asset_count' in script
    assert '"--release-index" $releaseIndexPath' in script
    assert '"--candidate-entry-id" $CandidateEntryId' in script
    assert '"--approved-results" $approvedResultsPath' in script
    assert '"--review-artifacts-dir" $reviewArtifactsPath' in script
    assert '"--catalog-ref"' not in script
    assert '"--wheel-ref"' not in script
    assert "CatalogCoverageStatus" not in script
    assert "DeclaredAssetTotal" not in script


def test_release_gate_requires_review_inputs_before_creating_output(tmp_path):
    output = tmp_path / "release-output"
    result = subprocess.run(
        [
            "pwsh", "-NoProfile", "-File", str(CHECK), "-Mode", "release",
            "-OutputRoot", str(output), "-ReleaseId", "release-test",
            "-CandidateEntryId", "candidate:test",
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )

    assert result.returncode != 0
    assert "-ReleaseIndex is required for release mode" in result.stderr
    assert not output.exists()


def test_release_gate_checks_the_installed_scientific_runtime():
    script = CHECK.read_text(encoding="utf-8")

    assert 'SCIREL_INSTALLED_RUNTIME = "1"' in script
    assert '"--installed-runtime"' in script
    assert 'foreach ($file in $preparation.test_paths)' in script
    assert '"runtime-test-bundle"' in script


def test_first_release_mode_smoke_from_review_fixture(tmp_path):
    if os.environ.get("SCIREL_RELEASE_SMOKE_CHILD") == "1":
        pytest.skip("release gate is already running its source suite")
    if os.environ.get("SCIREL_RUN_RELEASE_SMOKE") != "1":
        pytest.skip("run explicitly for the full release gate")

    from test_release_index import _candidate_entry_id, _reviewed_release_inputs

    git_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    artifacts, _, _, _, _ = _reviewed_release_inputs(
        tmp_path, git_revision=git_revision
    )
    output = tmp_path / "release-output"
    environment = os.environ.copy()
    environment["SCIREL_RELEASE_SMOKE_CHILD"] = "1"
    environment.pop("SCIREL_RUN_RELEASE_SMOKE", None)
    result = subprocess.run(
        [
            "pwsh", "-NoProfile", "-File", str(CHECK), "-Mode", "release",
            "-OutputRoot", str(output), "-ReleaseId", "release-smoke",
            "-ReleaseIndex", str(tmp_path / "index.json"),
            "-CandidateEntryId", _candidate_entry_id(tmp_path / "index.json"),
            "-ApprovedResults", str(tmp_path / "results.json"),
            "-ReviewArtifactsDir", str(artifacts),
        ],
        cwd=ROOT, env=environment, capture_output=True, text=True,
        encoding="utf-8", timeout=600,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    manifest = json.loads((output / "release" / "release-manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((output / "installed-asset-validation.json").read_text(encoding="utf-8"))
    assert manifest["included_assets"] == ["scirel.field.circular-filament-green"]
    assert validation["asset_count"] == 1
    assert validation["runtime_origin"] == "installed"
