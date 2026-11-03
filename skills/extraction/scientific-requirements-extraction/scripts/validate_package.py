"""Check one self-contained case's declared materials and replay records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys


STATES = {"candidate", "reference-reproduced", "frozen"}
REVIEW_STATES = {"pending", "accepted", "not-requested"}
PUBLIC = "题面"
PRIVATE = "参考"
SOURCE = f"{PRIVATE}/source"
RUNTIME = f"{PRIVATE}/runtime"


def has_lock_entries(text: str) -> bool:
    """Reject blank, comment-only and punctuation-only captured lock files."""
    return any(char.isalnum() for line in text.splitlines()
               for char in line.partition("#")[0])


def validate(root: Path, require_reference: bool = False) -> dict:
    root = root.absolute()
    errors: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    def read_json(path: Path, label: str) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("JSON root must be an object")
            return value
        except (OSError, UnicodeError, ValueError) as exc:
            fail(f"{label}: {exc}")
            return {}

    def is_link(path: Path) -> bool:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 1024)

    def check_hardlink(path: Path) -> None:
        info = path.stat()
        if info.st_nlink > 1:
            readonly = bool(getattr(info, "st_file_attributes", 0) & 1) if sys.platform == "win32" else not info.st_mode & 0o222
            if not readonly:
                fail(f"case_root: hardlinked material must be read-only: {path.relative_to(root).as_posix()}")

    def member(value: object, side: str, label: str, directory: bool = False) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            fail(f"{label}: nonempty relative path required")
            return None
        path = PurePosixPath(value)
        prefix = PurePosixPath(side).parts if side else ()
        if ("\\" in value or ":" in value or "\x00" in value or path.is_absolute()
                or PureWindowsPath(value).drive or any(part in {"", ".", ".."} for part in value.split("/"))
                or path.parts[:len(prefix)] != prefix):
            fail(f"{label}: path must stay below {side}/")
            return None
        destination = root.joinpath(*path.parts)
        for current in [destination, *destination.parents]:
            if current == root:
                break
            if (current.exists() or current.is_symlink()) and is_link(current):
                fail(f"{label}: links/reparse points are not accepted packet members")
                return None
        if directory:
            if not destination.is_dir() or not any(p.is_file() for p in destination.rglob("*")):
                fail(f"{label}: nonempty source directory required")
                return None
            return destination
        if not destination.is_file():
            fail(f"{label}: file does not exist")
            return None
        if destination.stat().st_size == 0:
            fail(f"{label}: empty file")
            return None
        return destination

    def paths(value: object, side: str, label: str) -> list[str]:
        if not isinstance(value, list) or not value:
            fail(f"{label}: nonempty path array required")
            return []
        for i, item in enumerate(value):
            member(item, side, f"{label}[{i}]")
        return [item for item in value if isinstance(item, str)]

    def argv(value: object, label: str, portable: bool = False) -> list[str]:
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
            fail(f"{label}: actual argv string array required")
            return []
        if portable and any(PurePosixPath(item.split("=", 1)[-1]).is_absolute()
                            or PureWindowsPath(item.split("=", 1)[-1]).drive or "\\" in item
                            or ".." in PurePosixPath(item.split("=", 1)[-1]).parts for item in value):
            fail(f"{label}: replay argv must be relative to the case root")
        return value

    def result(case_id: object = None, status: object = None) -> dict:
        return {"status": "FAIL" if errors else "PASS", "case_id": case_id, "case_status": status,
                "scope": "Declared material closure and recorded replay only; no execution or scientific approval",
                "scientific_approval": False, "errors": errors, "warnings": warnings}

    if not root.is_dir() or is_link(root):
        fail("case_root: real directory required; links/reparse points are not accepted")
        return result()
    for entry in root.iterdir():
        if is_link(entry):
            fail(f"case_root: linked member {entry.name}")
        elif entry.is_dir():
            if entry.name not in {PUBLIC, PRIVATE}:
                fail(f"case_root: only {PUBLIC}/ and {PRIVATE}/ directories are allowed")
        else:
            if entry.name not in {"case.json", "replay.py", "README.md"} or entry.stat().st_size > 131072:
                fail(f"case_root: unexpected or oversized root entry {entry.name}")
            if entry.is_file():
                check_hardlink(entry)
    pending = [root / side for side in [PUBLIC, PRIVATE] if (root / side).is_dir() and not is_link(root / side)]
    while pending:
        for entry in pending.pop().iterdir():
            if is_link(entry):
                fail(f"case_root: linked member {entry.relative_to(root).as_posix()}")
            elif entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                check_hardlink(entry)

    manifest_path = member("case.json", "", "case.json")
    manifest = read_json(manifest_path, "case.json") if manifest_path else {}
    case_id = manifest.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        fail("id: nonempty string required")
    title = manifest.get("title")
    if not isinstance(title, str) or title != root.name or not re.search(r"[\u3400-\u9fff]", title):
        fail("title: Chinese title matching the case directory name required")
    if manifest.get("replay") != "replay.py":
        fail("replay: expected the case-root entrypoint replay.py")
    status = manifest.get("status") if isinstance(manifest.get("status"), str) else None
    if status not in STATES:
        fail("status: expected candidate, reference-reproduced or frozen")
    coverage = manifest.get("coverage")
    if not isinstance(coverage, list) or not coverage or not all(isinstance(item, str) and item.strip() for item in coverage):
        fail("coverage: nonempty array of capability IDs required")
    elif len(set(coverage)) != len(coverage):
        fail("coverage: duplicate capability IDs")
    if not isinstance(manifest.get("scientific_review"), str) or manifest["scientific_review"] not in REVIEW_STATES:
        fail("scientific_review: expected pending, accepted or not-requested")
    issues = manifest.get("open_issues")
    if not isinstance(issues, list) or not all(isinstance(item, str) for item in issues):
        fail("open_issues: string array required (may be empty)")
        issues = []

    public = manifest.get("public")
    private = manifest.get("private")
    if not isinstance(public, dict):
        fail("public: object required")
        public = {}
    if not isinstance(private, dict):
        fail("private: object required")
        private = {}
    for key in ["statement", "output_spec", "acceptance"]:
        member(public.get(key), PUBLIC, f"public.{key}")
    inputs = paths(public.get("inputs"), PUBLIC, "public.inputs")

    provenance = member(private.get("provenance"), PRIVATE, "private.provenance")
    if provenance:
        data = read_json(provenance, "private.provenance")
        if not isinstance(data.get("source_revision"), str) or not data["source_revision"].strip():
            fail("provenance.source_revision: nonempty bound source identity required")
        anchors = data.get("anchors")
        if not isinstance(anchors, list) or not anchors or not all(isinstance(item, str) and item.strip() for item in anchors):
            fail("provenance.anchors: nonempty source anchor array required")

    needs_reference = require_reference or status in {"reference-reproduced", "frozen"}

    def required(key: str) -> bool:
        present = key in private
        if not present:
            missing.append(f"private.{key}")
            if needs_reference:
                fail(f"private.{key}: required for a reference-reproduced case")
        return present

    if required("source_bundle"):
        kind = private.get("source_kind")
        if not isinstance(kind, str) or kind not in {"archive", "slice"}:
            fail("private.source_kind: expected archive or slice")
        member(private["source_bundle"], SOURCE, "private.source_bundle", directory=kind == "slice")
    if required("source_licenses"):
        paths(private["source_licenses"], SOURCE, "private.source_licenses")
    if required("runtime_manifest"):
        runtime_path = member(private["runtime_manifest"], RUNTIME, "private.runtime_manifest")
        if runtime_path:
            runtime = read_json(runtime_path, "private.runtime_manifest")
            for key in ["recipe", "dockerfile"]:
                member(runtime.get(key), RUNTIME, f"runtime.{key}")
            locks = runtime.get("dependency_locks")
            if not isinstance(locks, list) or not locks:
                fail("runtime.dependency_locks: nonempty path array required")
            else:
                for i, value in enumerate(locks):
                    label = f"runtime.dependency_locks[{i}]"
                    lock_path = member(value, RUNTIME, label)
                    if lock_path:
                        try:
                            if not has_lock_entries(lock_path.read_text(encoding="utf-8-sig")):
                                fail(f"{label}: no dependency entries; captured lock contains only whitespace, comments or punctuation")
                        except (OSError, UnicodeError) as exc:
                            fail(f"{label}: readable UTF-8 dependency lock required: {exc}")
            dependencies = runtime.get("external_dependencies")
            if not isinstance(dependencies, list) or not dependencies:
                fail("runtime.external_dependencies: explicit environment dependency declarations required")
            else:
                for i, item in enumerate(dependencies):
                    if (not isinstance(item, dict) or not isinstance(item.get("kind"), str)
                            or item["kind"] not in {"oci-image", "tool", "system-library"}
                            or not all(isinstance(item.get(key), str) and item[key].strip() for key in ["identity", "purpose"])):
                        fail(f"runtime.external_dependencies[{i}]: kind, identity and purpose required; no external case materials")

    contract: dict = {}
    contract_outputs: list[str] = []
    if required("replay_contract"):
        contract_path = member(private["replay_contract"], PRIVATE, "private.replay_contract")
        if contract_path:
            contract = read_json(contract_path, "private.replay_contract")
            if contract.get("entrypoint") != "replay.py" or contract.get("cwd") != ".":
                fail("replay_contract: entrypoint=replay.py and cwd=. required")
            command = argv(contract.get("command"), "replay_contract.command", portable=True)
            if len(command) < 2 or command[1] != "replay.py":
                fail("replay_contract.command: expected [tool, replay.py, ...args] from the case root")
            if contract.get("runtime") != private.get("runtime_manifest"):
                fail("replay_contract.runtime: must name this case's runtime_manifest")
            replay_inputs = contract.get("inputs")
            if not isinstance(replay_inputs, list) or not replay_inputs:
                fail("replay_contract.inputs: nonempty case-relative path array required")
            else:
                for i, value in enumerate(replay_inputs):
                    side = PUBLIC if isinstance(value, str) and value.startswith(f"{PUBLIC}/") else PRIVATE
                    member(value, side, f"replay_contract.inputs[{i}]", directory=value == private.get("source_bundle") and private.get("source_kind") == "slice")
                for value in [*inputs, private.get("source_bundle")]:
                    if value and value not in replay_inputs:
                        fail(f"replay_contract.inputs: required material omitted: {value}")
            contract_outputs = paths(contract.get("outputs"), PRIVATE, "replay_contract.outputs")

    if needs_reference or contract:
        member("replay.py", "", "replay")
    elif not (root / "replay.py").is_file():
        missing.append("replay")

    def check_run(key: str, portable: bool = False) -> None:
        if not required(key):
            return
        run_path = member(private[key], PRIVATE, f"private.{key}")
        if not run_path:
            return
        run = read_json(run_path, f"private.{key}")
        if run.get("status") != "PASS" or type(run.get("exit_code")) is not int or run["exit_code"] != 0:
            if needs_reference:
                fail(f"{key}: actual PASS and exit_code=0 required")
            else:
                missing.append(f"private.{key}:successful execution")
        command = argv(run.get("command"), f"{key}.command", portable=portable)
        if not isinstance(run.get("environment"), dict) or not run["environment"]:
            fail(f"{key}.environment: recorded environment identity required")
        outputs = paths(run.get("outputs"), PRIVATE, f"{key}.outputs")
        if portable:
            if run.get("cwd") != "." or command != contract.get("command"):
                fail("replay_run: actual invocation must match replay_contract command and cwd=.")
            if set(outputs) != set(contract_outputs):
                fail("replay_run.outputs: must match replay_contract outputs")
        container = run.get("container")
        if not isinstance(container, dict) or not isinstance(container.get("used"), bool):
            fail(f"{key}.container: object with used boolean required")
        elif container["used"]:
            if not isinstance(container.get("state_after"), str) or container["state_after"] not in {"exited", "stopped", "removed"}:
                fail(f"{key}.container: final stopped state required")
            if not isinstance(container.get("identity"), str) or not container["identity"].strip():
                fail(f"{key}.container.identity: recorded value required")
            if not portable and (not isinstance(container.get("recipe"), str) or not container["recipe"].strip()):
                fail("reference_run.container.recipe: preserve actual historical value")

    check_run("reference_run")
    check_run("replay_run", portable=True)
    if required("comparator"):
        member(private["comparator"], PRIVATE, "private.comparator")
    if missing and status == "candidate":
        warnings.extend(f"HOLD: missing {item}" for item in missing)
        if not any(isinstance(issue, str) and issue.startswith("HOLD:") and issue[5:].strip()
                   for issue in issues):
            fail("candidate.open_issues: explicit HOLD: description required for missing material or execution")
    if status == "frozen":
        if manifest.get("scientific_review") != "accepted":
            fail("frozen: accepted scientific review required")
        member(private.get("review_record"), PRIVATE, "private.review_record")

    return result(case_id, status)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_root", type=Path)
    parser.add_argument("--require-reference", action="store_true")
    args = parser.parse_args()
    result = validate(args.case_root, args.require_reference)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
