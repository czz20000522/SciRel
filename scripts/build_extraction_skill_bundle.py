from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


BUNDLE_SCHEMA = "scirel.decomposition-skill-bundle"
MANIFEST_PATH = "scirel-decomposition-skill-bundle.json"
SKILL_NAMES = (
    "scientific-computation-asset-extraction",
    "scientific-computation-validation",
    "scientific-operator-review",
    "scientific-relation-implementation",
    "scientific-runtime-dataset-construction",
    "scientific-d2-decomposition",
    "scientific-d3-decomposition",
)
_IGNORED_NAMES = {"__pycache__"}
_IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _included_files(source_root: Path) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for skill_name in SKILL_NAMES:
        skill_root = source_root / skill_name
        if not (skill_root / "SKILL.md").is_file():
            raise ValueError(f"missing required skill entrypoint: {skill_root / 'SKILL.md'}")
        for path in sorted(skill_root.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_symlink():
                raise ValueError(f"skill bundle source may not contain symlinks: {path}")
            if not path.is_file():
                continue
            relative_parts = path.relative_to(source_root).parts
            if any(part in _IGNORED_NAMES for part in relative_parts):
                continue
            if path.suffix.lower() in _IGNORED_SUFFIXES:
                continue
            archive_path = PurePosixPath(*relative_parts).as_posix()
            files.append((archive_path, path.read_bytes()))
    return files


def build_manifest(source_root: Path) -> tuple[dict[str, object], list[tuple[str, bytes]]]:
    files = _included_files(source_root)
    records = [
        {"path": path, "bytes": len(content), "sha256": _sha256(content)}
        for path, content in files
    ]
    digest_payload = "".join(
        f"{record['path']}\0{record['bytes']}\0{record['sha256']}\n" for record in records
    ).encode("utf-8")
    manifest: dict[str, object] = {
        "schema": BUNDLE_SCHEMA,
        "bundle_digest": f"sha256:{_sha256(digest_payload)}",
        "skill_names": list(SKILL_NAMES),
        "entrypoints": [f"{name}/SKILL.md" for name in SKILL_NAMES],
        "files": records,
    }
    return manifest, files


def build_bundle(source_root: Path, output_path: Path) -> dict[str, object]:
    source_root = source_root.resolve()
    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(f"bundle output already exists: {output_path}")
    manifest, files = build_manifest(source_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for archive_path, content in files:
            info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        manifest_info = zipfile.ZipInfo(MANIFEST_PATH, date_time=(1980, 1, 1, 0, 0, 0))
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.create_system = 3
        manifest_info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(
            manifest_info,
            _canonical_json(manifest),
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the authoritative D0-D3 SciRel decomposition bundle.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "skills" / "extraction",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_bundle(args.source_root, args.output)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
