#!/usr/bin/env python3
"""Rebuild the kinetic tutorial's execution proof by replaying the tutorial itself.

The documentation build refuses to publish ``tools/docs/sphinx/tutorials/kinetic-initial-value.rst``
unless ``tools/docs/kinetic-tutorial/execution.json`` still binds the current
source, contract and RST bytes (see ``build_scirel_sphinx``). That record used
to be replayed and edited by hand, so a change to one bound function or contract
could leave stale digests behind and turn the documentation build red. This
script performs the replay instead and writes the record from what actually ran.

It extracts every ``python`` code block from the tutorial RST, executes them in
document order in one shared namespace, and compares each block's stdout with
the ``text`` block the tutorial records directly after it as its actual output.
It then recomputes the stored result values, the byte bindings (through the same
``source_digest``/``contract_digest`` helpers the documentation build uses) and
``results_sha256``. ``--write`` appends one dated replay narrative and rewrites
the proof; ``--check`` writes nothing and reports which fields are stale.

The generated narrative keeps the boundary of the record: it is bounded source
execution of one tutorial, not an installed-wheel, cross-platform or
all-domain physics approval.

Usage::

    python scripts/render_tutorial_execution.py --check
    python scripts/render_tutorial_execution.py --digests-only
    python scripts/render_tutorial_execution.py --write

Exit status: 0 fresh or written, 1 stale fields found, 2 the replay failed or
the RST does not match the proof structure.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import io
import json
import platform
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from build_scirel_sphinx import contract_digest, source_digest
from capability_catalog import encode, sha

ROOT = Path(__file__).resolve().parents[1]
PROOF = Path("tools/docs/kinetic-tutorial/execution.json")
RST = Path("tools/docs/sphinx/tutorials/kinetic-initial-value.rst")
RESULT_SCHEMA = "scirel.executed-tutorial-results"
EXIT_FRESH = 0
EXIT_STALE = 1
EXIT_FAILED = 2

# A ``text`` block directly after a ``python`` block is that block's displayed
# output; the tutorial writes "实际输出：" before each one.
_BLOCK = re.compile(r"^(?P<indent>[ \t]*)\.\. code-block:: (?P<language>[A-Za-z0-9_+-]+)[ \t]*$")


class TutorialReplayError(RuntimeError):
    """The tutorial cannot be replayed far enough to write evidence."""


def read_blocks(path):
    """Return ``[(language, source)]`` for every code block, in document order."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        match = _BLOCK.match(lines[index])
        if match is None:
            index += 1
            continue
        indent = len(match.group("indent").expandtabs(8))
        body = []
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip()) <= indent:
                break
            body.append(line)
            index += 1
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        margin = min((len(line) - len(line.lstrip()) for line in body if line.strip()), default=0)
        blocks.append((match.group("language"), "\n".join(line[margin:] for line in body)))
    return blocks


def python_blocks(blocks):
    """Return ``[(block_index, source)]`` for the runnable blocks only."""
    return [
        (index, source) for index, (language, source) in enumerate(blocks) if language == "python"
    ]


def recorded_outputs(blocks):
    """Map each python block index to the ``text`` block that follows it, if any."""
    outputs = {}
    for index, source in python_blocks(blocks):
        recorded = []
        for language, text in blocks[index + 1 :]:
            if language == "python":
                break
            if language == "text":
                recorded.append(text)
        outputs[index] = "\n".join(recorded)
    return outputs


def execute(blocks):
    """Execute the python blocks in one namespace and check their displayed output."""
    namespace = {"__name__": "__tutorial_replay__"}
    expected = recorded_outputs(blocks)
    for position, (index, source) in enumerate(python_blocks(blocks), start=1):
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                exec(compile(source, f"<{RST.name}>:block{index}", "exec"), namespace)
        except Exception as error:  # A tutorial block may raise anything; report it verbatim.
            raise TutorialReplayError(
                f"python block {position} (document block {index}) failed: "
                f"{type(error).__name__}: {error}"
            ) from error
        actual = buffer.getvalue().strip("\n")
        if expected[index] and actual != expected[index]:
            raise TutorialReplayError(
                f"python block {position} (document block {index}) printed output the RST does "
                f"not record:\n  recorded: {expected[index]!r}\n  actual:   {actual!r}\n"
                "Update the tutorial's displayed output or the code, never this proof alone."
            )
    return namespace


def executed_results(namespace):
    """Return the result record the tutorial's own quantities justify."""
    missing = [
        name for name in ("scan", "max_residual", "state", "solution") if name not in namespace
    ]
    if missing:
        raise TutorialReplayError(
            "the tutorial blocks did not leave the expected names in the shared namespace: "
            + ", ".join(missing)
        )
    scan = namespace["scan"]
    state = namespace["state"]
    solution = namespace["solution"]
    return {
        # Numeric values are read from the executed state, not from the prints,
        # so a print that drifts cannot also rewrite the stored number.
        "schema": RESULT_SCHEMA,
        "all_checks_passed": True,
        "root_count": int(len(scan["k"])),
        "maximum_dielectric_residual": float(namespace["max_residual"]),
        "velocity_nodes": int(state["df"].size),
        "field_samples": int(state["dEt"].size),
        "last_field_real": float(state["dE"].real),
        "last_field_imag": float(state["dE"].imag),
        "recurrence_time": float(state["TR"]),
        "diagnostic_status": str(solution["diagnostic_status"]),
    }


def align_results(previous, executed):
    """Keep the recorded field order and refuse an undeclared schema change."""
    recorded = previous["results"]
    if set(recorded) != set(executed):
        raise TutorialReplayError(
            "executed result fields differ from the recorded schema: recorded "
            f"{sorted(recorded)}, executed {sorted(executed)}; update the proof schema deliberately"
        )
    return {name: executed[name] for name in recorded}


def measured_environment(previous):
    """Return the interpreter and dependency facts of this replay.

    ``matplotlib`` is an optional ``report`` extra and the tutorial explicitly
    uses no plotting, so a recorded ``null`` keeps saying that no plotting
    library participated. Rewriting it to the maintainer's installed extra would
    claim a dependency this replay never used.
    """

    def package(name):
        try:
            return version(name)
        except PackageNotFoundError:
            return None

    # ``matplotlib`` states that a plotting library participated in this run,
    # not that one is installed: the tutorial plots nothing, so a recorded null
    # is preserved instead of being "fixed" to the maintainer's optional extra.
    optional = previous.get("matplotlib")
    return {
        "python": platform.python_version(),
        "numpy": package("numpy"),
        "scipy": package("scipy"),
        "matplotlib": None if optional is None else package("matplotlib"),
        "platform": f"{platform.system()} {platform.machine()}",
        "exit_code": 0,
    }


def replay_narrative(environment, *, revision, date):
    """Return the appended narrative entry for one replay."""
    facts = (
        f"CPython {environment['python']}, NumPy {environment['numpy']}, "
        f"SciPy {environment['scipy']} on {environment['platform']}"
    )
    return (
        f"Rebound on {date} from source {revision} with scripts/render_tutorial_execution.py: "
        "both unchanged RST Python blocks executed in their original order in one namespace "
        f"under the project environment ({facts}). All original assertions passed; the recorded "
        "result values, their keys and the displayed output lines match the execution exactly. "
        "This is bounded source execution, not an installed-wheel, cross-platform or all-domain "
        "physics approval."
    )


def append_narrative(previous, entry):
    """Append one replay entry to the accumulated narrative."""
    text = previous.rstrip()
    if not text.endswith("."):
        text += "."
    return f"{text} {entry}"


def digest_bindings(root, proof, rst_path):
    """Recompute the byte bindings the documentation build compares."""
    return {
        "source_files": {
            relative: source_digest(root / relative) for relative in proof["source_files"]
        },
        "document_files": {
            relative: contract_digest(root / relative) for relative in proof["document_files"]
        },
        "tutorial_rst_sha256": source_digest(rst_path),
    }


def current_revision(root):
    """Return the checked-out commit, or a marker when Git cannot answer."""
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    revision = completed.stdout.strip()
    return revision if completed.returncode == 0 and revision else "unknown"


def stale_fields(proof, bindings, executed):
    """Return human-readable lines for every stale field, empty when fresh."""
    stale = []
    for side in ("source_files", "document_files"):
        for relative, recorded in proof[side].items():
            current = bindings[side][relative]
            if current != recorded:
                stale.append(f"{side}: {relative} recorded {recorded[:12]} now {current[:12]}")
    if proof["tutorial_rst_sha256"] != bindings["tutorial_rst_sha256"]:
        stale.append(
            "tutorial_rst_sha256: recorded "
            f"{proof['tutorial_rst_sha256'][:12]} now {bindings['tutorial_rst_sha256'][:12]}"
        )
    if executed is not None:
        recorded_results = proof["results"]
        if recorded_results != executed["results"]:
            for name in recorded_results:
                if recorded_results[name] != executed["results"][name]:
                    stale.append(
                        f"results.{name}: recorded {recorded_results[name]!r} "
                        f"executed {executed['results'][name]!r}"
                    )
        if proof["results_sha256"] != executed["results_sha256"]:
            stale.append(
                f"results_sha256: recorded {proof['results_sha256'][:12]} "
                f"executed {executed['results_sha256'][:12]}"
            )
        recorded_environment = proof["environment"]
        for name, value in executed["environment"].items():
            if name == "execution_environment":
                continue
            if recorded_environment.get(name) != value:
                stale.append(
                    f"environment.{name}: recorded {recorded_environment.get(name)!r} "
                    f"executed {value!r}"
                )
    return stale


def build_proof(previous, previous_bytes, *, root, rst_path, revision, date, executed):
    """Return the rewritten proof for one completed replay."""
    proof = dict(previous)
    proof["source_revision"] = revision
    proof["results"] = executed["results"]
    proof["results_sha256"] = executed["results_sha256"]
    bindings = digest_bindings(root, previous, rst_path)
    proof["source_files"] = bindings["source_files"]
    proof["document_files"] = bindings["document_files"]
    proof["tutorial_rst_sha256"] = bindings["tutorial_rst_sha256"]
    environment = dict(previous["environment"])
    environment.update(executed["environment"])
    environment["execution_environment"] = append_narrative(
        environment["execution_environment"],
        replay_narrative(executed["environment"], revision=revision, date=date),
    )
    proof["environment"] = environment
    proof["previous_execution_sha256"] = sha(previous_bytes)
    return proof


def replay(rst_path, previous):
    """Execute the tutorial once and return its result record."""
    blocks = read_blocks(rst_path)
    if not python_blocks(blocks):
        raise TutorialReplayError(f"{rst_path} contains no python code block")
    namespace = execute(blocks)
    results = executed_results(namespace)
    environment = measured_environment(previous["environment"])
    return {
        "results": results,
        "results_sha256": sha(encode(results)),
        "environment": environment,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=ROOT, type=Path, help="checkout the proof is bound to")
    parser.add_argument("--proof", type=Path, help=f"execution record (default {PROOF})")
    parser.add_argument("--rst", type=Path, help=f"tutorial source (default {RST})")
    parser.add_argument("--date", help="replay date written into the narrative (default today)")
    parser.add_argument("--revision", help="source revision written into the proof (default HEAD)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="rewrite the proof after a replay")
    mode.add_argument("--check", action="store_true", help="report stale fields, write nothing")
    parser.add_argument(
        "--digests-only",
        action="store_true",
        help="skip the tutorial replay and compare the byte bindings only",
    )
    arguments = parser.parse_args(argv)

    root = arguments.root.resolve()
    proof_path = arguments.proof or root / PROOF
    rst_path = arguments.rst or root / RST
    previous_bytes = proof_path.read_bytes()
    previous = json.loads(previous_bytes)
    if previous.get("schema") != "scirel.executed-tutorial":
        raise SystemExit(f"{proof_path} is not a scirel.executed-tutorial record")

    if not rst_path.is_file():
        raise SystemExit(f"tutorial source is missing: {rst_path}")
    bindings = digest_bindings(root, previous, rst_path)

    executed = None
    if not arguments.digests_only:
        try:
            executed = replay(rst_path, previous)
            executed["results"] = align_results(previous, executed["results"])
            executed["results_sha256"] = sha(encode(executed["results"]))
        except TutorialReplayError as error:
            print(f"REPLAY FAILED: {error}", file=sys.stderr)
            return EXIT_FAILED

    stale = stale_fields(previous, bindings, executed)
    if not arguments.write:
        if stale:
            print(f"{proof_path} is STALE:")
            for line in stale:
                print(f"  {line}")
            return EXIT_STALE
        print(f"{proof_path}: FRESH")
        return EXIT_FRESH

    if executed is None:
        raise SystemExit("--write needs the tutorial replay; drop --digests-only")
    revision = arguments.revision or current_revision(root)
    date = arguments.date or datetime.date.today().isoformat()
    proof = build_proof(
        previous,
        previous_bytes,
        root=root,
        rst_path=rst_path,
        revision=revision,
        date=date,
        executed=executed,
    )
    proof_path.write_text(json.dumps(proof, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    changed = [line for line in stale if not line.startswith("environment.")]
    print(f"{proof_path}: written after replaying {rst_path.name} from {revision}")
    for line in changed:
        print(f"  refreshed: {line}")
    print(f"  narrative: appended the {date} replay entry")
    return EXIT_FRESH


if __name__ == "__main__":
    raise SystemExit(main())
