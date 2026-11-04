"""Replay one saved L1 JSON artifact through the SciRel wire operations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scirel_plugin import execute_body_import_wire  # noqa: E402


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _wire_response_body(response: dict[str, Any]) -> bytes:
    body = response.get("body")
    if not isinstance(body, str):
        raise ValueError("wire response body must be a UTF-8 string")
    body_bytes = body.encode("utf-8")
    if response.get("body_digest") != _digest(body_bytes):
        raise ValueError("wire response body digest does not match body")
    return body_bytes


def run_smoke(source: Path) -> dict[str, Any]:
    source_body = source.read_bytes()
    source_digest = _digest(source_body)
    import_response = execute_body_import_wire(
        {
            "operation": "scirel.import_l1",
            "artifact_ref": f"local://l1/{source.name}",
            "artifact_digest": source_digest,
            "media_type": "application/json",
            "body": source_body.decode("utf-8"),
        }
    )
    candidate_body = _wire_response_body(import_response)
    candidate = json.loads(candidate_body.decode("utf-8"))
    check_response = execute_body_import_wire(
        {
            "operation": "scirel.automated_check",
            "artifact_ref": "local://candidate/" + candidate["candidate_id"],
            "artifact_digest": _digest(candidate_body),
            "media_type": "application/json",
            "body": candidate_body.decode("utf-8"),
        }
    )
    result_body = _wire_response_body(check_response)
    result = json.loads(result_body.decode("utf-8"))
    return {
        "schema": "scirel.l1-wire-smoke.dev",
        "source": source.as_posix(),
        "source_digest": source_digest,
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": import_response["body_digest"],
        "asset_count": len(candidate.get("assets", [])),
        "result_digest": check_response["body_digest"],
        "next_action": result["next_action"],
        "gap_count": len(result["gaps"]),
        "check_count": len(result["checks"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="saved L1 JSON artifact")
    parser.add_argument("--output", type=Path, required=True, help="new smoke report path")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if not source.is_file():
        raise SystemExit(f"L1 source is not a file: {source}")
    if output.exists():
        raise SystemExit(f"refusing to overwrite smoke report: {output}")
    report = run_smoke(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
