"""Build replayable SciRel body-wire request and response fixtures from saved L1."""

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


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_fixture(
    source: Path,
    output_dir: Path,
    *,
    artifact_ref: str,
) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite fixture directory: {output_dir}")
    source_body = source.read_bytes()
    source_text = source_body.decode("utf-8")
    source_payload = json.loads(source_text)
    if not isinstance(source_payload, dict):
        raise ValueError("saved L1 fixture must contain a JSON object")
    source_digest = _digest(source_body)
    import_request = {
        "operation": "scirel.import_l1",
        "artifact_ref": artifact_ref,
        "artifact_digest": source_digest,
        "media_type": "application/json",
        "body": source_text,
    }
    candidate_response = execute_body_import_wire(import_request)
    candidate_body = candidate_response["body"].encode("utf-8")
    candidate = json.loads(candidate_response["body"])
    check_request = {
        "operation": "scirel.automated_check",
        "artifact_ref": f"fixture://candidate/{candidate['candidate_id']}",
        "artifact_digest": _digest(candidate_body),
        "media_type": "application/json",
        "body": candidate_response["body"],
    }
    check_response = execute_body_import_wire(check_request)

    output_dir.mkdir(parents=True)
    _write(output_dir / "01-import-request.json", import_request)
    _write(output_dir / "02-candidate-response.json", candidate_response)
    (output_dir / "02-candidate-body.json").write_bytes(candidate_body)
    _write(output_dir / "03-automated-check-request.json", check_request)
    _write(output_dir / "04-automated-check-response.json", check_response)
    result_body_bytes = check_response["body"].encode("utf-8")
    (output_dir / "05-automated-check-result-body.json").write_bytes(
        result_body_bytes
    )
    result_body = json.loads(result_body_bytes)
    summary = {
        "schema": "scirel.l1-wire-fixture.dev",
        "source_digest": source_digest,
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate_response["body_digest"],
        "result_digest": check_response["body_digest"],
        "next_action": result_body["next_action"],
        "gap_count": len(result_body["gaps"]),
    }
    _write(output_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact-ref", default="fixture://saved-l1/input")
    args = parser.parse_args()
    summary = build_fixture(
        args.source.resolve(),
        args.output_dir.resolve(),
        artifact_ref=args.artifact_ref,
    )
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
