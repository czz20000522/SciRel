"""Read an existing JSON record by literal JSON Pointer; never infer science or status."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def resolve(document: object, pointer: str) -> object:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON Pointer, e.g. /milestones/M1/state")
    value = document
    for raw in pointer[1:].split("/"):
        # Invalid escape sequences must not silently select a different field.
        check = raw.replace("~0", "").replace("~1", "")
        if "~" in check:
            raise ValueError("Invalid JSON Pointer escape")
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if key not in value:
                raise ValueError(f"Missing field at {pointer!r}; inspect --shape")
            value = value[key]
        elif isinstance(value, list):
            if not key.isascii() or not key.isdecimal() or (len(key) > 1 and key[0] == "0"):
                raise ValueError("Array selector must be a canonical nonnegative index")
            index = int(key)
            if index >= len(value):
                raise ValueError(f"Array index out of range at {pointer!r}")
            value = value[index]
        else:
            raise ValueError(f"Cannot traverse scalar at {pointer!r}")
    return value


def shape(value: object, depth: int, limit: int) -> dict:
    kind = ("object" if isinstance(value, dict) else "array" if isinstance(value, list)
            else "null" if value is None else "boolean" if isinstance(value, bool)
            else "number" if isinstance(value, (int, float)) else "string")
    result = {"type": kind}
    if isinstance(value, (dict, list)):
        result["count"] = len(value)
        if depth > 0:
            if isinstance(value, dict):
                keys = list(value)[:limit]
                result["fields"] = {key: shape(value[key], depth - 1, limit) for key in keys}
            else:
                result["items"] = [shape(v, depth - 1, limit) for v in value[:limit]]
            result["omitted"] = max(0, len(value) - limit)
    return result


def query(path: Path, pointers: list[str], *, expected_sha256: str | None = None,
          expected_schema: str | None = None, include_shape: bool = False,
          depth: int = 2, limit: int = 20) -> dict:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Material changed: SHA-256 does not match the pinned record")
    document = json.loads(raw)
    schema = document.get("schema") if isinstance(document, dict) else None
    if expected_schema is not None and schema != expected_schema:
        raise ValueError(f"Schema mismatch: observed {schema!r}")
    result = {"path": str(path.resolve()), "bytes": len(raw), "sha256": digest,
              "declared_schema": schema,
              "values": {p: resolve(document, p) for p in pointers}}
    if include_shape:
        result["shape"] = shape(document, depth, limit)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--pointer", action="append", default=[])
    parser.add_argument("--shape", action="store_true")
    parser.add_argument("--expect-sha256")
    parser.add_argument("--expect-schema")
    parser.add_argument("--depth", type=int, choices=range(0, 5), default=2)
    parser.add_argument("--limit", type=int, choices=range(1, 101), default=20)
    parser.add_argument("--max-output-bytes", type=int, default=16384)
    args = parser.parse_args()
    try:
        if args.max_output_bytes < 256:
            raise ValueError("max-output-bytes must be at least 256")
        result = query(args.path, args.pointer, expected_sha256=args.expect_sha256,
                       expected_schema=args.expect_schema, include_shape=args.shape or not args.pointer,
                       depth=args.depth, limit=args.limit)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if len(output.encode("utf-8")) > args.max_output_bytes:
            raise ValueError("Projection exceeds output budget; select a narrower pointer/depth/limit")
        print(output)
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error), "status": "query_failed"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
