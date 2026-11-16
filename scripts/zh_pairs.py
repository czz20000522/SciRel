"""Check and record the Chinese reader records against the contracts they translate.

`tools/docs/zh/*.json` holds Chinese translations of contract prose. Its only
binding used to be one `source_sha256` per record: it proves some bytes were
seen, cannot say which field drifted, and forces a whole-file rewrite for a
one-word change. This tool keeps a per-field pair in one sidecar instead:

    tools/docs/zh-pairing.json
    {"schema": "scirel.zh-pairing", "records": [
      {"asset_id": "...", "fields": {"definition": {"en": "...", "zh": "..."}}},
      ...
    ]}

One record per line, sorted by asset id, so the file reviews as a table and
merges line by line. The sidecar sits beside the reader directory rather than
inside it: `scripts/capability_catalog.py` consumes every `tools/docs/zh/*.json`
as a reader bundle and rejects an unknown schema, so a file in there would break
the documentation and delivery builds.

Each section is one translated field of the record, hashed from its canonical
JSON on both sides. A contract edit moves the `en` hash and a translation edit
moves the `zh` hash, so a stale pair names the field instead of the file. The
record is the reviewable act of confirming the pair: a green run means "these
exact contents were confirmed together", never that the Chinese says the same
thing well.

The sidecar must cover every contract that has a Chinese record, and every record
must have a sidecar entry: a missing entry is a failure, not an "unmigrated" pass.
An earlier in-record `pairing` block is ignored rather than trusted, so removing
an entry cannot silently fall back to a weaker check. `title` is not paired: it is
a mechanical copy of the contract's own bilingual title and is checked by equality
instead; `source_sha256` is the superseded whole-file binding and is not paired.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PAIRING_SCHEMA = "scirel.zh-pairing"
PAIRING_VERSION = 1
SIDECAR = "tools/docs/zh-pairing.json"
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
    "family": ("family",),
}

# Fields the record copies verbatim from the contract's own bilingual value rather
# than translating. They are checked for equality, not hashed as a pair.
COPY_ONLY: dict[str, tuple[str, ...]] = {"title": ("title",)}


class _Missing:
    def __repr__(self) -> str:
        return "<absent>"


_MISSING = _Missing()


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


def load_contracts(root: Path) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    for directory in CONTRACT_DIRS:
        for path in sorted((root / directory).glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            documents[document["asset_id"]] = document
    return documents


def expected_fields(record: dict, document: dict) -> dict[str, dict[str, str]]:
    """Hashes for every section the record actually translates."""
    fields: dict[str, dict[str, str]] = {}
    for name, path in SECTIONS.items():
        if name not in record:
            continue
        english = contract_field(document, path)
        if english is _MISSING:
            continue
        fields[name] = {"en": digest(english), "zh": digest(record[name])}
    return fields


def zh_files(root: Path) -> list[Path]:
    return sorted(root.glob(ZH_GLOB))


def iter_records(root: Path):
    for path in zh_files(root):
        document = json.loads(path.read_text(encoding="utf-8"))
        for index, record in enumerate(document.get("records") or []):
            if isinstance(record, dict):
                yield path, document, index, record


def sidecar_path(root: Path) -> Path:
    return root / SIDECAR


def load_sidecar(root: Path) -> tuple[dict[str, dict], list[str]]:
    """Return (fields by asset id, errors). A missing sidecar is not an error."""
    path = sidecar_path(root)
    if not path.is_file():
        return {}, [f"{SIDECAR}: file is missing; run --write to record the pairs"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return {}, [f"{SIDECAR}: not valid JSON: {error}"]
    if not isinstance(document, dict) or document.get("schema") != PAIRING_SCHEMA:
        return {}, [f"{SIDECAR}: schema must be {PAIRING_SCHEMA!r}"]
    if document.get("version") != PAIRING_VERSION:
        return {}, [f"{SIDECAR}: version {document.get('version')!r} is not {PAIRING_VERSION}"]
    entries: dict[str, dict] = {}
    errors: list[str] = []
    for position, entry in enumerate(document.get("records") or []):
        if not isinstance(entry, dict):
            errors.append(f"{SIDECAR}: records[{position}] must be an object")
            continue
        asset = entry.get("asset_id")
        fields = entry.get("fields")
        if not isinstance(asset, str) or not asset:
            errors.append(f"{SIDECAR}: records[{position}] has no asset_id")
            continue
        if asset in entries:
            errors.append(f"{SIDECAR}: duplicate asset_id {asset}")
            continue
        if not isinstance(fields, dict) or not fields:
            errors.append(f"{SIDECAR} [{asset}]: fields must be a nonempty object")
            continue
        entries[asset] = fields
    return entries, errors


def validate_fields(where: str, recorded: dict, expected: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    drifted: list[str] = []
    unknown = sorted(set(recorded) - set(expected))
    if unknown:
        errors.append(f"{where}: pairs name fields the record no longer translates: {unknown}")
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
    return errors, drifted


def check(root: Path) -> tuple[list[str], list[str], dict[str, str]]:
    """Return (errors, notes, state). Every record needs a sidecar entry; there is no fallback."""
    contracts = load_contracts(root)
    entries, errors = load_sidecar(root)
    notes: list[str] = []
    state: dict[str, str] = {}
    records: dict[str, tuple[Path, dict]] = {}
    for path, _document, index, record in iter_records(root):
        asset = record.get("asset_id") or f"<record {index}>"
        if asset in records:
            errors.append(f"{path.name} [{asset}]: duplicate Chinese record")
            state[asset] = "duplicate-record"
            continue
        records[asset] = (path, record)

    for asset in sorted(set(contracts) - set(records)):
        errors.append(f"{SIDECAR}: contract {asset} has no Chinese record to pair with")
        state[asset] = "missing-record"
    for asset in sorted(set(records) - set(contracts)):
        errors.append(
            f"{records[asset][0].name} [{asset}]: no contract in {' or '.join(CONTRACT_DIRS)}"
        )
        state[asset] = "missing-contract"
    for asset in sorted(set(entries) - set(records)):
        errors.append(f"{SIDECAR}: pair for {asset} has no Chinese record")
        state[asset] = "orphaned"

    for asset, (path, record) in sorted(records.items()):
        contract = contracts.get(asset)
        if contract is None:
            continue
        where = f"{SIDECAR} [{asset}] (translation in {path.name})"
        recorded = entries.get(asset)
        if recorded is None:
            errors.append(
                f"{where}: no recorded pair; a missing entry is a failure, not an unmigrated pass. "
                f"Run --write after confirming the pair"
            )
            state[asset] = "unrecorded"
            continue
        for name, path_keys in COPY_ONLY.items():
            if name not in record:
                continue
            english = contract_field(contract, path_keys)
            if english is _MISSING:
                continue
            if record[name] != english:
                errors.append(
                    f"{where}: field '{name}' must copy the contract value exactly; it is a "
                    "bilingual identifier, not a translation"
                )
        expected = expected_fields(record, contract)
        section_errors, drifted = validate_fields(where, recorded, expected)
        errors.extend(section_errors)
        if drifted:
            state[asset] = "drift:" + ",".join(sorted(set(drifted)))
        elif state.get(asset) != "duplicate-record":
            state[asset] = "ok"
    return errors, notes, state


def render_sidecar(entries: dict[str, dict[str, dict[str, str]]]) -> str:
    lines = [
        "{",
        f' "schema": "{PAIRING_SCHEMA}",',
        f' "version": {PAIRING_VERSION},',
        ' "language": "zh-CN",',
        ' "records": [',
    ]
    assets = sorted(entries)
    for position, asset in enumerate(assets):
        entry = {"asset_id": asset, "fields": entries[asset]}
        comma = "," if position < len(assets) - 1 else ""
        lines.append("  " + json.dumps(entry, ensure_ascii=False) + comma)
    lines.extend([" ]", "}", ""])
    return "\n".join(lines)


def write(root: Path) -> tuple[list[str], bool]:
    """Recompute every record's pair and store the sidecar. Reader files are untouched."""
    contracts = load_contracts(root)
    entries: dict[str, dict[str, dict[str, str]]] = {}
    errors: list[str] = []
    for path, _document, index, record in iter_records(root):
        asset = record.get("asset_id")
        contract = contracts.get(asset)
        if contract is None:
            errors.append(f"{path.name} [{asset or index}]: no contract to pair against")
            continue
        entries[asset] = expected_fields(record, contract)
    for asset in sorted(set(contracts) - set(entries)):
        errors.append(f"contract {asset} has no Chinese record, so it has no pair to record")
    if errors:
        return errors, False
    rendered = render_sidecar(entries)
    target = sidecar_path(root)
    previous = target.read_text(encoding="utf-8") if target.is_file() else None
    if previous != rendered:
        target.write_text(rendered, encoding="utf-8")
        return [], True
    return [], False


def format_list(states: dict[str, str]) -> str:
    lines = [f"{'status':16s} asset"]
    for asset in sorted(states):
        lines.append(f"{states[asset]:16s} {asset}")
    return "\n".join(lines)


def count_records(root: Path) -> int:
    return sum(1 for _ in iter_records(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument(
        "--write", action="store_true", help="recompute and store the sidecar for every record"
    )
    parser.add_argument(
        "--list", action="store_true", help="print the pairing state of every record"
    )
    args = parser.parse_args(argv)

    root = Path(args.repo).resolve()
    if not zh_files(root):
        print(f"FAIL: no Chinese reader records found under {root / ZH_GLOB}")
        return 2

    if args.write:
        write_errors, changed = write(root)
        print(f"recorded: {SIDECAR}" if changed else "recorded: nothing to change")
        # Re-read what was written: the pre-write drift is not a failure of this run.
        errors, _notes, _state = check(root)
        errors = write_errors + errors
        if errors:
            print(f"\nFAIL: {len(errors)} problem(s)")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"\nOK: {count_records(root)} records carry a fresh pair")
        return 0

    errors, notes, state = check(root)
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
