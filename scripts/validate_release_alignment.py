"""Validate the canonical current SciRel release tuple.

``release/CURRENT.json`` is the one mutable coordination record for the
checkout.  The old wheel and documentation ``CURRENT.json`` files are kept as
thin compatibility pointers; prior versions live in Git history and short
release notes rather than parallel metadata directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
from typing import Any
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA256_DIGEST = re.compile(r"[0-9a-f]{64}")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _project_version(root: Path) -> str:
    path = root / "pyproject.toml"
    try:
        metadata = tomllib.loads(path.read_text(encoding="utf-8"))
        version = metadata["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("pyproject.toml does not declare a readable project version") from error
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml project.version must be a non-empty string")
    return version


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(root: Path, value: str, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{field} escapes the repository: {value}")
    if not path.is_file():
        raise ValueError(f"{field} does not name a file: {value}")
    return path


def _external_ref(value: object, *, field: str) -> PurePosixPath:
    """Validate a logical POSIX key used below an external artifact root."""

    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty logical artifact reference")
    if "\\" in value or value.startswith("/"):
        raise ValueError(f"{field} must be a relative POSIX artifact reference")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} contains an unsafe artifact reference: {value}")
    return path


def _external_artifact_path(root: Path, value: object, *, field: str) -> Path:
    logical = _external_ref(value, field=field)
    root = root.expanduser().resolve()
    path = (root / Path(*logical.parts)).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{field} escapes the external artifact root")
    return path


def _validate_external_manifest_digest(path: Path, expected: object, *, field: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{field} does not name an external manifest: {path}")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError(f"{field} has an invalid manifest_sha256")
    if _sha256(path) != expected:
        raise ValueError(f"{field} manifest digest differs")
    manifest = _read_json(path)
    return manifest


def _git_blob_summary(root: Path, revision: str, relative: str) -> tuple[str, int] | None:
    """Return a Git blob digest and byte count when the source object resolves.

    External-artifact tests and archived receipts may intentionally use a
    synthetic revision without a Git checkout.  In that case shape validation
    still applies and content comparison is skipped; a real repository/ref is
    checked byte-for-byte.
    """

    try:
        result = subprocess.run(
            ["git", "cat-file", "blob", f"{revision}:{relative}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        return None
    if result.returncode:
        return None
    return hashlib.sha256(result.stdout).hexdigest(), len(result.stdout)


def _git_blob_bytes(root: Path, revision: str, relative: str) -> bytes | None:
    """Read a Git blob when the recorded source revision is available."""

    try:
        result = subprocess.run(
            ["git", "cat-file", "blob", f"{revision}:{relative}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        return None
    if result.returncode:
        return None
    return result.stdout


def _validate_wheel_contents(
    wheel_path: Path,
    contents: object,
    *,
    package_layout_members: set[str] | None = None,
) -> set[str]:
    """Check a ref-build's member digest index against the actual ZIP bytes."""

    if not isinstance(contents, dict) or contents.get("schema") != "scirel.wheel-contents.v1":
        raise ValueError("external wheel manifest has an invalid contents binding")
    rows = contents.get("members")
    package_members = contents.get("package_members")
    if not isinstance(rows, list) or not isinstance(package_members, list):
        raise ValueError("external wheel manifest contents are incomplete")
    expected: dict[str, tuple[str, int]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("external wheel manifest member summary is invalid")
        name = row.get("path")
        digest = row.get("sha256")
        size = row.get("bytes")
        if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
            raise ValueError("external wheel manifest member path is invalid")
        logical = PurePosixPath(name)
        if any(part in {"", ".", ".."} for part in logical.parts):
            raise ValueError(f"external wheel manifest member path is unsafe: {name}")
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            raise ValueError(f"external wheel manifest member digest is invalid: {name}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"external wheel manifest member byte count is invalid: {name}")
        if name in expected:
            raise ValueError(f"external wheel manifest repeats member: {name}")
        expected[name] = (digest, size)
    if len(package_members) != len(set(package_members)) or any(
        not isinstance(name, str) or name not in expected or not name.startswith("scirel/")
        for name in package_members
    ):
        raise ValueError("external wheel manifest package member list is invalid")
    expected_package = {name for name in expected if name.startswith("scirel/")}
    if set(package_members) != expected_package:
        raise ValueError("external wheel manifest package member list differs from members")
    if package_layout_members is not None and not package_layout_members <= expected_package:
        raise ValueError("external wheel manifest is missing package layout members")

    try:
        with zipfile.ZipFile(wheel_path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("external wheel repeats a member")
            actual: dict[str, tuple[str, int]] = {}
            for info in infos:
                if info.is_dir() or info.filename.endswith("/"):
                    raise ValueError(f"external wheel contains a directory member: {info.filename}")
                data = archive.read(info)
                actual[info.filename] = (hashlib.sha256(data).hexdigest(), len(data))
    except zipfile.BadZipFile as error:
        raise ValueError("external wheel is not a valid ZIP archive") from error
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        if missing:
            raise ValueError("external wheel is missing manifest members: " + ", ".join(missing))
        if extra:
            raise ValueError("external wheel has unbound members: " + ", ".join(extra))
        raise ValueError("external wheel member bytes differ from manifest")
    return expected_package


def _public_module_wheel_member(module: object, package_members: set[str]) -> str:
    if not isinstance(module, str) or not module or not module.startswith("scirel"):
        raise ValueError(f"source document public API module is invalid: {module!r}")
    module_path = module.replace(".", "/")
    direct = module_path + ".py"
    package = module_path + "/__init__.py"
    if direct in package_members:
        return direct
    if package in package_members:
        return package
    raise ValueError(f"source document public API module is absent from wheel: {module}")


def _validate_release_binding(
    root: Path,
    current: dict[str, Any],
    wheel_manifest: dict[str, Any],
    wheel_path: Path,
    *,
    source_revision: str | None,
) -> None:
    """Validate capability/layout/source bindings added after the dev9 build."""

    binding = wheel_manifest.get("release_binding")
    if binding is None:
        # Historical manifests, including the immutable dev9 artifact, use the
        # earlier build schema.  Their existing artifact and document checks
        # remain authoritative.
        return
    if not isinstance(binding, dict) or binding.get("schema") != "scirel.release-binding.v1":
        raise ValueError("external wheel manifest has an invalid release binding")
    source = binding.get("source")
    if not isinstance(source, dict):
        raise ValueError("external wheel release binding lacks source metadata")
    if source.get("revision") != source_revision or source.get("version") != current.get("version"):
        raise ValueError("external wheel release binding source differs from release CURRENT")

    files = binding.get("files")
    if not isinstance(files, dict):
        raise ValueError("external wheel release binding lacks source file summaries")
    for label, summary in files.items():
        if not isinstance(label, str) or not isinstance(summary, dict):
            raise ValueError("external wheel release binding file summary is invalid")
        relative = summary.get("path")
        digest = summary.get("sha256")
        size = summary.get("bytes")
        if not isinstance(relative, str) or not relative or "\\" in relative or relative.startswith("/"):
            raise ValueError(f"external wheel release binding path is invalid: {label}")
        path = PurePosixPath(relative)
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError(f"external wheel release binding path is unsafe: {relative}")
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            raise ValueError(f"external wheel release binding digest is invalid: {label}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"external wheel release binding byte count is invalid: {label}")
        if source_revision is not None:
            actual = _git_blob_summary(root, source_revision, relative)
            if actual is not None and actual != (digest, size):
                raise ValueError(f"external wheel release binding differs from source revision: {relative}")

    layout = binding.get("layout")
    selection = binding.get("selection")
    handbook = binding.get("handbook")
    integration = binding.get("integration")
    matrix = binding.get("platform_matrix")
    for label, value in (
        ("layout", layout),
        ("selection", selection),
        ("handbook", handbook),
        ("integration", integration),
        ("platform_matrix", matrix),
    ):
        if not isinstance(value, dict) or not isinstance(value.get("path"), str):
            raise ValueError(f"external wheel release binding {label} is invalid")
        file_summary = files.get(label)
        if not isinstance(file_summary, dict):
            raise ValueError(f"external wheel release binding lacks {label} file summary")
        if (
            value.get("path") != file_summary.get("path")
            or value.get("sha256") != file_summary.get("sha256")
        ):
            raise ValueError(f"external wheel release binding {label} digest differs from file summary")
    wheel = current.get("wheel")
    docs = current.get("documentation")
    if not isinstance(wheel, dict) or not isinstance(docs, dict):
        raise ValueError("release CURRENT lacks wheel/documentation objects")
    if layout["path"] != wheel.get("package_layout"):
        raise ValueError("external wheel layout path differs from release CURRENT")
    if selection["path"] != docs.get("source_documents"):
        raise ValueError("external wheel selection path differs from release CURRENT")
    if handbook["path"] != docs.get("handbook"):
        raise ValueError("external wheel handbook path differs from release CURRENT")
    if integration["path"] != docs.get("integration_record"):
        raise ValueError("external wheel integration path differs from release CURRENT")
    if matrix["path"] != "release/platform-support-matrix.json":
        raise ValueError("external wheel platform matrix path is invalid")
    if selection.get("sha256") != docs.get("selection_sha256"):
        raise ValueError("external wheel selection digest differs from release CURRENT")
    if handbook.get("sha256") != docs.get("handbook_sha256"):
        raise ValueError("external wheel handbook digest differs from release CURRENT")

    counts = selection.get("counts")
    if not isinstance(counts, dict) or counts != wheel.get("selected_capabilities") or counts != docs.get("capability_counts"):
        raise ValueError("external wheel capability counts differ from release CURRENT")
    capabilities = selection.get("capabilities")
    if not isinstance(capabilities, list) or len(capabilities) != counts.get("document_closure"):
        raise ValueError("external wheel capability closure count is invalid")
    seen_assets: set[str] = set()
    capability_members: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise ValueError("external wheel capability entry is invalid")
        asset_id = capability.get("asset_id")
        module = capability.get("module")
        symbol = capability.get("symbol")
        member = capability.get("wheel_member")
        kind = capability.get("kind")
        if (
            not isinstance(asset_id, str)
            or not asset_id
            or asset_id in seen_assets
            or not isinstance(module, str)
            or not isinstance(symbol, str)
            or not symbol
            or not isinstance(member, str)
            or not isinstance(kind, str)
        ):
            raise ValueError("external wheel capability entry has invalid identity")
        seen_assets.add(asset_id)
        capability_members.add(member)

    layout_members = layout.get("members")
    if not isinstance(layout_members, list) or len(layout_members) != len(set(layout_members)) or any(
        not isinstance(member, str) for member in layout_members
    ):
        raise ValueError("external wheel layout member list is invalid")
    package_members = _validate_wheel_contents(
        wheel_path,
        wheel_manifest.get("contents"),
        package_layout_members=set(layout_members),
    )
    wheel_members = binding.get("wheel_members")
    if not isinstance(wheel_members, list) or len(wheel_members) != len(set(wheel_members)):
        raise ValueError("external wheel release binding wheel member list is invalid")
    if set(wheel_members) != package_members:
        raise ValueError("external wheel release binding wheel members differ from contents")
    if not capability_members <= package_members:
        raise ValueError("external wheel capability closure points outside wheel package")
    if integration.get("selection_sha256") != selection.get("sha256"):
        raise ValueError("external wheel integration selection digest differs")
    if integration.get("handbook_sha256") != handbook.get("sha256"):
        raise ValueError("external wheel integration handbook digest differs")

    # Parse the source layout and matrix through Git when possible.  This is a
    # bidirectional check: the manifest points to source files, and those files
    # must describe the same package paths and platform identities.
    if source_revision is not None:
        selection_bytes = _git_blob_bytes(root, source_revision, selection["path"])
        if selection_bytes is not None:
            try:
                selection_record = json.loads(selection_bytes)
            except json.JSONDecodeError as error:
                raise ValueError("source selected document set is not valid JSON") from error
            if not isinstance(selection_record, dict) or selection_record.get("schema") != "scirel.selected-document-set.v1":
                raise ValueError("source selected document set has an invalid schema")
            source_rows = selection_record.get("records")
            if not isinstance(source_rows, list):
                raise ValueError("source selected document set records are invalid")
            expected_capabilities: list[dict[str, object]] = []
            expected_counts = {"operators": 0, "task_graphs": 0, "document_closure": len(source_rows)}
            for row in source_rows:
                if not isinstance(row, dict) or set(row) != {"asset_id", "path", "sha256"}:
                    raise ValueError("source selected document set contains an invalid row")
                asset_id = row.get("asset_id")
                document_path = row.get("path")
                expected_digest = row.get("sha256")
                if not isinstance(asset_id, str) or not isinstance(document_path, str):
                    raise ValueError("source selected document set identity is invalid")
                document_bytes = _git_blob_bytes(root, source_revision, document_path)
                if document_bytes is None:
                    raise ValueError(f"source selected document is missing: {document_path}")
                if not isinstance(expected_digest, str) or hashlib.sha256(document_bytes).hexdigest() != expected_digest:
                    raise ValueError(f"source selected document digest differs: {asset_id}")
                try:
                    document = json.loads(document_bytes)
                except json.JSONDecodeError as error:
                    raise ValueError(f"source selected document is not valid JSON: {asset_id}") from error
                if not isinstance(document, dict) or document.get("asset_id") != asset_id:
                    raise ValueError(f"source selected document asset_id differs: {asset_id}")
                kind = document.get("kind")
                if kind == "operator":
                    expected_counts["operators"] += 1
                elif kind == "task_graph":
                    expected_counts["task_graphs"] += 1
                else:
                    raise ValueError(f"source selected document kind is invalid: {asset_id}")
                implementation = document.get("version")
                if not isinstance(implementation, dict) or implementation.get("implementation_version") != current.get("version"):
                    raise ValueError(f"source selected document implementation version differs: {asset_id}")
                public_api = document.get("public_api")
                python_api = public_api.get("python") if isinstance(public_api, dict) else None
                if not isinstance(python_api, dict):
                    raise ValueError(f"source selected document lacks Python public API: {asset_id}")
                module = python_api.get("module")
                symbol = python_api.get("symbol")
                if not isinstance(symbol, str) or not symbol:
                    raise ValueError(f"source selected document symbol is invalid: {asset_id}")
                expected_capabilities.append(
                    {
                        "asset_id": asset_id,
                        "kind": kind,
                        "module": module,
                        "symbol": symbol,
                        "wheel_member": _public_module_wheel_member(module, package_members),
                    }
                )
            if selection.get("capabilities") != expected_capabilities:
                raise ValueError("external wheel capability closure differs from source selection")
            if selection.get("counts") != expected_counts:
                raise ValueError("external wheel capability counts differ from source selection")

        layout_bytes = _git_blob_bytes(root, source_revision, layout["path"])
        if layout_bytes is not None:
            try:
                layout_record = json.loads(layout_bytes)
            except json.JSONDecodeError as error:
                raise ValueError("source wheel layout is not valid JSON") from error
            if not isinstance(layout_record, dict) or layout_record.get("schema") != "scirel.wheel-layout.v1":
                raise ValueError("source wheel layout has an invalid schema")
            expected_layout = {
                f"scirel/{domain}/__init__.py"
                for domain in layout_record.get("domain_packages", [])
                if isinstance(domain, str)
            }
            organized = layout_record.get("organized_general_primitives", {})
            if isinstance(organized, dict):
                for domain, modules in organized.items():
                    if isinstance(domain, str) and isinstance(modules, list):
                        expected_layout.update(
                            f"scirel/{domain}/{module}.py"
                            for module in modules
                            if isinstance(module, str)
                        )
            if set(layout_members) != expected_layout:
                raise ValueError("external wheel layout members differ from source layout")
            if not expected_layout <= package_members:
                raise ValueError("external wheel is missing source layout members")

        matrix_bytes = _git_blob_bytes(root, source_revision, matrix["path"])
        if matrix_bytes is not None:
            try:
                matrix_record = json.loads(matrix_bytes)
            except json.JSONDecodeError as error:
                raise ValueError("source platform matrix is not valid JSON") from error
            if not isinstance(matrix_record, dict) or matrix_record.get("schema") != "scirel.platform-support-matrix.v1":
                raise ValueError("source platform matrix has an invalid schema")
            source_ids = sorted(
                row["id"] for row in matrix_record.get("platforms", [])
                if isinstance(row, dict) and isinstance(row.get("id"), str)
            )
            if matrix.get("platform_ids") != source_ids:
                raise ValueError("external wheel platform matrix differs from source")

        integration_bytes = _git_blob_bytes(root, source_revision, integration["path"])
        if integration_bytes is not None:
            try:
                integration_record = json.loads(integration_bytes)
            except json.JSONDecodeError as error:
                raise ValueError("source document integration record is not valid JSON") from error
            if not isinstance(integration_record, dict):
                raise ValueError("source document integration record is invalid")
            if integration_record.get("project_version") != current.get("version"):
                raise ValueError("source document integration record version differs")
            record_selection = integration_record.get("selection")
            record_handbook = integration_record.get("handbook")
            if (
                not isinstance(record_selection, dict)
                or record_selection.get("path") != selection["path"]
                or record_selection.get("sha256") != selection["sha256"]
                or not isinstance(record_handbook, dict)
                or record_handbook.get("path") != handbook["path"]
                or record_handbook.get("sha256") != handbook["sha256"]
            ):
                raise ValueError("external wheel integration binding differs from source record")


def _validate_build_inputs(
    root: Path,
    manifest: dict[str, Any],
    *,
    source_revision: str | None,
    field: str,
) -> None:
    """Validate additive source/helper input metadata in a build manifest.

    ``inputs`` was added after the first ``scirel.git-*.-v1`` manifests were
    issued, so its absence remains valid for historical ``CURRENT`` records.
    When present, the metadata is checked structurally and, if the source ref
    is available in the checkout, against Git blob bytes.
    """

    inputs = manifest.get("inputs")
    if inputs is None:
        return
    if not isinstance(inputs, dict) or inputs.get("schema") != "scirel.build-inputs.v1":
        raise ValueError(f"external {field} manifest has invalid inputs schema")
    files = inputs.get("files")
    if not isinstance(files, dict) or "pyproject.toml" not in files:
        raise ValueError(f"external {field} manifest inputs lack pyproject.toml")
    for relative, summary in files.items():
        if not isinstance(relative, str) or not relative or "\\" in relative:
            raise ValueError(f"external {field} manifest has an unsafe input path")
        logical = PurePosixPath(relative)
        if logical.is_absolute() or any(part in {"", ".", ".."} for part in logical.parts):
            raise ValueError(f"external {field} manifest has an unsafe input path: {relative}")
        if not isinstance(summary, dict):
            raise ValueError(f"external {field} manifest input summary is invalid: {relative}")
        digest = summary.get("sha256")
        size = summary.get("bytes")
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            raise ValueError(f"external {field} manifest input digest is invalid: {relative}")
        if not isinstance(size, int) or size < 0:
            raise ValueError(f"external {field} manifest input byte count is invalid: {relative}")
        if source_revision is not None:
            actual = _git_blob_summary(root, source_revision, relative)
            if actual is not None and actual != (digest, size):
                raise ValueError(f"external {field} manifest input differs from source revision: {relative}")

    license_files = inputs.get("license_files")
    if not isinstance(license_files, list) or any(
        not isinstance(path, str) or path not in files for path in license_files
    ):
        raise ValueError(f"external {field} manifest license input list is invalid")
    if len(set(license_files)) != len(license_files):
        raise ValueError(f"external {field} manifest license input list repeats a path")

    helper = inputs.get("helper")
    if not isinstance(helper, dict):
        raise ValueError(f"external {field} manifest lacks helper input binding")
    helper_revision = helper.get("revision")
    if helper_revision is not None and (
        not isinstance(helper_revision, str) or re.fullmatch(r"[0-9a-f]{40}", helper_revision) is None
    ):
        raise ValueError(f"external {field} manifest helper revision is invalid")
    if not isinstance(helper.get("dirty"), bool):
        raise ValueError(f"external {field} manifest helper dirty flag is invalid")
    helper_files = helper.get("files")
    if not isinstance(helper_files, dict) or not helper_files:
        raise ValueError(f"external {field} manifest helper files are missing")
    for relative, summary in helper_files.items():
        if not isinstance(relative, str) or not relative.startswith("scripts/"):
            raise ValueError(f"external {field} manifest helper path is invalid: {relative}")
        logical = PurePosixPath(relative)
        if logical.is_absolute() or any(part in {"", ".", ".."} for part in logical.parts):
            raise ValueError(f"external {field} manifest helper path is unsafe: {relative}")
        if not isinstance(summary, dict):
            raise ValueError(f"external {field} manifest helper summary is invalid: {relative}")
        digest = summary.get("sha256")
        size = summary.get("bytes")
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            raise ValueError(f"external {field} manifest helper digest is invalid: {relative}")
        if not isinstance(size, int) or size < 0:
            raise ValueError(f"external {field} manifest helper byte count is invalid: {relative}")
        if helper_revision is not None and not helper.get("dirty"):
            actual = _git_blob_summary(root, helper_revision, relative)
            if actual is not None and actual != (digest, size):
                raise ValueError(f"external {field} manifest helper differs from helper revision: {relative}")


def _validate_source_revision(root: Path, revision: object, version: str) -> None:
    """Check a bound source revision when ``root`` is a Git checkout.

    Copied fixture roots used by structural tests have no ``.git`` directory;
    those roots still receive all file-level checks and leave this optional
    repository-object check unclaimed.  A real checkout must resolve the
    exact commit and expose a matching ``pyproject.toml`` at that commit.
    """

    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("source_revision must be an exact 40-character Git SHA")
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return
    if result.returncode:
        # A copied source fixture is not a checkout.  A path that does contain
        # Git metadata must fail closed when its recorded object is missing.
        git_marker = root / ".git"
        if git_marker.exists():
            raise ValueError("source_revision does not resolve to a Git commit")
        return
    resolved = result.stdout.strip()
    if resolved != revision:
        raise ValueError("source_revision does not resolve to the recorded Git commit")
    try:
        pyproject = subprocess.run(
            ["git", "show", f"{revision}:pyproject.toml"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        metadata = tomllib.loads(pyproject)
        source_version = metadata["project"]["version"]
    except (OSError, subprocess.CalledProcessError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("source_revision has no readable pyproject.toml") from error
    if source_version != version:
        raise ValueError("source_revision pyproject.toml version differs from release CURRENT")


def _validate_external_artifacts(
    root: Path,
    current: dict[str, Any],
    *,
    version: str,
    source_revision: str | None,
    artifact_root: Path | None,
) -> str:
    """Validate external wheel/docs manifests when an artifact root is supplied.

    The repository deliberately cannot prove external bytes without a storage
    root.  In that mode this function still validates the logical reference
    shape and returns ``external_artifact_unchecked``; release gates must pass
    ``--artifact-root`` to obtain byte-level proof.
    """

    wheel = current["wheel"]
    docs = current["documentation"]
    wheel_artifact = wheel.get("artifact")
    docs_artifact = docs.get("artifact")
    if not isinstance(wheel_artifact, dict) or not isinstance(docs_artifact, dict):
        raise ValueError("release CURRENT v2 requires wheel and documentation artifact objects")

    wheel_manifest_ref = _external_ref(
        wheel_artifact.get("manifest_ref"), field="wheel artifact manifest_ref"
    )
    docs_manifest_ref = _external_ref(
        docs_artifact.get("manifest_ref"), field="documentation artifact manifest_ref"
    )
    filename_ref = _external_ref(
        wheel_artifact.get("filename"), field="wheel artifact filename"
    )
    if len(filename_ref.parts) != 1:
        raise ValueError("wheel artifact filename must be a single file name")
    _external_ref(
        docs_artifact.get("snapshot_ref"), field="documentation artifact snapshot_ref"
    )
    for field, value in (
        ("wheel artifact manifest_sha256", wheel_artifact.get("manifest_sha256")),
        ("documentation artifact manifest_sha256", docs_artifact.get("manifest_sha256")),
        ("wheel artifact sha256", wheel_artifact.get("sha256")),
        ("documentation artifact snapshot_sha256", docs_artifact.get("snapshot_sha256")),
    ):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"{field} is invalid")
    for field, value in (
        ("wheel artifact bytes", wheel_artifact.get("bytes")),
        ("documentation artifact snapshot_bytes", docs_artifact.get("snapshot_bytes")),
    ):
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} is invalid")

    if artifact_root is None:
        return "external_artifact_unchecked"

    wheel_manifest_path = _external_artifact_path(
        artifact_root, wheel_manifest_ref.as_posix(), field="wheel artifact manifest_ref"
    )
    docs_manifest_path = _external_artifact_path(
        artifact_root, docs_manifest_ref.as_posix(), field="documentation artifact manifest_ref"
    )
    wheel_manifest = _validate_external_manifest_digest(
        wheel_manifest_path,
        wheel_artifact.get("manifest_sha256"),
        field="wheel artifact",
    )
    docs_manifest = _validate_external_manifest_digest(
        docs_manifest_path,
        docs_artifact.get("manifest_sha256"),
        field="documentation artifact",
    )

    if wheel_manifest.get("schema") != "scirel.git-build.v1":
        raise ValueError("external wheel manifest has an invalid schema")
    if docs_manifest.get("schema") != "scirel.git-docs-build.v1":
        raise ValueError("external documentation manifest has an invalid schema")
    for label, manifest in (("wheel", wheel_manifest), ("documentation", docs_manifest)):
        source = manifest.get("source")
        project = manifest.get("project")
        if not isinstance(source, dict) or not isinstance(project, dict):
            raise ValueError(f"external {label} manifest lacks source/project binding")
        if project.get("name") != "scirel" or project.get("version") != version:
            raise ValueError(f"external {label} manifest project differs from release CURRENT")
        if source_revision is not None and source.get("revision") != source_revision:
            raise ValueError(f"external {label} manifest source revision differs")
        _validate_build_inputs(
            root,
            manifest,
            source_revision=source_revision,
            field=label,
        )

    wheel_info = wheel_manifest.get("wheel")
    if not isinstance(wheel_info, dict):
        raise ValueError("external wheel manifest lacks wheel metadata")
    if {
        "filename": wheel_info.get("filename"),
        "sha256": wheel_info.get("sha256"),
        "bytes": wheel_info.get("bytes"),
    } != {
        "filename": wheel_artifact["filename"],
        "sha256": wheel_artifact["sha256"],
        "bytes": wheel_artifact["bytes"],
    }:
        raise ValueError("external wheel manifest artifact differs from release CURRENT")
    wheel_path = wheel_manifest_path.parent / filename_ref.name
    if not wheel_path.is_file() or wheel_path.is_symlink():
        raise ValueError("external wheel filename does not resolve beside its manifest")
    if _sha256(wheel_path) != wheel_artifact["sha256"] or wheel_path.stat().st_size != wheel_artifact["bytes"]:
        raise ValueError("external wheel bytes differ from release CURRENT")
    _validate_release_binding(
        root,
        current,
        wheel_manifest,
        wheel_path,
        source_revision=source_revision,
    )

    snapshot_info = docs_manifest.get("snapshot")
    selection_info = docs_manifest.get("selection")
    if not isinstance(snapshot_info, dict) or not isinstance(selection_info, dict):
        raise ValueError("external documentation manifest lacks snapshot/selection metadata")
    if {
        "sha256": snapshot_info.get("sha256"),
        "bytes": snapshot_info.get("bytes"),
    } != {
        "sha256": docs_artifact["snapshot_sha256"],
        "bytes": docs_artifact["snapshot_bytes"],
    }:
        raise ValueError("external documentation snapshot differs from release CURRENT")
    if docs.get("snapshot_sha256") != snapshot_info.get("sha256"):
        raise ValueError("documentation snapshot_sha256 differs from external manifest")
    if selection_info.get("sha256") != docs.get("selection_sha256"):
        raise ValueError("external documentation selection differs from release CURRENT")
    snapshot_ref = _external_ref(
        docs_artifact["snapshot_ref"], field="documentation artifact snapshot_ref"
    )
    manifest_snapshot_ref = _external_ref(
        snapshot_info.get("path"), field="external documentation snapshot.path"
    )
    if snapshot_ref != manifest_snapshot_ref:
        raise ValueError("documentation snapshot_ref differs from external manifest")
    snapshot_path = _external_artifact_path(
        docs_manifest_path.parent,
        manifest_snapshot_ref.as_posix(),
        field="external documentation snapshot.path",
    )
    if not snapshot_path.is_dir() or snapshot_path.is_symlink():
        raise ValueError("external documentation snapshot path is not a directory")
    snapshot_manifest_path = snapshot_path / "manifest.json"
    if not snapshot_manifest_path.is_file() or snapshot_manifest_path.is_symlink():
        raise ValueError("external documentation snapshot has no manifest.json")
    snapshot_manifest = _read_json(snapshot_manifest_path)
    if snapshot_manifest.get("schema") != "scirel.documentation-snapshot.v1":
        raise ValueError("external documentation snapshot has an invalid schema")
    unsigned = {key: value for key, value in snapshot_manifest.items() if key != "snapshot_sha256"}
    encoded = (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if hashlib.sha256(encoded).hexdigest() != snapshot_manifest.get("snapshot_sha256"):
        raise ValueError("external documentation snapshot manifest digest differs")
    if snapshot_manifest.get("snapshot_sha256") != snapshot_info.get("sha256"):
        raise ValueError("external documentation snapshot digest differs")
    if snapshot_manifest.get("source_revision") != source_revision:
        raise ValueError("external documentation snapshot source revision differs")
    if snapshot_manifest.get("project_version") != version:
        raise ValueError("external documentation snapshot project version differs")
    files = snapshot_manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("external documentation snapshot files index is invalid")
    actual_files: dict[str, Path] = {}
    for path in snapshot_path.rglob("*"):
        if path == snapshot_manifest_path:
            continue
        if path.is_symlink():
            raise ValueError("external documentation snapshot contains a non-regular file")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("external documentation snapshot contains a non-regular file")
        relative = path.relative_to(snapshot_path).as_posix()
        actual_files[relative] = path
    if set(files) != set(actual_files):
        raise ValueError("external documentation snapshot file set differs from its manifest")
    for relative, metadata in files.items():
        if not isinstance(metadata, dict):
            raise ValueError("external documentation snapshot file metadata is invalid")
        path = actual_files[relative]
        if (
            metadata.get("bytes") != path.stat().st_size
            or metadata.get("sha256") != _sha256(path)
        ):
            raise ValueError(f"external documentation snapshot file differs: {relative}")
    total_bytes = snapshot_manifest_path.stat().st_size + sum(
        path.stat().st_size for path in actual_files.values()
    )
    if total_bytes != docs_artifact["snapshot_bytes"]:
        raise ValueError("external documentation snapshot byte size differs")
    return "external_artifact_verified"


def _selected_documents(root: Path, record: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    selection_path = _repo_path(root, record["source_documents"], field="source_documents")
    selection_digest = _sha256(selection_path)
    selection = _read_json(selection_path)
    if selection.get("schema") != "scirel.selected-document-set.v1":
        raise ValueError("source document selection has an invalid schema")
    rows = selection.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("source document selection is empty")
    documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"asset_id", "path", "sha256"}:
            raise ValueError("source document selection contains an invalid row")
        asset_id = row["asset_id"]
        document_path = _repo_path(root, row["path"], field=f"document[{asset_id}]")
        if _sha256(document_path) != row["sha256"]:
            raise ValueError(f"document digest differs from selection: {asset_id}")
        document = _read_json(document_path)
        if document.get("asset_id") != asset_id:
            raise ValueError(f"document asset ID differs from selection: {asset_id}")
        if asset_id in documents:
            raise ValueError(f"source document selection repeats {asset_id}")
        documents[asset_id] = document
    return documents, selection_digest


def _handbook_assets(root: Path, record: dict[str, Any]) -> tuple[set[str], str]:
    handbook_path = _repo_path(root, record["handbook"], field="handbook")
    handbook = _read_json(handbook_path)
    if handbook.get("schema") != "scirel.handbook.v1":
        raise ValueError("handbook has an invalid schema")
    assets: list[str] = []
    for chapter in handbook.get("chapters", []):
        for topic in chapter.get("topics", []):
            topic_assets = topic.get("assets")
            if not isinstance(topic_assets, list) or not topic_assets:
                raise ValueError("handbook contains an empty topic")
            assets.extend(topic_assets)
    if len(assets) != len(set(assets)):
        raise ValueError("handbook repeats an asset")
    return set(assets), _sha256(handbook_path)


def _validate_catalog_source_revision(
    root: Path, record: dict[str, Any], expected_source_revision: str | None
) -> None:
    """Check a built catalog when the current tuple points at one.

    Development CURRENT records may point at ``catalog/examples`` rather than a
    built ``release.json``. In that case there is no catalog release tuple to
    compare and the existing document selection checks remain authoritative.
    """
    catalog_value = record.get("catalog_root")
    if not isinstance(catalog_value, str) or not catalog_value:
        return
    catalog_root = (root / catalog_value).resolve()
    if not catalog_root.is_relative_to(root.resolve()):
        raise ValueError("documentation catalog_root escapes the repository")
    release_path = catalog_root / "release.json"
    if not release_path.is_file():
        return
    release = _read_json(release_path)
    if release.get("schema") != "scirel.catalog-release.v1":
        raise ValueError("documentation catalog release has an invalid schema")
    catalog_revision = release.get("source_revision")
    if not isinstance(catalog_revision, str) or re.fullmatch(r"[0-9a-f]{40}", catalog_revision) is None:
        raise ValueError("documentation catalog release lacks an exact source_revision")
    required_revision = expected_source_revision
    if required_revision is None:
        required_revision = record.get("source_revision")
    if required_revision is not None and catalog_revision != required_revision:
        raise ValueError("documentation catalog source_revision differs from release CURRENT")


def _validate_compat_pointer(root: Path, path: Path, *, line: str) -> None:
    pointer = _read_json(path)
    if pointer.get("schema") != "scirel.release-compat-pointer.v1":
        raise ValueError(f"{line} CURRENT is not a compatibility pointer")
    if pointer.get("line") != line or pointer.get("canonical") != "../CURRENT.json":
        raise ValueError(f"{line} CURRENT points somewhere other than release/CURRENT.json")
    target = (path.parent / pointer["canonical"]).resolve()
    if target != (root / "release/CURRENT.json").resolve():
        raise ValueError(f"{line} CURRENT canonical target is invalid")


def _validate_platform_receipts(
    root: Path,
    wheel: dict[str, Any],
    *,
    expected_source_revision: str | None = None,
    require_bound_candidate_match: bool = False,
) -> None:
    receipts = wheel.get("platform_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("wheel platform_receipts must be a non-empty list")
    for row in receipts:
        if not isinstance(row, dict) or set(row) != {"platform", "path", "sha256"}:
            raise ValueError("wheel platform receipt has an invalid shape")
        receipt_path = _repo_path(root, row["path"], field="wheel platform receipt")
        if _sha256(receipt_path) != row["sha256"]:
            raise ValueError(f"platform receipt digest differs: {row['platform']}")
        receipt = _read_json(receipt_path)
        schema = receipt.get("schema")
        if schema == "scirel.installed-wheel-validation.v1":
            bound = receipt
            receipt_source_revision = receipt.get("source_revision")
        elif schema == "scirel.dev9-linux-acceptance.v1":
            # The platform runner wraps the installed-wheel validator with
            # reproducible-build and source-archive evidence.  Keep the inner
            # validator as the runtime contract while checking the outer source
            # binding and status here.
            if receipt.get("status") != "PASS":
                raise ValueError(f"platform receipt is not PASS: {row['platform']}")
            source = receipt.get("source")
            validation = receipt.get("validation")
            if not isinstance(source, dict) or not isinstance(validation, dict):
                raise ValueError(f"platform receipt lacks wrapped validation: {row['platform']}")
            receipt_source_revision = source.get("revision")
            if validation.get("schema") != "scirel.installed-wheel-validation.v1":
                raise ValueError(f"platform receipt inner schema is invalid: {row['platform']}")
            bound = validation
        elif schema == "scirel.offline-wheelhouse-validation.v1":
            # Offline wheelhouse receipts are accepted only when the runner
            # proves that no index/network resolution was used and the inner
            # installed-wheel validator passed.  ``source_revision`` is
            # optional at generation time, but the common binding check below
            # requires it whenever CURRENT carries a source revision.
            if receipt.get("status") != "PASS":
                raise ValueError(f"platform receipt is not PASS: {row['platform']}")
            validation = receipt.get("validation")
            execution = receipt.get("execution")
            wheelhouse = receipt.get("wheelhouse")
            if not isinstance(validation, dict) or not isinstance(execution, dict):
                raise ValueError(
                    f"offline platform receipt lacks wrapped validation: {row['platform']}"
                )
            if validation.get("schema") != "scirel.installed-wheel-validation.v1":
                raise ValueError(f"offline platform receipt inner schema is invalid: {row['platform']}")
            if execution.get("network_resolution") is not False:
                raise ValueError(f"offline platform receipt claims network resolution: {row['platform']}")
            pip_install = execution.get("pip_install")
            if not isinstance(pip_install, dict) or pip_install.get("status") != "PASS":
                raise ValueError(f"offline platform receipt pip install is not PASS: {row['platform']}")
            if (
                not isinstance(wheelhouse, dict)
                or not isinstance(wheelhouse.get("wheels"), list)
                or not wheelhouse["wheels"]
            ):
                raise ValueError(
                    f"offline platform receipt lacks wheelhouse inventory: {row['platform']}"
                )
            for wheelhouse_row in wheelhouse["wheels"]:
                if not isinstance(wheelhouse_row, dict) or set(wheelhouse_row) != {
                    "filename",
                    "sha256",
                    "bytes",
                }:
                    raise ValueError(
                        f"offline platform receipt has an invalid wheelhouse row: {row['platform']}"
                    )
                if (
                    not isinstance(wheelhouse_row["filename"], str)
                    or not wheelhouse_row["filename"].endswith(".whl")
                    or Path(wheelhouse_row["filename"]).name != wheelhouse_row["filename"]
                    or not isinstance(wheelhouse_row["sha256"], str)
                    or _SHA256_DIGEST.fullmatch(wheelhouse_row["sha256"]) is None
                    or not isinstance(wheelhouse_row["bytes"], int)
                    or isinstance(wheelhouse_row["bytes"], bool)
                    or wheelhouse_row["bytes"] < 0
                ):
                    raise ValueError(
                        f"offline platform receipt has an invalid wheelhouse identity: {row['platform']}"
                    )
            if validation.get("status") != "PASS":
                raise ValueError(f"offline platform inner validation is not PASS: {row['platform']}")
            receipt_source_revision = receipt.get("source_revision")
            if (
                not isinstance(receipt_source_revision, str)
                or _COMMIT.fullmatch(receipt_source_revision) is None
            ):
                raise ValueError(
                    f"offline platform receipt lacks an exact source revision: {row['platform']}"
                )
            bound = validation
        else:
            raise ValueError(f"platform receipt has an invalid schema: {row['platform']}")
        if receipt.get("status") != "PASS" and schema == "scirel.installed-wheel-validation.v1":
            raise ValueError(f"platform receipt is not PASS: {row['platform']}")
        if expected_source_revision is not None:
            if (
                not isinstance(receipt_source_revision, str)
                or len(receipt_source_revision) != 40
            ):
                raise ValueError(
                    f"platform receipt lacks source revision: {row['platform']}"
                )
            if receipt_source_revision != expected_source_revision:
                raise ValueError(f"platform receipt source revision differs: {row['platform']}")
        package = bound.get("package")
        if not isinstance(package, dict) or package.get("version") != wheel["version"]:
            raise ValueError(f"platform receipt package version differs: {row['platform']}")
        receipt_artifact = bound.get("artifact")
        expected_artifact = wheel.get("artifact")
        if (
            not isinstance(receipt_artifact, dict)
            or receipt_artifact.get("sha256") != expected_artifact.get("sha256")
            or receipt_artifact.get("bytes") != expected_artifact.get("bytes")
        ):
            raise ValueError(f"platform receipt wheel artifact differs: {row['platform']}")
        runtime = bound.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("expected_platform") != row["platform"]:
            raise ValueError(f"platform receipt target differs: {row['platform']}")
        _validate_reproducible_build_evidence(
            receipt.get("build"),
            expected_artifact,
            platform=row["platform"],
            require_bound_candidate_match=require_bound_candidate_match,
        )


def _validate_reproducible_build_evidence(
    build: object,
    expected_artifact: object,
    *,
    platform: str,
    require_bound_candidate_match: bool,
) -> None:
    """Validate optional rebuild evidence attached to a platform receipt.

    ``byte_identical`` only establishes that the two fresh builds agree with
    each other.  ``matches_bound_candidate`` establishes the separate link to
    the wheel selected by ``release/CURRENT.json``.  A strict release gate
    requires both claims and recomputes them from the recorded digests instead
    of trusting either boolean in isolation.
    """

    if build is None:
        if require_bound_candidate_match:
            raise ValueError(
                f"platform receipt lacks reproducible build evidence: {platform}"
            )
        return
    if not isinstance(build, dict):
        raise ValueError(f"platform receipt build evidence is invalid: {platform}")

    expected = expected_artifact
    if not isinstance(expected, dict):
        raise ValueError(f"release wheel artifact is invalid: {platform}")
    expected_sha = expected.get("sha256")
    expected_bytes = expected.get("bytes")
    if not isinstance(expected_sha, str) or _SHA256_DIGEST.fullmatch(expected_sha) is None:
        raise ValueError(f"release wheel artifact digest is invalid: {platform}")
    if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool) or expected_bytes < 0:
        raise ValueError(f"release wheel artifact byte count is invalid: {platform}")
    expected_pair = {"sha256": expected_sha, "bytes": expected_bytes}

    def _build_pair(field: str) -> dict[str, Any]:
        value = build.get(field)
        if not isinstance(value, dict):
            raise ValueError(f"platform receipt build.{field} is missing: {platform}")
        digest = value.get("sha256")
        size = value.get("bytes")
        if not isinstance(digest, str) or _SHA256_DIGEST.fullmatch(digest) is None:
            raise ValueError(f"platform receipt build.{field}.sha256 is invalid: {platform}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"platform receipt build.{field}.bytes is invalid: {platform}")
        return {"sha256": digest, "bytes": size}

    has_build_pair = "first_build" in build or "second_build" in build
    has_bound_pair = "bound_candidate" in build
    if not has_build_pair and not has_bound_pair:
        if require_bound_candidate_match:
            raise ValueError(
                f"platform receipt lacks first/second build evidence: {platform}"
            )
        return

    first = _build_pair("first_build")
    second = _build_pair("second_build")
    byte_identical = build.get("byte_identical")
    if not isinstance(byte_identical, bool):
        raise ValueError(f"platform receipt byte_identical is invalid: {platform}")
    computed_byte_identical = first == second
    if byte_identical != computed_byte_identical:
        raise ValueError(
            f"platform receipt byte_identical disagrees with build digests: {platform}"
        )

    if has_bound_pair:
        bound_candidate = _build_pair("bound_candidate")
        if bound_candidate != expected_pair:
            raise ValueError(
                f"platform receipt bound_candidate differs from release wheel: {platform}"
            )
        matches_bound_candidate = build.get("matches_bound_candidate")
        if not isinstance(matches_bound_candidate, bool):
            raise ValueError(
                f"platform receipt matches_bound_candidate is invalid: {platform}"
            )
        computed_match = first == bound_candidate
        if matches_bound_candidate != computed_match:
            raise ValueError(
                "platform receipt matches_bound_candidate disagrees with build digests: "
                f"{platform}"
            )
    elif require_bound_candidate_match:
        raise ValueError(
            f"platform receipt lacks bound_candidate evidence: {platform}"
        )

    if require_bound_candidate_match:
        if byte_identical is not True:
            raise ValueError(
                f"platform receipt builds are not byte-identical: {platform}"
            )
        if build.get("matches_bound_candidate") is not True:
            raise ValueError(
                f"platform receipt rebuild does not match bound candidate: {platform}"
            )


def _validate_document_integration(
    root: Path,
    docs: dict[str, Any],
    *,
    version: str,
    source_revision: str | None,
    wheel: dict[str, Any],
    selection_digest: str,
    handbook_digest: str,
) -> None:
    record_value = docs.get("integration_record")
    record_path = _repo_path(root, record_value, field="integration_record")
    record = _read_json(record_path)
    if record.get("status") != "PASS":
        raise ValueError("documentation integration record is not PASS")
    if record.get("project_version") != version:
        raise ValueError("documentation integration record version differs")
    if source_revision is not None and record.get("source_revision") != source_revision:
        raise ValueError("documentation integration source revision differs")

    record_wheel = record.get("wheel")
    artifact = wheel.get("artifact")
    if (
        not isinstance(record_wheel, dict)
        or record_wheel.get("sha256") != artifact.get("sha256")
        or record_wheel.get("bytes") != artifact.get("bytes")
    ):
        raise ValueError("documentation integration wheel artifact differs")

    record_selection = record.get("selection")
    if (
        not isinstance(record_selection, dict)
        or record_selection.get("path") != docs.get("source_documents")
        or record_selection.get("sha256") != selection_digest
    ):
        raise ValueError("documentation integration selection differs")
    record_handbook = record.get("handbook")
    if (
        not isinstance(record_handbook, dict)
        or record_handbook.get("path") != docs.get("handbook")
        or record_handbook.get("sha256") != handbook_digest
    ):
        raise ValueError("documentation integration handbook differs")
    if record_handbook.get("scope", "exact") != docs.get("handbook_scope", "exact"):
        raise ValueError("documentation integration handbook scope differs")
    snapshot = record.get("snapshot")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("sha256") != docs.get("snapshot_sha256")
    ):
        raise ValueError("documentation integration snapshot differs")


def _validate_platform_matrix(root: Path, *, version: str, receipt_paths: set[str]) -> None:
    matrix = _read_json(root / "release/platform-support-matrix.json")
    if matrix.get("schema") != "scirel.platform-support-matrix.v1":
        raise ValueError("platform support matrix has an invalid schema")
    if matrix.get("package") != "scirel":
        raise ValueError("platform support matrix names an unexpected package")
    if matrix.get("package_version") != version:
        raise ValueError("platform support matrix version differs from current release")
    binding = matrix.get("runtime_binding")
    if not isinstance(binding, dict) or binding.get("release_tuple") != "release/CURRENT.json":
        raise ValueError("platform support matrix is not bound to release/CURRENT.json")
    if binding.get("dependency_lock") != "uv.lock" or not (root / "uv.lock").is_file():
        raise ValueError("platform support matrix dependency lock is invalid")
    rows = matrix.get("platforms")
    if not isinstance(rows, list):
        raise ValueError("platform support matrix platforms must be a list")
    evidence_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("evidence"), list):
            raise ValueError("platform support matrix contains an invalid evidence row")
        evidence_paths.update(value for value in row["evidence"] if isinstance(value, str))
    if not receipt_paths <= evidence_paths:
        raise ValueError("current platform receipt is missing from the support matrix")


def validate_alignment(
    root: Path = ROOT,
    *,
    expected_source_revision: str | None = None,
    artifact_root: Path | None = None,
    require_bound_candidate_match: bool = False,
) -> dict[str, Any]:
    canonical_path = root / "release/CURRENT.json"
    current = _read_json(canonical_path)
    if current.get("schema") != "scirel.release-current.v2":
        raise ValueError("release CURRENT has an invalid schema")
    if current.get("package") != "scirel":
        raise ValueError("release CURRENT names an unexpected package")
    version = current.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("release CURRENT version must be a non-empty string")
    if _project_version(root) != version:
        raise ValueError("release CURRENT version differs from pyproject.toml project.version")
    source_revision = current.get("source_revision")
    if source_revision is not None and (not isinstance(source_revision, str) or not source_revision):
        raise ValueError("source_revision must be null or a non-empty string")
    if expected_source_revision is not None and source_revision != expected_source_revision:
        raise ValueError(
            "release CURRENT source_revision differs from the expected Git revision"
        )
    if source_revision is not None:
        _validate_source_revision(root, source_revision, version)

    wheel = current.get("wheel")
    docs = current.get("documentation")
    if not isinstance(wheel, dict) or not isinstance(docs, dict):
        raise ValueError("release CURRENT must contain wheel and documentation objects")
    if wheel.get("version") != version:
        raise ValueError("release CURRENT version differs from wheel tuple")
    if docs.get("compatible_wheel") != version:
        raise ValueError("documentation tuple is compatible with a different wheel")
    if wheel.get("status") != current.get("status") or docs.get("status") != current.get("status"):
        raise ValueError("release tuple statuses differ")
    if not isinstance(wheel.get("artifact"), dict):
        raise ValueError("wheel tuple lacks artifact metadata")
    artifact_status = _validate_external_artifacts(
        root,
        current,
        version=version,
        source_revision=source_revision,
        artifact_root=artifact_root,
    )
    _validate_platform_receipts(
        root,
        wheel,
        expected_source_revision=source_revision,
        require_bound_candidate_match=require_bound_candidate_match,
    )
    _validate_platform_matrix(
        root,
        version=version,
        receipt_paths={row["path"] for row in wheel["platform_receipts"]},
    )

    _validate_compat_pointer(root, root / "release/wheel/CURRENT.json", line="wheel")
    _validate_compat_pointer(root, root / "release/docs/CURRENT.json", line="documentation")

    selected, selection_digest = _selected_documents(root, docs)
    _validate_catalog_source_revision(root, docs, source_revision)
    handbook_assets, handbook_digest = _handbook_assets(root, docs)
    selected_ids = set(selected)
    handbook_scope = docs.get("handbook_scope", "exact")
    if handbook_scope == "repository":
        if not selected_ids <= handbook_assets:
            raise ValueError("repository handbook does not cover selected document closure")
    elif handbook_scope == "exact":
        if handbook_assets != selected_ids:
            raise ValueError("handbook coverage differs from selected document closure")
    else:
        raise ValueError("documentation handbook_scope is invalid")

    counts = {"operators": 0, "task_graphs": 0}
    for document in selected.values():
        kind = document.get("kind")
        if kind == "operator":
            counts["operators"] += 1
        elif kind == "task_graph":
            counts["task_graphs"] += 1
        else:
            raise ValueError(f"unsupported document kind: {kind}")
        implementation_version = document.get("version", {}).get("implementation_version")
        if implementation_version != version:
            raise ValueError(
                f"document {document.get('asset_id')} targets {implementation_version}, "
                f"which differs from the current project version {version}"
            )
    counts["document_closure"] = len(selected)
    expected = wheel.get("selected_capabilities")
    if expected != counts:
        raise ValueError(f"document counts {counts} differ from wheel selection {expected}")
    if docs.get("capability_counts") != counts:
        raise ValueError("documentation record capability_counts differ from its selection")

    if docs.get("selection_sha256") != selection_digest:
        raise ValueError("release CURRENT selection_sha256 differs from selected docs")
    if docs.get("handbook_sha256") != handbook_digest:
        raise ValueError("release CURRENT handbook_sha256 differs from handbook")
    snapshot_sha256 = docs.get("snapshot_sha256")
    if not isinstance(snapshot_sha256, str) or len(snapshot_sha256) != 64:
        raise ValueError("release CURRENT documentation snapshot_sha256 is invalid")
    _validate_document_integration(
        root,
        docs,
        version=version,
        source_revision=source_revision,
        wheel=wheel,
        selection_digest=selection_digest,
        handbook_digest=handbook_digest,
    )

    return {
        "wheel_version": version,
        "documentation_selection": docs["selection_id"],
        "source_revision": source_revision,
        "capability_counts": counts,
        "selection_sha256": selection_digest,
        "handbook_sha256": handbook_digest,
        "external_artifacts": artifact_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--expected-source-revision",
        help="require CURRENT.source_revision to match this exact Git commit",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="external root containing logical wheel/documentation artifact references",
    )
    parser.add_argument(
        "--require-bound-candidate-match",
        action="store_true",
        help=(
            "require every platform receipt to prove reproducible builds and "
            "a byte match to the wheel bound by CURRENT.json"
        ),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate_alignment(
                args.root.resolve(),
                expected_source_revision=args.expected_source_revision,
                artifact_root=args.artifact_root.resolve() if args.artifact_root else None,
                require_bound_candidate_match=args.require_bound_candidate_match,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
