"""Validate a model standardization submission and emit a review workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scirel_workflow import (  # noqa: E402
    CandidatePackage,
    SciRelWorkflow,
    StandardizationSubmission,
    WorkflowError,
)
from scirel_workflow.models import digest  # noqa: E402


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} must be readable UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} must be readable UTF-8 JSON: {error}") from error


def _file_digest(path: Path) -> str:
    try:
        body = path.read_bytes()
    except OSError as error:
        raise ValueError(f"skill entrypoint cannot be read: {error}") from error
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _git_head(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(f"cannot resolve SciRel Git baseline: {error}") from error
    return completed.stdout.strip()


def build_review_workflow(
    candidate_payload: dict[str, Any],
    submission_payload: dict[str, Any],
    candidate_pool_payload: Any,
    *,
    scirel_git_base: str,
    skill_digest: str,
) -> dict[str, Any]:
    candidate = CandidatePackage.from_mapping(candidate_payload)
    submission = StandardizationSubmission.from_mapping(submission_payload)
    workflow = SciRelWorkflow(candidate)
    workflow.submit_standardization(
        submission,
        expected_scirel_git_base=scirel_git_base,
        expected_candidate_pool_digest=digest(candidate_pool_payload),
        expected_skill_digest=skill_digest,
    )
    return workflow.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("submission", type=Path)
    parser.add_argument("candidate_pool", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--skill-entrypoint",
        type=Path,
        default=ROOT / "skills" / "integration" / "scirel-integration" / "SKILL.md",
    )
    parser.add_argument("--scirel-root", type=Path, default=ROOT)
    args = parser.parse_args()

    try:
        workflow = build_review_workflow(
            _load_object(args.candidate, "candidate"),
            _load_object(args.submission, "standardization submission"),
            _load_json(args.candidate_pool, "candidate pool"),
            scirel_git_base=_git_head(args.scirel_root),
            skill_digest=_file_digest(args.skill_entrypoint),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(
                json.dumps(workflow, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            )
    except FileExistsError:
        print("standardization output already exists", file=sys.stderr)
        return 2
    except (OSError, TypeError, ValueError, WorkflowError) as error:
        print(f"standardization submission rejected: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
