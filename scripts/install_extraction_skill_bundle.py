from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from build_extraction_skill_bundle import BUNDLE_SCHEMA, MANIFEST_PATH, SKILL_NAMES


INSTALL_RECEIPT = ".scirel-extraction-install.json"
ACTIVE_LINK = ".scirel-extraction-active"
BUNDLE_DIR = ".scirel-extraction-bundles"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _validated_bundle(bundle_path: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    bundle_bytes = bundle_path.read_bytes()
    with zipfile.ZipFile(bundle_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or MANIFEST_PATH not in names:
            raise ValueError("bundle must contain one unique manifest")
        manifest = json.loads(archive.read(MANIFEST_PATH))
        if manifest.get("schema") != BUNDLE_SCHEMA:
            raise ValueError("unsupported extraction skill bundle schema")
        if manifest.get("skill_names") != list(SKILL_NAMES):
            raise ValueError("bundle does not contain the exact SciRel decomposition skills")
        if manifest.get("entrypoints") != [f"{name}/SKILL.md" for name in SKILL_NAMES]:
            raise ValueError("bundle entrypoints do not match the SciRel decomposition skills")
        records = manifest.get("files")
        if not isinstance(records, list) or not records:
            raise ValueError("bundle manifest has no files")
        expected_names = {MANIFEST_PATH}
        payload: dict[str, bytes] = {}
        digest_lines: list[str] = []
        record_names: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("bundle manifest contains an invalid file record")
            name = record.get("path")
            if not isinstance(name, str):
                raise ValueError("bundle file path must be a string")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
                raise ValueError(f"unsafe bundle file path: {name}")
            if path.parts[0] not in SKILL_NAMES:
                raise ValueError(f"file is outside the SciRel decomposition skills: {name}")
            if name in record_names:
                raise ValueError(f"bundle manifest repeats a file path: {name}")
            record_names.add(name)
            info = archive.getinfo(name)
            file_type = (info.external_attr >> 16) & 0o170000
            if file_type not in (0, stat.S_IFREG):
                raise ValueError(f"bundle entry is not a regular file: {name}")
            content = archive.read(name)
            if record.get("bytes") != len(content) or record.get("sha256") != _sha256(content):
                raise ValueError(f"bundle file digest mismatch: {name}")
            expected_names.add(name)
            payload[name] = content
            digest_lines.append(f"{name}\0{len(content)}\0{_sha256(content)}\n")
        if not set(manifest["entrypoints"]).issubset(record_names):
            raise ValueError("bundle payload is missing a required skill entrypoint")
        if set(names) != expected_names:
            raise ValueError("bundle contains files that are absent from its manifest")
        expected_digest = f"sha256:{_sha256(''.join(digest_lines).encode('utf-8'))}"
        if manifest.get("bundle_digest") != expected_digest:
            raise ValueError("bundle root digest mismatch")
    manifest["artifact_sha256"] = f"sha256:{_sha256(bundle_bytes)}"
    return manifest, payload


def _make_tree_writable(path: Path) -> None:
    for child in path.rglob("*"):
        if child.is_dir():
            child.chmod(0o755)
        elif not child.is_symlink():
            child.chmod(0o644)
    path.chmod(0o755)


def _safe_remove_owned_bundle(path: Path, bundle_root: Path) -> None:
    resolved_parent = path.resolve().parent
    if resolved_parent != bundle_root.resolve() or not path.name.startswith("sha256-"):
        raise ValueError(f"refusing to remove non-owned bundle path: {path}")
    _make_tree_writable(path)
    shutil.rmtree(path)


def _verify_installed_payload(bundle_path: Path, payload: dict[str, bytes]) -> None:
    actual_files: set[str] = set()
    for path in bundle_path.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"installed bundle contains a symlink: {path}")
        if path.is_file():
            relative = path.relative_to(bundle_path).as_posix()
            actual_files.add(relative)
            if relative == MANIFEST_PATH:
                continue
            if relative not in payload or path.read_bytes() != payload[relative]:
                raise ValueError(f"installed bundle payload mismatch: {relative}")
    if actual_files != set(payload) | {MANIFEST_PATH}:
        raise ValueError("installed bundle file set does not match the verified artifact")


def _make_bundle_read_only(bundle_path: Path) -> None:
    for path in bundle_path.rglob("*"):
        if path.is_dir():
            path.chmod(0o555)
        elif not path.is_symlink():
            path.chmod(0o444)
    bundle_path.chmod(0o555)


def install_bundle(bundle_path: Path, target_root: Path, *, dry_run: bool = False) -> dict[str, object]:
    manifest, payload = _validated_bundle(bundle_path.resolve())
    digest = str(manifest["bundle_digest"]).removeprefix("sha256:")
    target_root = target_root.resolve()
    bundle_root = target_root / BUNDLE_DIR
    final_bundle = bundle_root / f"sha256-{digest}"
    active_link = target_root / ACTIVE_LINK
    receipt_path = target_root / INSTALL_RECEIPT

    if bundle_root.is_symlink() or (bundle_root.exists() and not bundle_root.is_dir()):
        raise ValueError(f"refusing to use a non-directory SciRel bundle root: {bundle_root}")
    if active_link.is_symlink():
        active_target = Path(os.readlink(active_link))
        if active_target.parent != Path(BUNDLE_DIR) or not active_target.name.startswith("sha256-"):
            raise ValueError(f"refusing to replace a foreign active bundle link: {active_link}")
    elif active_link.exists():
        raise ValueError(f"refusing to replace a foreign active bundle path: {active_link}")
    if final_bundle.is_symlink():
        raise ValueError(f"refusing to trust a symlinked content-addressed bundle: {final_bundle}")

    foreign_entries = []
    for skill_name in SKILL_NAMES:
        entry = target_root / skill_name
        desired = Path(ACTIVE_LINK) / skill_name
        if entry.is_symlink() and Path(os.readlink(entry)) != desired:
            foreign_entries.append(str(entry))
        elif entry.exists() and not entry.is_symlink():
            foreign_entries.append(str(entry))
    if foreign_entries:
        raise ValueError("refusing to replace non-SciRel skill directories: " + ", ".join(foreign_entries))

    previous_bundles = []
    if bundle_root.is_dir():
        for path in bundle_root.iterdir():
            if path == final_bundle:
                continue
            if path.is_symlink() or not path.is_dir() or not path.name.startswith("sha256-"):
                raise ValueError(f"refusing to manage an unowned bundle-root entry: {path}")
            previous_bundles.append(str(path))
        previous_bundles.sort()
    plan: dict[str, object] = {
        "schema": "scirel.extraction-skill-install-plan.v1",
        "bundle_digest": manifest["bundle_digest"],
        "artifact_sha256": manifest["artifact_sha256"],
        "target_skill_root": str(target_root),
        "entrypoints": [str(target_root / name / "SKILL.md") for name in SKILL_NAMES],
        "previous_bundles_to_remove": previous_bundles,
        "dry_run": dry_run,
    }
    if dry_run:
        return plan

    target_root.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    if not final_bundle.exists():
        stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=bundle_root))
        try:
            for name, content in payload.items():
                destination = stage / Path(*PurePosixPath(name).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            (stage / MANIFEST_PATH).write_bytes(_canonical_json({k: v for k, v in manifest.items() if k != "artifact_sha256"}))
            _verify_installed_payload(stage, payload)
            _make_bundle_read_only(stage)
            os.replace(stage, final_bundle)
        finally:
            if stage.exists():
                _make_tree_writable(stage)
                shutil.rmtree(stage)
    _verify_installed_payload(final_bundle, payload)
    _make_bundle_read_only(final_bundle)

    for skill_name in SKILL_NAMES:
        entry = target_root / skill_name
        desired = Path(ACTIVE_LINK) / skill_name
        if entry.is_symlink() and Path(os.readlink(entry)) == desired:
            continue
        temporary = target_root / f".{skill_name}.tmp-{os.getpid()}"
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
        temporary.symlink_to(desired, target_is_directory=True)
        os.replace(temporary, entry)

    temporary_active = target_root / f"{ACTIVE_LINK}.tmp-{os.getpid()}"
    if temporary_active.exists() or temporary_active.is_symlink():
        temporary_active.unlink()
    temporary_active.symlink_to(Path(BUNDLE_DIR) / final_bundle.name, target_is_directory=True)
    os.replace(temporary_active, active_link)

    for path_text in previous_bundles:
        path = Path(path_text)
        if path.exists():
            _safe_remove_owned_bundle(path, bundle_root)
    receipt = dict(plan)
    receipt["schema"] = "scirel.extraction-skill-install-receipt.v1"
    receipt["dry_run"] = False
    receipt["removed_previous_bundles"] = previous_bundles
    temporary_receipt = target_root / f"{INSTALL_RECEIPT}.tmp-{os.getpid()}"
    temporary_receipt.write_bytes(_canonical_json(receipt))
    os.replace(temporary_receipt, receipt_path)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a verified SciRel D0-D3 decomposition skill bundle.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--target-skill-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = install_bundle(args.bundle, args.target_skill_root, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
