#!/usr/bin/env python3
"""Parse and check human-review tickets.

A ticket is one Markdown file with a front matter block. The format and state machine are in
``docs/maintainer/supply-pipeline.md`` section 7. This module uses the standard library only.

Front matter values are a deliberately small subset of YAML: ``key: value`` per line, where a
value is ``null``, an integer, a bare or quoted string, a flow list such as ``[A, B]``, or JSON
(a list or mapping). A ``#`` outside quotes starts a comment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

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
        agreeing = [
            d for d in decisions if isinstance(d, dict) and d.get("option") == data["resolution"]
        ]
        if isinstance(required, int) and len(agreeing) < required:
            errors.append(
                f"resolution needs {required} agreeing reviewer decisions; found {len(agreeing)}"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check_parser = sub.add_parser("check", help="check every ticket under the given paths")
    check_parser.add_argument("paths", nargs="+", type=Path)
    list_parser = sub.add_parser("list", help="list tickets, optionally by status")
    list_parser.add_argument("root", type=Path)
    list_parser.add_argument("--status", choices=STATUSES)
    args = parser.parse_args()

    files = []
    for path in getattr(args, "paths", None) or [args.root]:
        files += sorted(path.rglob("*.md")) if path.is_dir() else [path]
    files = [f for f in files if f.name != "README.md"]
    if args.command == "check":
        failed = 0
        for path in files:
            errors = check(path.read_text(encoding="utf-8"))
            failed += bool(errors)
            for error in errors:
                print(f"FAIL {path}: {error}")
        print(f"tickets checked {len(files)}, passed {len(files) - failed}, failed {failed}")
        return 1 if failed or not files else 0
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
