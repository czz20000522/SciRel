"""Verify local outbound evaluation manifests against frozen artifacts.

This is an explicit evaluation verifier, not part of the ordinary pytest
baseline.  It intentionally fails when a referenced frozen artifact is missing;
that absence means the local evidence cannot be verified, not that it passed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "docs" / "evaluations" / "outbound-progressive-projects" / "manifests"


@dataclass(frozen=True)
class ManifestFileHashPair:
    manifest_name: str
    path_key: str
    hash_key: str
    path: str
    sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_file(path_text: str, expected: str, label: str) -> list[str]:
    path = ROOT / path_text
    if not path.is_file():
        return [f"{label}: missing file {path_text}"]
    actual = _sha256(path)
    if actual != expected:
        return [f"{label}: expected {expected}, got {actual} for {path_text}"]
    return []


def _verify_p3_reactivation() -> list[str]:
    manifest_path = MANIFEST_DIR / "2026-09-25-p3-reactivation-claude.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    archives = manifest["archives"]
    traces = manifest["traces"]
    errors.extend(_check_file(archives["final"], archives["final_sha256"], "p3-reactivation final archive"))
    errors.extend(_check_file(archives["round1"], archives["round1_sha256"], "p3-reactivation round1 archive"))
    errors.extend(_check_file(traces["round1"], traces["round1_sha256"], "p3-reactivation round1 trace"))
    errors.extend(_check_file(traces["round2"], traces["round2_sha256"], "p3-reactivation round2 trace"))
    return errors


def _verify_acceptance_reuse(manifest_name: str, label: str) -> list[str]:
    manifest_path = MANIFEST_DIR / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return _check_file(
        manifest["archive"],
        manifest["archive_sha256"],
        label,
    )


def _verify_evidence_file(manifest_name: str, label: str) -> list[str]:
    manifest_path = MANIFEST_DIR / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return _check_file(
        manifest["evidence"]["path"],
        manifest["evidence"]["sha256"],
        label,
    )


def _collect_manifest_file_hash_pairs(
    value: object,
    *,
    manifest_name: str,
    prefix: str = "",
) -> list[ManifestFileHashPair]:
    if not isinstance(value, dict):
        return []
    pairs: list[ManifestFileHashPair] = []
    if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
        pairs.append(
            ManifestFileHashPair(
                manifest_name=manifest_name,
                path_key=f"{prefix}path",
                hash_key=f"{prefix}sha256",
                path=value["path"],
                sha256=value["sha256"],
            )
        )
    for key, item in value.items():
        if key.endswith("_sha256") and isinstance(item, str):
            path_key = key.removesuffix("_sha256")
            path = value.get(path_key)
            if isinstance(path, str):
                pairs.append(
                    ManifestFileHashPair(
                        manifest_name=manifest_name,
                        path_key=f"{prefix}{path_key}",
                        hash_key=f"{prefix}{key}",
                        path=path,
                        sha256=item,
                    )
                )
        if isinstance(item, dict):
            pairs.extend(
                _collect_manifest_file_hash_pairs(
                    item,
                    manifest_name=manifest_name,
                    prefix=f"{prefix}{key}.",
                )
            )
    return pairs


def _manifest_file_hash_pairs() -> list[ManifestFileHashPair]:
    pairs: list[ManifestFileHashPair] = []
    for manifest_path in sorted(MANIFEST_DIR.glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pairs.extend(
            _collect_manifest_file_hash_pairs(
                manifest,
                manifest_name=manifest_path.name,
            )
        )
    return pairs


def _verify_manifest_file_hash_pairs() -> list[str]:
    errors: list[str] = []
    for pair in _manifest_file_hash_pairs():
        errors.extend(
            _check_file(
                pair.path,
                pair.sha256,
                f"{pair.manifest_name} {pair.path_key}",
            )
        )
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(_verify_manifest_file_hash_pairs())
    errors.extend(_verify_p3_reactivation())
    errors.extend(
        _verify_evidence_file(
            "2026-09-25-affected-selector-scirel-solving-skill.json",
            "affected selector scirel-solving skill evidence",
        )
    )
    errors.extend(
        _verify_evidence_file(
            "2026-09-25-clean-source-manifest-pytest.json",
            "clean-source manifest pytest evidence",
        )
    )
    errors.extend(
        _verify_acceptance_reuse(
            "2026-09-25-outbound-acceptance-reuse.json",
            "outbound acceptance reuse archive",
        )
    )
    errors.extend(
        _verify_acceptance_reuse(
            "2026-09-25-outbound-acceptance-reuse-v4.json",
            "outbound acceptance reuse v4 archive",
        )
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("outbound evaluation frozen artifacts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
