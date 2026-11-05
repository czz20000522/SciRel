"""Run the review closure for held candidates.

Usage:
    .venv/bin/python scripts/review_harness.py --check

The harness validates the held contracts and dependency closure, then checks their
runtime bindings and examples in a separate review process. Direct tests come
only from verification.tests; the default import surface is checked in fresh
processes by the import-guard tests. Passing this closure does not lift a hold or
replace missing external artifacts.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

from validate_asset_documents import (
    load_document_set,
    resolve_test_reference,
    validate_document,
    validate_runtime,
)

ROOT = Path(__file__).resolve().parents[1]
IMPORT_SURFACE_TEST = "tests/tooling/test_hold_import_guard.py"
STAGE_TIMEOUT_SECONDS = 300


def load_review_documents(source_root: Path) -> list[dict]:
    """Load the explicitly held contracts, without silently dropping a binding."""
    review = source_root / "catalog" / "review"
    held = json.loads((review / "HOLD.json").read_text(encoding="utf-8"))["assets"]
    documents = []
    for asset in sorted(held):
        path = review / "examples" / (asset + ".json")
        document = json.loads(path.read_text(encoding="utf-8"))
        validate_document(document, location=str(path))
        if document["asset_id"] != asset:
            raise ValueError(f"{path}: held asset_id differs from filename")
        module = document["public_api"]["python"]["module"]
        candidate = review / "candidates" / "src" / (module.replace(".", "/") + ".py")
        if not candidate.is_file():
            raise ValueError(f"{asset}: review implementation is missing: {candidate}")
        documents.append(document)
    return documents


def review_test_references(documents: list[dict], source_root: Path) -> list[str]:
    """Resolve every declared test file while preserving pytest node selectors."""
    tests = set()
    for document in documents:
        references = document["verification"]["tests"]
        if not references:
            raise ValueError(f"{document['asset_id']}: no direct tests declared")
        for reference in references:
            resolve_test_reference(reference, source_root)
            tests.add(reference)
    return sorted(tests)


def check_contracts() -> None:
    """Validate review runtimes and execute examples without exposing candidates."""
    documents = load_review_documents(ROOT)
    load_document_set(
        ROOT / "catalog" / "examples",
        additional_directories=(ROOT / "catalog" / "review" / "examples",),
    )
    os.environ["SCIREL_REVIEW_HOLD"] = "1"
    for document in documents:
        python_api = document["public_api"]["python"]
        parent_name = python_api["module"].rsplit(".", 1)[0]
        parent = importlib.import_module(parent_name)
        candidate_parent = (
            ROOT / "catalog" / "review" / "candidates" / "src" / parent_name.replace(".", "/")
        )
        if str(candidate_parent) not in parent.__path__:
            parent.__path__.append(str(candidate_parent))

        # Validate the review module binding directly. If a contract explicitly
        # declares a canonical identity, check it separately without treating
        # that metadata as permission to expose a held symbol publicly.
        runtime_document = document
        if "canonical_module" in python_api:
            runtime_document = deepcopy(document)
            runtime_api = runtime_document["public_api"]["python"]
            runtime_api.pop("canonical_module")
            runtime_api.pop("canonical_symbol")
        validate_runtime(runtime_document, source_root=ROOT)
        if "canonical_module" in python_api:
            canonical = importlib.import_module(python_api["canonical_module"])
            implementation = importlib.import_module(python_api["module"])
            if getattr(canonical, python_api["canonical_symbol"], None) is not getattr(
                implementation, python_api["symbol"]
            ):
                raise ValueError(f"{document['asset_id']}: canonical review binding differs")
        exec(
            compile(document["example"]["code"], f"{document['asset_id']} example", "exec"),
            {"__name__": "__main__"},
        )
    print(f"review contracts: {len(documents)} schema/runtime/examples PASS")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.parse_args(argv)
    try:
        documents = load_review_documents(ROOT)
        if not documents:
            print("review harness: no held assets; no tests run")
            return 0
        tests = review_test_references(documents, ROOT)
        resolve_test_reference(IMPORT_SURFACE_TEST, ROOT)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"review harness: {error}", file=sys.stderr)
        return 1
    env = dict(
        os.environ,
        SCIREL_REVIEW_HOLD="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=os.pathsep.join((str(ROOT / "scripts"), str(ROOT / "src"))),
    )
    commands = [
        [
            sys.executable,
            "-B",
            "-c",
            "from review_harness import check_contracts; check_contracts()",
        ],
        [sys.executable, "-B", "-m", "pytest", "-q", *sorted({*tests, IMPORT_SURFACE_TEST})],
    ]
    for command in commands:
        print("review harness:", " ".join(command), flush=True)
        try:
            code = subprocess.run(
                command, cwd=ROOT, env=env, timeout=STAGE_TIMEOUT_SECONDS
            ).returncode
        except subprocess.TimeoutExpired:
            print("review harness: stage timed out", file=sys.stderr)
            return 1
        if code:
            return code
    print("held assets:", ", ".join(document["asset_id"] for document in documents))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
