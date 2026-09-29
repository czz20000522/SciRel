"""Register immutable development candidates in the SciRel release index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scirel_plugin.adapter import review_item_from_body  # noqa: E402


SCHEMA = "scirel.release-index.dev"
_GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def read_index(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"schema", "entries"}:
        raise ValueError("release index fields are invalid")
    if value["schema"] != SCHEMA or not isinstance(value["entries"], list):
        raise ValueError("release index schema or entries are invalid")
    ids = set()
    candidates = set()
    latest_release = None
    for entry in value["entries"]:
        if not isinstance(entry, dict) or entry.get("status") not in {
            "candidate", "released"
        }:
            raise ValueError("release index contains an invalid entry")
        unsigned = {key: part for key, part in entry.items() if key != "entry_digest"}
        if entry.get("entry_digest") != digest(canonical_json(unsigned)):
            raise ValueError("release index entry digest differs from its contents")
        if entry.get("entry_id") in ids:
            raise ValueError("release index repeats an entry ID")
        ids.add(entry["entry_id"])
        if entry["status"] == "candidate":
            if not isinstance(entry.get("items"), list) or not entry["items"]:
                raise ValueError("candidate index entry has no review items")
            candidates.add(entry["entry_id"])
        else:
            if (
                entry.get("predecessor_entry_id") not in candidates
                or entry.get("baseline_entry_id") != latest_release
            ):
                raise ValueError("released index entry has an invalid predecessor")
            latest_release = entry["entry_id"]
    return value


def append_entry(index: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(entry)
    unsigned["entry_digest"] = digest(canonical_json(entry))
    result = {"schema": SCHEMA, "entries": [*index["entries"], unsigned]}
    if any(old["entry_id"] == entry["entry_id"] for old in index["entries"]):
        raise ValueError("release index entry ID already exists")
    return result


def register_candidate(
    *,
    item_artifacts: list[Path],
    git_revision: str,
    output_path: Path,
    existing_index: Path | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    if not _GIT_REVISION.fullmatch(git_revision):
        raise ValueError("candidate Git revision must be an exact 40-character SHA")
    if not item_artifacts:
        raise ValueError("candidate requires review item artifacts")
    index = (
        read_index(existing_index)
        if existing_index is not None
        else {"schema": SCHEMA, "entries": []}
    )
    items = []
    candidate_ids = set()
    draft_ids = set()
    asset_ids = set()
    item_refs = set()
    for path in item_artifacts:
        body = path.read_bytes()
        item = review_item_from_body(body)
        if item["status"] != "review_pending":
            raise ValueError("candidate item must be pending")
        asset = item["asset"]
        asset_id = asset.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError("candidate asset requires a stable asset_id")
        if asset_id in asset_ids or item["item_ref"] in item_refs:
            raise ValueError("candidate repeats an asset or review item")
        asset_ids.add(asset_id)
        item_refs.add(item["item_ref"])
        candidate_ids.add(item["candidate_id"])
        draft_ids.add(item["draft_id"])
        items.append(
            {
                "item_ref": item["item_ref"],
                "initial_revision": digest(body),
                "asset_id": asset_id,
                "document_digest": digest(canonical_json(asset)),
                "dependency_asset_ids": item["dependency_asset_ids"],
            }
        )
    if len(candidate_ids) != 1 or len(draft_ids) != 1:
        raise ValueError("candidate items must belong to one candidate and draft")
    items.sort(key=lambda item: item["item_ref"])
    entry = {
        "entry_id": "candidate:" + digest(canonical_json([git_revision, items]))[7:],
        "status": "candidate",
        "candidate_id": candidate_ids.pop(),
        "draft_id": draft_ids.pop(),
        "git_revision": git_revision,
        "items": items,
    }
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-artifact", type=Path, action="append", required=True)
    parser.add_argument("--git-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--existing-index", type=Path)
    args = parser.parse_args()
    try:
        index = register_candidate(
            item_artifacts=args.item_artifact,
            git_revision=args.git_revision,
            output_path=args.output,
            existing_index=args.existing_index,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"candidate registration failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"entry": index["entries"][-1]["entry_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
