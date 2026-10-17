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
    _validate_wheel_contents,
    _validate_source_revision,
    validate_alignment,
)  # noqa: E402


def test_current_release_alignment_is_exact() -> None:
    result = validate_alignment(ROOT)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert result["wheel_version"] == project["project"]["version"]
    assert result["documentation_selection"] == "scientific-core-current"
    assert result["source_revision"] == "5556f1aede8104b815a1595fda03167c0dadd135"
    assert result["capability_counts"] == {
        "operators": 230,
        "task_graphs": 30,
        "document_closure": 260,
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


def test_current_release_version_is_the_pyproject_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["version"] == project["project"]["version"]


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
    assert result["source_revision"] == "5556f1aede8104b815a1595fda03167c0dadd135"


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
            "wheels": [{"filename": "numpy.whl", "sha256": "c" * 64, "bytes": 1}]
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
