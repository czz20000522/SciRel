#!/usr/bin/env python3
"""Parse and check human-review tickets.

A ticket is one Markdown file with a front matter block. The format and state machine are in
``docs/maintainer/supply-pipeline.md`` section 7. This module uses the standard library only.

Front matter values are a deliberately small subset of YAML: ``key: value`` per line, where a
value is ``null``, an integer, a bare or quoted string, a flow list such as ``[A, B]``, or JSON
(a list or mapping). A ``#`` outside quotes starts a comment.

Commands::

    python scripts/tickets.py list tickets --status decided   # the work to do first
    python scripts/tickets.py check tickets                    # format, location, unique ids
    python scripts/tickets.py check tickets --base origin/main # also the state transitions
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

KINDS = ("physics-dispute", "convention", "scope", "evidence-gap")
STATUSES = ("open", "decided", "applied", "closed")
REQUIRED_KEYS = (
    "id",
    "kind",
    "status",
    "assets",
    "default_applied",
    "options",
    "reviewers_required",
    "decisions",
    "resolution",
    "applied",
)
BODY_HEADINGS = ("## 要决定的问题", "## 选项", "## 各方意见", "## 不决定的后果")
ID_RE = re.compile(r"^T-\d{4}-\d{4}$")
ROOT = Path(__file__).resolve().parents[1]
# Who writes what (supply-pipeline.md section 7.3): the review platform writes only the verdict,
# the agent writes everything else. ``status`` moves with the writer of that step.
VERDICT_KEYS = ("decisions", "resolution")
AGENT_KEYS = tuple(k for k in REQUIRED_KEYS if k not in VERDICT_KEYS + ("status",))
# Allowed status changes, and the keys each one may change besides ``status``. Body edits are
# allowed only while the ticket is open and the status stays open.
TRANSITIONS = {
    ("open", "open"): AGENT_KEYS + VERDICT_KEYS,
    ("open", "decided"): VERDICT_KEYS,
    ("decided", "decided"): (),
    ("decided", "applied"): ("applied",),
    ("applied", "applied"): (),
    ("applied", "closed"): (),
    ("closed", "closed"): (),
}


class TicketError(ValueError):
    """A ticket does not follow the format."""


def _strip_comment(raw: str) -> str:
    quote = None
    for index, char in enumerate(raw):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or raw[index - 1].isspace()):
            return raw[:index].strip()
    return raw.strip()


def _value(raw: str):
    text = _strip_comment(raw)
    if text in ("", "null", "~"):
        return None
    if text[0] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if text[0] == "[" and text[-1] == "]":
                inner = text[1:-1].strip()
                return [_value(item) for item in inner.split(",")] if inner else []
            raise TicketError(f"cannot parse value: {text}") from None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def parse(text: str) -> tuple[dict, str]:
    """Return the front matter mapping and the body of one ticket."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise TicketError("front matter must start on the first line with ---")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise TicketError("front matter has no closing ---") from None
    data = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, raw = line.partition(":")
        if not sep or not re.fullmatch(r"[a-z_]+", key.strip()):
            raise TicketError(f"line {number}: expected 'key: value', got {line!r}")
        key = key.strip()
        if key in data:
            raise TicketError(f"line {number}: duplicate key {key}")
        data[key] = _value(raw)
    return data, "\n".join(lines[end + 1 :])


def check(text: str, *, allowed_statuses: tuple[str, ...] = STATUSES) -> list[str]:
    """Return every format error in one ticket; an empty list means it follows the format."""
    try:
        data, body = parse(text)
    except TicketError as error:
        return [str(error)]
    errors = [f"missing key: {key}" for key in REQUIRED_KEYS if key not in data]
    unknown = sorted(set(data) - set(REQUIRED_KEYS))
    errors += [f"unknown key: {key}" for key in unknown]
    if errors:
        return errors
    if not isinstance(data["id"], str) or not ID_RE.fullmatch(data["id"]):
        errors.append(f"id must look like T-2026-0042, got {data['id']!r}")
    if data["kind"] not in KINDS:
        errors.append(f"kind must be one of {', '.join(KINDS)}; got {data['kind']!r}")
    status = data["status"]
    if status not in allowed_statuses:
        errors.append(f"status must be one of {', '.join(allowed_statuses)}; got {status!r}")
    for key in ("assets", "options"):
        if not isinstance(data[key], list) or not data[key]:
            errors.append(f"{key} must be a non-empty list")
    if not isinstance(data["default_applied"], str) or not data["default_applied"].strip():
        errors.append("default_applied must say which safe default is already in effect")
    required = data["reviewers_required"]
    if not isinstance(required, int) or required < 1:
        errors.append("reviewers_required must be a positive integer")
    if not isinstance(data["decisions"], list):
        errors.append("decisions must be a list")
    options = data["options"] if isinstance(data["options"], list) else []
    if status == "open":
        if data["resolution"] is not None:
            errors.append("an open ticket has no resolution")
        if data["applied"] is not None:
            errors.append("an open ticket has no applied record")
    if status in ("decided", "applied", "closed"):
        if data["resolution"] not in options:
            errors.append(f"resolution must be one of the options {options}")
        decisions = data["decisions"] if isinstance(data["decisions"], list) else []
        reviewers = [d.get("reviewer") if isinstance(d, dict) else None for d in decisions]
        if any(not isinstance(r, str) or not r.strip() for r in reviewers):
            errors.append("every decision must name its reviewer")
        named = [r for r in reviewers if isinstance(r, str) and r.strip()]
        if len(named) != len(set(named)):
            errors.append("a reviewer may record only one decision per ticket")
        agreeing = {
            d["reviewer"]
            for d in decisions
            if isinstance(d, dict)
            and isinstance(d.get("reviewer"), str)
            and d["reviewer"].strip()
            and d.get("option") == data["resolution"]
        }
        if isinstance(required, int) and len(agreeing) < required:
            errors.append(
                f"resolution needs {required} distinct agreeing reviewers; found {len(agreeing)}"
            )
        if len({d.get("option") for d in decisions if isinstance(d, dict)}) > 1:
            errors.append("reviewers disagree; a ticket with split decisions stays open")
    if status in ("applied", "closed"):
        applied = data["applied"]
        if not isinstance(applied, dict) or not all(applied.get(k) for k in ("by", "ref", "date")):
            errors.append("applied must record by, ref and date")
    if status == "decided" and data["applied"] is not None:
        errors.append("a decided ticket is not applied yet")
    for heading in BODY_HEADINGS:
        if heading not in body:
            errors.append(f"body is missing the section {heading}")
    return errors


def check_location(path: Path, data: dict) -> list[str]:
    """A repository ticket lives at ``tickets/<kind>/<id>.md``."""
    errors = []
    if data.get("kind") != path.parent.name:
        errors.append(f"kind {data.get('kind')!r} does not match its directory {path.parent.name}/")
    if data.get("id") != path.stem:
        errors.append(f"id {data.get('id')!r} does not match its file name {path.name}")
    return errors


def check_transition(old: str | None, new: str | None) -> list[str]:
    """Return the errors of one ticket change from the base text ``old`` to ``new``.

    ``None`` stands for a missing file. Both texts are assumed to pass ``check``.
    """
    if new is None:
        return ["tickets are never deleted; close them instead"] if old is not None else []
    new_data, new_body = parse(new)
    if old is None:
        errors = []
        if new_data["status"] != "open":
            errors.append(f"a new ticket starts open, not {new_data['status']}")
        if new_data["decisions"]:
            errors.append("a new ticket carries no decisions; the review platform writes them")
        return errors
    old_data, old_body = parse(old)
    step = (old_data["status"], new_data["status"])
    if step not in TRANSITIONS:
        return [f"status may not change from {step[0]} to {step[1]}"]
    allowed = TRANSITIONS[step]
    errors = [
        f"{key} may not change when the status goes from {step[0]} to {step[1]}"
        for key in REQUIRED_KEYS
        if key != "status" and key not in allowed and old_data.get(key) != new_data.get(key)
    ]
    if step != ("open", "open") and old_body.strip() != new_body.strip():
        errors.append(f"the body may not change when the status goes from {step[0]} to {step[1]}")
    if "decisions" in allowed:
        old_decisions, new_decisions = old_data["decisions"], new_data["decisions"]
        if new_decisions[: len(old_decisions)] != old_decisions:
            errors.append("recorded decisions may only be appended to, never edited or removed")
    return errors


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def base_texts(root: Path, base: str) -> dict[Path, str]:
    """Return the ticket texts under ``root`` at revision ``base``, keyed by absolute path."""
    top = Path(_git(["rev-parse", "--show-toplevel"], root).stdout.strip())
    listed = _git(["ls-tree", "-r", "--name-only", base, "--", str(root.resolve())], top)
    if listed.returncode != 0:
        raise TicketError(f"--base {base!r} is not a revision of this repository")
    texts = {}
    for name in listed.stdout.splitlines():
        if name.endswith(".md") and not name.endswith("README.md"):
            texts[(top / name).resolve()] = _git(["show", f"{base}:{name}"], top).stdout
    return texts


def base_for(paths: list[Path], base: str) -> dict[Path, str]:
    """Return the baseline texts in the scope of ``paths``.

    A directory covers every ticket under it, so a ticket deleted there is reported. A file
    covers only itself: its siblings are outside the requested scope and must not be reported
    as deleted.
    """
    texts: dict[Path, str] = {}
    for path in paths:
        if path.is_dir():
            texts.update(base_texts(path, base))
        else:
            wanted = path.resolve()
            texts.update({k: v for k, v in base_texts(path.parent, base).items() if k == wanted})
    return texts


def check_files(files: list[Path], *, base: dict[Path, str] | None = None) -> list[str]:
    """Return every error of the repository tickets ``files``, prefixed with their path."""
    errors = []
    seen: dict[str, Path] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        own = check(text)
        if not own:
            data, _ = parse(text)
            own = check_location(path, data)
            if data["id"] in seen:
                own.append(f"id {data['id']} is already used by {seen[data['id']]}")
            seen.setdefault(data["id"], path)
        if not own and base is not None:
            old = base.get(path.resolve())
            if old is not None and check(old):
                own = ["the base version does not follow the format; transition not checked"]
            else:
                own = check_transition(old, text)
        errors += [f"{path}: {error}" for error in own]
    if base is not None:
        present = {p.resolve() for p in files}
        for old_path, old in sorted(base.items()):
            if old_path not in present:
                errors += [f"{old_path}: {e}" for e in check_transition(old, None)]
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check_parser = sub.add_parser("check", help="check every ticket under the given paths")
    check_parser.add_argument("paths", nargs="+", type=Path)
    check_parser.add_argument(
        "--base", help="also check each ticket's state transition from this revision"
    )
    list_parser = sub.add_parser("list", help="list tickets, optionally by status")
    list_parser.add_argument("root", type=Path)
    list_parser.add_argument("--status", choices=STATUSES)
    args = parser.parse_args()

    files = []
    for path in getattr(args, "paths", None) or [args.root]:
        files += sorted(path.rglob("*.md")) if path.is_dir() else [path]
    files = [f for f in files if f.name != "README.md"]
    if args.command == "check":
        try:
            base = None
            if args.base:
                base = base_for(args.paths, args.base)
        except TicketError as error:
            print(f"FAIL {error}")
            return 1
        errors = check_files(files, base=base)
        for error in errors:
            print(f"FAIL {error}")
        failed = len({error.split(": ", 1)[0] for error in errors})
        print(f"tickets checked {len(files)}, failed {failed}")
        return 1 if errors or not files else 0
    for path in files:
        try:
            data, _ = parse(path.read_text(encoding="utf-8"))
        except TicketError as error:
            print(f"FAIL {path}: {error}")
            continue
        if args.status is None or data.get("status") == args.status:
            print(f"{data.get('status')}\t{data.get('kind')}\t{data.get('id')}\t{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
