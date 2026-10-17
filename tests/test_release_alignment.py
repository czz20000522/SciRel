from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_release_alignment import (
    _validate_build_inputs,
    _validate_external_artifacts,
    _validate_platform_receipts,
    _validate_documentation_version,
    _validate_wheel_metadata,
    _validate_wheel_contents,
    _validate_source_revision,
    validate_alignment,
)  # noqa: E402


def test_current_release_alignment_is_exact() -> None:
    result = validate_alignment(ROOT)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert result["wheel_version"] == project["project"]["version"]
    assert _validate_documentation_version(
        current["documentation"], wheel_version=project["project"]["version"]
    ) == result["documentation_version"]
    assert result["documentation_source_revision"] == current["source_revision"]
    assert result["documentation_selection"] == "scientific-core-current"
    assert result["source_revision"] == current["source_revision"]
    assert result["capability_counts"] == {
        "operators": 235,
        "task_graphs": 32,
        "document_closure": 267,
    }
    assert result["external_artifacts"] == "external_artifact_unchecked"


def test_source_revision_is_a_git_commit_with_matching_project_version() -> None:
    revision = "34d06da7a839870ee0c082418883de70551d37e0"
    _validate_source_revision(ROOT, revision, "0.1.0.dev9")
    with pytest.raises(ValueError, match="pyproject.toml version"):
        _validate_source_revision(ROOT, revision, "0.1.0.dev10")


def test_external_manifest_input_digests_bind_to_source_git_blobs() -> None:
    import hashlib
    import subprocess

    revision = "34d06da7a839870ee0c082418883de70551d37e0"
    pyproject = subprocess.check_output(
        ["git", "show", f"{revision}:pyproject.toml"], cwd=ROOT
    )
    helper = ROOT / "scripts/build_scirel_from_ref.py"
    manifest = {
        "inputs": {
            "schema": "scirel.build-inputs.v1",
            "files": {
                "pyproject.toml": {
                    "sha256": hashlib.sha256(pyproject).hexdigest(),
                    "bytes": len(pyproject),
                }
            },
            "license_files": [],
            "helper": {
                "revision": None,
                "dirty": True,
                "files": {
                    "scripts/build_scirel_from_ref.py": {
                        "sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                        "bytes": helper.stat().st_size,
                    }
                },
            },
        }
    }
    _validate_build_inputs(
        ROOT,
        manifest,
        source_revision=revision,
        field="wheel",
    )
    manifest["inputs"]["files"]["pyproject.toml"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs from source revision"):
        _validate_build_inputs(ROOT, manifest, source_revision=revision, field="wheel")


def test_external_artifact_manifest_and_snapshot_are_verified(tmp_path: Path) -> None:
    import hashlib

    revision = "a" * 40
    version = "0.1.0.dev9"
    artifact_root = tmp_path / "artifacts"
    wheel_dir = artifact_root / "scirel" / version / revision / "wheel"
    docs_dir = artifact_root / "scirel" / version / revision / "docs"
    wheel_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)
    wheel_bytes = b"test wheel bytes"
    wheel_path = wheel_dir / "scirel-0.1.0.dev9-py3-none-any.whl"
    wheel_path.write_bytes(wheel_bytes)
    wheel_manifest = {
        "schema": "scirel.git-build.v1",
        "source": {"revision": revision},
        "project": {"name": "scirel", "version": version},
        "wheel": {
            "filename": wheel_path.name,
            "sha256": hashlib.sha256(wheel_bytes).hexdigest(),
            "bytes": len(wheel_bytes),
        },
    }
    wheel_manifest_path = wheel_dir / "build-manifest.json"
    wheel_manifest_path.write_text(json.dumps(wheel_manifest, sort_keys=True), encoding="utf-8")

    snapshot_dir = docs_dir / "snapshot"
    snapshot_dir.mkdir()
    content = b"snapshot content"
    (snapshot_dir / "index.html").write_bytes(content)
    unsigned = {
        "schema": "scirel.documentation-snapshot.v1",
        "source_revision": revision,
        "project_version": version,
        "files": {
            "index.html": {
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
            }
        },
    }
    encoded_unsigned = (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    snapshot_digest = hashlib.sha256(encoded_unsigned).hexdigest()
    snapshot_manifest = dict(unsigned, snapshot_sha256=snapshot_digest)
    snapshot_manifest_path = snapshot_dir / "manifest.json"
    snapshot_manifest_path.write_text(
        json.dumps(snapshot_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    snapshot_bytes = snapshot_manifest_path.stat().st_size + len(content)
    docs_manifest = {
        "schema": "scirel.git-docs-build.v1",
        "source": {"revision": revision},
        "project": {"name": "scirel", "version": version},
        "selection": {"sha256": "c" * 64},
        "snapshot": {"path": "snapshot", "sha256": snapshot_digest, "bytes": snapshot_bytes},
    }
    docs_manifest_path = docs_dir / "build-manifest.json"
    docs_manifest_path.write_text(json.dumps(docs_manifest, sort_keys=True), encoding="utf-8")

    wheel_artifact = {
        "manifest_ref": f"scirel/{version}/{revision}/wheel/build-manifest.json",
        "manifest_sha256": hashlib.sha256(wheel_manifest_path.read_bytes()).hexdigest(),
        "filename": wheel_path.name,
        "sha256": wheel_manifest["wheel"]["sha256"],
        "bytes": len(wheel_bytes),
    }
    docs_artifact = {
        "manifest_ref": f"scirel/{version}/{revision}/docs/build-manifest.json",
        "manifest_sha256": hashlib.sha256(docs_manifest_path.read_bytes()).hexdigest(),
        "snapshot_ref": "snapshot",
        "snapshot_sha256": snapshot_digest,
        "snapshot_bytes": snapshot_bytes,
    }
    current = {
        "wheel": {"artifact": wheel_artifact},
        "documentation": {"artifact": docs_artifact, "snapshot_sha256": snapshot_digest, "selection_sha256": "c" * 64},
    }
    assert _validate_external_artifacts(
        ROOT,
        current,
        version=version,
        source_revision=revision,
        artifact_root=artifact_root,
    ) == "external_artifact_verified"
    revised_current = json.loads(json.dumps(current))
    revised_current["documentation"]["version"] = "0.1.1"
    with pytest.raises(ValueError, match="documentation manifest documentation version"):
        _validate_external_artifacts(
            ROOT,
            revised_current,
            version=version,
            source_revision=revision,
            artifact_root=artifact_root,
        )
    (snapshot_dir / "index.html").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="snapshot file differs"):
        _validate_external_artifacts(
            ROOT,
            current,
            version=version,
            source_revision=revision,
            artifact_root=artifact_root,
        )

def test_external_artifact_reference_rejects_path_traversal() -> None:
    current = {
        "wheel": {"artifact": {"manifest_ref": "../wheel.json", "manifest_sha256": "a" * 64, "filename": "a.whl", "sha256": "b" * 64, "bytes": 1}},
        "documentation": {"artifact": {"manifest_ref": "docs.json", "manifest_sha256": "c" * 64, "snapshot_ref": "snapshot", "snapshot_sha256": "d" * 64, "snapshot_bytes": 1}},
    }
    with pytest.raises(ValueError, match="unsafe artifact reference"):
        _validate_external_artifacts(ROOT, current, version="0.1.0.dev9", source_revision=None, artifact_root=None)


def test_wheel_contents_binding_rejects_member_byte_drift(tmp_path: Path) -> None:
    import hashlib
    import zipfile

    wheel = tmp_path / "scirel.whl"
    payload = b"print('ok')\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("scirel/foo.py", payload)
    digest = hashlib.sha256(payload).hexdigest()
    binding = {
        "schema": "scirel.wheel-contents.v1",
        "members": [{"path": "scirel/foo.py", "sha256": digest, "bytes": len(payload)}],
        "package_members": ["scirel/foo.py"],
    }
    assert _validate_wheel_contents(wheel, binding) == {"scirel/foo.py"}
    binding["members"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="member bytes differ"):
        _validate_wheel_contents(wheel, binding)


def test_wheel_metadata_parity_covers_python_dependencies_and_extras(tmp_path: Path) -> None:
    import zipfile

    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "scirel"
version = "0.1.0.dev9"
requires-python = ">=3.14,<3.15"
dependencies = ["numpy==2.5.4", "scipy==1.18.1"]

[project.optional-dependencies]
plot = ["matplotlib==3.11.2"]
netcdf = ["netCDF4==1.7.4"]
""",
        encoding="utf-8",
    )
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    metadata = """Metadata-Version: 2.4
Name: scirel
Version: 0.1.0.dev9
Requires-Python: <3.15,>=3.14
Requires-Dist: numpy==2.5.4
Requires-Dist: scipy==1.18.1
Provides-Extra: plot
Requires-Dist: matplotlib==3.11.2; extra == "plot"
Provides-Extra: netcdf
Requires-Dist: netCDF4==1.7.4; extra == "netcdf"

"""
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("scirel-0.1.0.dev9.dist-info/METADATA", metadata)

    _validate_wheel_metadata(tmp_path, wheel, source_revision=None)


def test_wheel_metadata_parity_rejects_dependency_drift(tmp_path: Path) -> None:
    import zipfile

    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "scirel"
version = "0.1.0.dev9"
requires-python = ">=3.14,<3.15"
dependencies = ["numpy==2.5.4"]

[project.optional-dependencies]
plot = ["matplotlib==3.11.2"]
""",
        encoding="utf-8",
    )
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    metadata = """Metadata-Version: 2.4
Name: scirel
Version: 0.1.0.dev9
Requires-Python: >=3.14,<3.15
Requires-Dist: numpy==2.5.3
Provides-Extra: plot
Requires-Dist: matplotlib==3.11.2; extra == "plot"

"""
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("scirel-0.1.0.dev9.dist-info/METADATA", metadata)

    with pytest.raises(ValueError, match="Requires-Dist differs"):
        _validate_wheel_metadata(tmp_path, wheel, source_revision=None)


def test_current_release_version_is_the_pyproject_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["version"] == project["project"]["version"]


def test_documentation_revision_can_advance_within_the_wheel_release_line() -> None:
    wheel = "0.1.0.dev9"
    for documentation in ("0.1.1", "0.1.0.post1", "0.1.0.dev10", "0.1.3+wording.1"):
        assert _validate_documentation_version(
            {"version": documentation}, wheel_version=wheel
        ) == documentation


def test_wheel_patch_evolution_keeps_documentation_on_the_same_release_line() -> None:
    assert _validate_documentation_version(
        {"version": "0.1.1", "release_line": "0.1"},
        wheel_version="0.1.0.dev10",
    ) == "0.1.1"


def test_documentation_revision_rejects_a_different_wheel_release_line() -> None:
    with pytest.raises(ValueError, match="release line differs"):
        _validate_documentation_version(
            {"version": "0.2.0"}, wheel_version="0.1.0.dev9"
        )
    with pytest.raises(ValueError, match="release line differs"):
        _validate_documentation_version(
            {"version": "1.1.0"}, wheel_version="0.1.0.dev9"
        )


def test_documentation_revision_uses_wheel_version_for_legacy_records() -> None:
    assert _validate_documentation_version({}, wheel_version="0.1.0.dev9") == "0.1.0.dev9"
    with pytest.raises(ValueError, match="valid PEP 440"):
        _validate_documentation_version(
            {"version": "release-next"}, wheel_version="0.1.0.dev9"
        )


def test_documentation_release_line_must_match_its_pep440_version() -> None:
    assert _validate_documentation_version(
        {"version": "0.1.1", "release_line": "0.1"},
        wheel_version="0.1.0.dev9",
    ) == "0.1.1"
    with pytest.raises(ValueError, match="documentation release_line"):
        _validate_documentation_version(
            {"version": "0.1.1", "release_line": "0.2"},
            wheel_version="0.1.0.dev9",
        )


def test_alignment_accepts_documentation_patch_revision_when_integration_binds_it(
    tmp_path: Path,
) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        shutil.copytree(source, target)
    for relative in ("pyproject.toml", "uv.lock"):
        (tmp_path / relative).write_bytes((ROOT / relative).read_bytes())
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["documentation"]["version"] = "0.1.1"
    current["documentation"]["release_line"] = "0.1"
    integration_path = tmp_path / current["documentation"]["integration_record"]
    integration = json.loads(integration_path.read_text(encoding="utf-8"))
    integration["documentation_version"] = "0.1.1"
    integration_path.write_text(json.dumps(integration), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")
    result = validate_alignment(tmp_path)
    assert result["documentation_version"] == "0.1.1"


def test_alignment_rejects_documentation_revision_on_a_different_release_line(
    tmp_path: Path,
) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    for relative in ("pyproject.toml", "uv.lock"):
        (tmp_path / relative).write_bytes((ROOT / relative).read_bytes())
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["documentation"]["version"] = "0.2.0"
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="release line differs"):
        validate_alignment(tmp_path)


def test_alignment_rejects_a_split_documentation_source_revision(tmp_path: Path) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    for relative in ("pyproject.toml", "uv.lock"):
        (tmp_path / relative).write_bytes((ROOT / relative).read_bytes())
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["documentation"]["source_revision"] = "a" * 40
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="documentation source revision must match"):
        validate_alignment(tmp_path)


def test_alignment_rejects_a_pyproject_version_drift(tmp_path: Path) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        project.replace('version = "0.1.0.dev9"', 'version = "0.1.0.dev10"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pyproject.toml project.version"):
        validate_alignment(tmp_path)


def test_alignment_can_require_an_exact_git_source_revision() -> None:
    with pytest.raises(ValueError, match="expected Git revision"):
        validate_alignment(ROOT, expected_source_revision="0" * 40)


def test_current_release_strict_gate_accepts_bound_rebuild() -> None:
    result = validate_alignment(ROOT, require_bound_candidate_match=True)
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert result["source_revision"] == current["source_revision"]


def test_legacy_current_files_are_thin_compatibility_pointers() -> None:
    for line in ("wheel", "docs"):
        path = ROOT / "release" / line / "CURRENT.json"
        pointer = json.loads(path.read_text())
        assert pointer["schema"] == "scirel.release-compat-pointer.v1"
        assert pointer["canonical"] == "../CURRENT.json"
        assert pointer["deprecated"] is True


def test_version_history_is_kept_in_git_and_short_release_notes() -> None:
    assert not list((ROOT / "release/wheel/versions").glob("*.json"))
    assert not list((ROOT / "release/docs/versions").glob("*.json"))
    assert (ROOT / "docs/release/0.1.0.dev8-notes.md").is_file()
    assert not list((ROOT / "tools/docs/handbooks").glob("*.json"))
    assert json.loads((ROOT / "release/CURRENT.json").read_text())["documentation"]["handbook"] == "tools/docs/handbook.json"


def test_alignment_rejects_a_document_added_outside_the_wheel(tmp_path: Path) -> None:
    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            import shutil

            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text())
    current["documentation"]["capability_counts"]["document_closure"] += 1
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="capability_counts"):
        validate_alignment(tmp_path)


def test_alignment_rejects_a_catalog_record_outside_the_selection(tmp_path: Path) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    extra = json.loads(
        (tmp_path / "catalog/examples/scirel.kinetic.fluidbw-case-state.json").read_text()
    )
    extra["asset_id"] = "scirel.test.catalog-only"
    (tmp_path / "catalog/examples/catalog-only.json").write_text(
        json.dumps(extra), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="catalog closure differs"):
        validate_alignment(tmp_path)


def test_alignment_rejects_a_built_catalog_from_a_different_source_revision(
    tmp_path: Path,
) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    catalog_root = tmp_path / "built-catalog"
    catalog_root.mkdir()
    (catalog_root / "release.json").write_text(
        json.dumps({
            "schema": "scirel.catalog-release.v1",
            "source_revision": "0" * 40,
        }),
        encoding="utf-8",
    )
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["documentation"]["catalog_root"] = "built-catalog"
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="documentation catalog source_revision"):
        validate_alignment(tmp_path)


def test_alignment_accepts_wrapped_platform_receipt_and_checks_source_revision(
    tmp_path: Path,
) -> None:
    import hashlib

    source_revision = "a" * 40
    artifact_sha = "b" * 64
    inner = {
        "schema": "scirel.installed-wheel-validation.v1",
        "status": "PASS",
        "package": {"version": "0.1.0.dev9"},
        "artifact": {"sha256": artifact_sha, "bytes": 123},
        "runtime": {"expected_platform": "linux-x86_64-cp314"},
    }
    receipt = {
        "schema": "scirel.dev9-linux-acceptance.v1",
        "status": "PASS",
        "source": {"revision": source_revision},
        "build": {
            "bound_candidate": {"sha256": artifact_sha, "bytes": 123},
            "byte_identical": True,
            "first_build": {"sha256": artifact_sha, "bytes": 123},
            "matches_bound_candidate": True,
            "second_build": {"sha256": artifact_sha, "bytes": 123},
        },
        "validation": inner,
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    wheel = {
        "version": "0.1.0.dev9",
        "artifact": {"sha256": artifact_sha, "bytes": 123},
        "platform_receipts": [
            {
                "platform": "linux-x86_64-cp314",
                "path": "receipt.json",
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        ],
    }

    _validate_platform_receipts(
        tmp_path, wheel, expected_source_revision=source_revision
    )
    _validate_platform_receipts(
        tmp_path,
        wheel,
        expected_source_revision=source_revision,
        require_bound_candidate_match=True,
    )
    with pytest.raises(ValueError, match="source revision differs"):
        _validate_platform_receipts(
            tmp_path, wheel, expected_source_revision="c" * 40
        )


def test_alignment_accepts_offline_wheelhouse_receipt_when_source_bound(
    tmp_path: Path,
) -> None:
    import hashlib

    source_revision = "a" * 40
    artifact_sha = "b" * 64
    receipt = {
        "schema": "scirel.offline-wheelhouse-validation.v1",
        "status": "PASS",
        "source_revision": source_revision,
        "execution": {
            "network_resolution": False,
            "pip_install": {"status": "PASS"},
        },
        "wheelhouse": {
            "wheels": [
                {
                    "filename": "certifi-2026.7.22-py3-none-any.whl",
                    "sha256": "d" * 64,
                    "bytes": 1,
                },
                {
                    "filename": "numpy-1.0.0-py3-none-any.whl",
                    "sha256": "c" * 64,
                    "bytes": 1,
                },
            ],
            "wheel_count": 2,
        },
        "dependency_closure": {
            "status": "PASS",
            "lockfile": {"path": "uv.lock", "sha256": "e" * 64},
            "requested_extras": [],
            "direct_requirements": ["numpy==1.0.0"],
            "expected_packages": [{"name": "numpy", "version": "1.0.0"}],
            "wheelhouse_packages": [
                {
                    "filename": "certifi-2026.7.22-py3-none-any.whl",
                    "sha256": "d" * 64,
                    "bytes": 1,
                    "name": "certifi",
                    "version": "2026.7.22",
                    "tags": ["py3-none-any"],
                    "platform_compatible": True,
                },
                {
                    "filename": "numpy-1.0.0-py3-none-any.whl",
                    "sha256": "c" * 64,
                    "bytes": 1,
                    "name": "numpy",
                    "version": "1.0.0",
                    "tags": ["py3-none-any"],
                    "platform_compatible": True,
                },
            ],
            "missing_packages": [],
            "version_mismatches": [],
            "duplicate_packages": [],
            "unknown_packages": [],
            "unneeded_packages": ["certifi"],
            "incompatible_wheels": [],
        },
        "validation": {
            "schema": "scirel.installed-wheel-validation.v1",
            "status": "PASS",
            "package": {"version": "0.1.0.dev9"},
            "artifact": {"sha256": artifact_sha, "bytes": 123},
            "runtime": {"expected_platform": "linux-x86_64-cp314"},
        },
    }
    receipt_path = tmp_path / "offline-receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    wheel = {
        "version": "0.1.0.dev9",
        "artifact": {"sha256": artifact_sha, "bytes": 123},
        "platform_receipts": [
            {
                "platform": "linux-x86_64-cp314",
                "path": receipt_path.name,
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        ],
    }

    _validate_platform_receipts(
        tmp_path, wheel, expected_source_revision=source_revision
    )

    tampered = json.loads(json.dumps(receipt))
    tampered["dependency_closure"]["wheelhouse_packages"][1]["name"] = "not-numpy"
    receipt_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="wheel identity is inconsistent"):
        _validate_platform_receipts(
            tmp_path,
            {
                **wheel,
                "platform_receipts": [
                    {
                        **wheel["platform_receipts"][0],
                        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    }
                ],
            },
            expected_source_revision=source_revision,
        )

    receipt = json.loads(json.dumps(receipt))
    receipt["execution"]["network_resolution"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="claims network resolution"):
        _validate_platform_receipts(
            tmp_path,
            {
                **wheel,
                "platform_receipts": [
                    {
                        **wheel["platform_receipts"][0],
                        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    }
                ],
            },
            expected_source_revision=source_revision,
        )


def test_strict_gate_distinguishes_reproducibility_from_bound_candidate_match(
    tmp_path: Path,
) -> None:
    import hashlib

    source_revision = "a" * 40
    bound_sha = "b" * 64
    rebuilt_sha = "c" * 64
    receipt = {
        "schema": "scirel.dev9-linux-acceptance.v1",
        "status": "PASS",
        "source": {"revision": source_revision},
        "build": {
            "bound_candidate": {"sha256": bound_sha, "bytes": 123},
            "byte_identical": True,
            "first_build": {"sha256": rebuilt_sha, "bytes": 123},
            "matches_bound_candidate": False,
            "second_build": {"sha256": rebuilt_sha, "bytes": 123},
        },
        "validation": {
            "schema": "scirel.installed-wheel-validation.v1",
            "status": "PASS",
            "package": {"version": "0.1.0.dev9"},
            "artifact": {"sha256": bound_sha, "bytes": 123},
            "runtime": {"expected_platform": "linux-x86_64-cp314"},
        },
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    wheel = {
        "version": "0.1.0.dev9",
        "artifact": {"sha256": bound_sha, "bytes": 123},
        "platform_receipts": [
            {
                "platform": "linux-x86_64-cp314",
                "path": "receipt.json",
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        ],
    }

    # Structural/history inspection can preserve the development candidate.
    _validate_platform_receipts(
        tmp_path, wheel, expected_source_revision=source_revision
    )
    # The formal release gate must reject the equally reproducible but
    # differently bound wheel.
    with pytest.raises(ValueError, match="rebuild does not match bound candidate"):
        _validate_platform_receipts(
            tmp_path,
            wheel,
            expected_source_revision=source_revision,
            require_bound_candidate_match=True,
        )
