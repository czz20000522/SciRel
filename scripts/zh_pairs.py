"""Check and record the Chinese reader records against the contracts they translate.

`tools/docs/zh/*.json` holds Chinese translations of contract prose. Until now the
only binding was one `source_sha256` per record: it proves *some* bytes were seen,
cannot say which field drifted, and forces a whole-file rewrite for a one-word
change. This tool records a per-field pair instead:

    "pairing": {"version": 1, "sections": {"definition": {"en": "...", "zh": "..."}}}

Each section is one translated field of the record, hashed from its canonical JSON
on both sides. A contract edit moves the `en` hash and a translation edit moves the
`zh` hash, so a stale pair names the field instead of the file. The record is the
reviewable act of confirming the pair: a green run means "these exact contents were
confirmed together", never that the Chinese says the same thing well.

Sections absent from a record are not expected; a record without a `pairing` block
is treated as v1 and passes with an explicit note, so the switch can land before
the data migration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PAIRING_SCHEMA = "scirel.zh-pairing"
PAIRING_VERSION = 1
ZH_GLOB = "tools/docs/zh/*.json"
CONTRACT_DIRS = ("catalog/examples", "catalog/review/examples")
INDENT = 1

# section name -> path inside the contract document.
SECTIONS: dict[str, tuple[str, ...]] = {
    "summary": ("summary",),
    "definition": ("identity", "definition"),
    "model": ("identity", "model"),
    "assumptions": ("identity", "assumptions"),
    "boundary": ("identity", "boundary"),
    "inputs": ("inputs",),
    "outputs": ("outputs",),
    "applicability": ("applicability",),
    "failure_semantics": ("failure_semantics",),
    "example": ("example",),
    "verification": ("verification",),
}
RESERVED = {"asset_id", "source_sha256", "pairing"}


def digest(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def contract_field(document: dict, path: tuple[str, ...]):
    node = document
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return _MISSING
        node = node[key]
    return node


class _Missing:
    def __repr__(self) -> str:
        return "<absent>"


_MISSING = _Missing()


def load_contracts(root: Path) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    for directory in CONTRACT_DIRS:
        for path in sorted((root / directory).glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            documents[document["asset_id"]] = document
    return documents


def pairing_sections(record: dict, document: dict) -> dict[str, dict[str, str]]:
    """Hashes for every section the record actually translates."""
    sections: dict[str, dict[str, str]] = {}
    for name, path in SECTIONS.items():
        if name not in record:
            continue
        english = contract_field(document, path)
        if english is _MISSING:
            continue
        sections[name] = {"en": digest(english), "zh": digest(record[name])}
    return sections


def zh_files(root: Path) -> list[Path]:
    return sorted(root.glob(ZH_GLOB))


def iter_records(root: Path):
    for path in zh_files(root):
        document = json.loads(path.read_text(encoding="utf-8"))
        for index, record in enumerate(document.get("records") or []):
            if isinstance(record, dict):
                yield path, document, index, record


def check(root: Path) -> tuple[list[str], list[str], dict[str, str]]:
    """Return (errors, notes, state) where state maps asset id to a short status."""
    contracts = load_contracts(root)
    errors: list[str] = []
    notes: list[str] = []
    state: dict[str, str] = {}
    for path, _document, index, record in iter_records(root):
        asset = record.get("asset_id") or f"<record {index}>"
        relative = path.relative_to(root).as_posix()
        where = f"{relative} [{asset}]"
        contract = contracts.get(asset)
        if contract is None:
            errors.append(f"{where}: no contract in {' or '.join(CONTRACT_DIRS)} for this record")
            state[asset] = "missing-contract"
            continue
        pairing = record.get("pairing")
        if pairing is None:
            notes.append(f"{where}: v1 record without a pairing block; accepted as unmigrated")
            state[asset] = "v1"
            continue
        if not isinstance(pairing, dict):
            errors.append(f"{where}: pairing must be an object")
            state[asset] = "malformed"
            continue
        if pairing.get("version") != PAIRING_VERSION:
            errors.append(
                f"{where}: pairing version {pairing.get('version')!r} is not {PAIRING_VERSION}"
            )
            state[asset] = "malformed"
            continue
        recorded = pairing.get("sections")
        if not isinstance(recorded, dict) or not recorded:
            errors.append(f"{where}: pairing has no sections")
            state[asset] = "malformed"
            continue
        expected = pairing_sections(record, contract)
        unknown = sorted(set(recorded) - set(expected))
        if unknown:
            errors.append(
                f"{where}: pairing names sections the record no longer translates: {unknown}"
            )
        drifted: list[str] = []
        for name, hashes in expected.items():
            if name not in recorded:
                errors.append(
                    f"{where}: field '{name}' has no recorded hash; re-run --write after confirming it"
                )
                drifted.append(name)
                continue
            entry = recorded[name]
            if not isinstance(entry, dict) or set(entry) != {"en", "zh"}:
                errors.append(f"{where}: field '{name}' entry must be an object with en and zh")
                drifted.append(name)
                continue
            if entry["en"] != hashes["en"]:
                errors.append(
                    f"{where}: contract field '{name}' changed since the pair was confirmed "
                    f"(recorded {entry['en']}, now {hashes['en']})"
                )
                drifted.append(name)
            if entry["zh"] != hashes["zh"]:
                errors.append(
                    f"{where}: Chinese text of field '{name}' changed without re-recording the pair "
                    f"(recorded {entry['zh']}, now {hashes['zh']})"
                )
                drifted.append(name)
        state[asset] = "drift:" + ",".join(sorted(set(drifted))) if drifted else "ok"
    return errors, notes, state


def write(root: Path) -> tuple[list[str], list[str]]:
    """Recompute and store every record's pairing block, preserving file formatting."""
    contracts = load_contracts(root)
    errors: list[str] = []
    changed: list[str] = []
    for path in zh_files(root):
        document = json.loads(path.read_text(encoding="utf-8"))
        touched = False
        for record in document.get("records") or []:
            if not isinstance(record, dict):
                continue
            asset = record.get("asset_id")
            contract = contracts.get(asset)
            if contract is None:
                errors.append(f"{path.name} [{asset}]: no contract to pair against")
                continue
            record["pairing"] = {
                "schema": PAIRING_SCHEMA,
                "version": PAIRING_VERSION,
                "sections": pairing_sections(record, contract),
            }
            touched = True
        if touched:
            rendered = json.dumps(document, ensure_ascii=False, indent=INDENT) + "\n"
            if rendered != path.read_text(encoding="utf-8"):
                path.write_text(rendered, encoding="utf-8")
                changed.append(path.relative_to(root).as_posix())
    return errors, changed


def format_list(states: dict[str, str]) -> str:
    lines = [f"{'status':12s} asset"]
    for asset in sorted(states):
        lines.append(f"{states[asset]:12s} {asset}")
    return "\n".join(lines)


def count_records(root: Path) -> int:
    return sum(1 for _ in iter_records(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument(
        "--write", action="store_true", help="recompute and store the pairing block of every record"
    )
    parser.add_argument(
        "--list", action="store_true", help="print the pairing state of every record"
    )
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    if not zh_files(root):
        print(f"FAIL: no Chinese reader records found under {root / ZH_GLOB}")
        return 2

    errors, notes, state = check(root)
    if args.write:
        write_errors, changed = write(root)
        for relative in changed:
            print(f"recorded: {relative}")
        if not changed:
            print("recorded: nothing to change")
        # Re-read what was written: the pre-write drift is not a failure of this run.
        errors, notes, state = check(root)
        errors = write_errors + errors
        if errors:
            print(f"\nFAIL: {len(errors)} problem(s)")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"\nOK: {count_records(root)} records carry a fresh pairing block")
        return 0

    if args.list:
        print(format_list(state))
        print()
        print(f"records: {len(state)} | errors: {len(errors)} | v1 notes: {len(notes)}")
        return 1 if errors else 0

    for note in notes:
        print(f"note: {note}")
    if errors:
        print(f"\nFAIL: {len(errors)} problem(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: {len(state)} Chinese records pair with their contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
