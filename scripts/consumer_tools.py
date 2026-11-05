"""Transport-neutral, read-only MCP tool definitions and dispatch.

The host adapter supplies MCP transport/lifecycle; this module never executes
scientific calls or user code. It reads one verified consumption snapshot.
"""

from __future__ import annotations

import base64
import json
import re

from capability_query import REQUEST_SCHEMA
from query import Consumer, encode, sha

TOOL_PREFIX = "scirel_"


def is_error_result(result):
    return result.get("outcome") not in {"ok", "match", "near_miss", "no_candidates"}


def tools():
    query = {
        key: dict(value) for key, value in REQUEST_SCHEMA["properties"].items() if key != "schema"
    }
    query["limit"]["default"] = 5
    pins = {
        key: {"type": "string", "minLength": 64, "maxLength": 64, "pattern": "^[0-9a-f]{64}$"}
        for key in ("expected_snapshot_sha256", "expected_wheel_sha256")
    }
    query.update(pins)
    query["cursor"] = {"type": "string", "maxLength": 4096}
    query["max_bytes"] = {"type": "integer", "minimum": 4096, "maximum": 65536, "default": 32768}
    empty = {"type": "object", "additionalProperties": False, "properties": {}}
    definitions = [
        (
            "describe",
            "Describe the bound public snapshot, query contract and runtime requirements.",
            {**empty, "properties": {"expected_wheel_sha256": pins["expected_wheel_sha256"]}},
        ),
        (
            "browse",
            "Browse bounded public discovery cards in stable asset ID order; filters are metadata constraints.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(pins),
                "properties": {key: value for key, value in query.items() if key != "q"},
            },
        ),
        (
            "search",
            "Recall bounded lexical candidates, with hit reasons and conflicts. Recall is not scientific applicability.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": list(pins),
                "properties": query,
            },
        ),
        (
            "get",
            "Read one complete original public contract with its bound path and hash. Check units, model, boundary and evidence before use.",
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["asset_id", *pins],
                "properties": {**pins, "asset_id": {"type": "string", "minLength": 1}},
            },
        ),
    ]
    return [
        dict(
            name=TOOL_PREFIX + name,
            description=description,
            inputSchema=schema,
            annotations={
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        )
        for name, description, schema in definitions
    ]


def call_tool(root, name, arguments=None):
    """Return a consumer JSON envelope, independent of stdio/HTTP transport."""
    definitions = {item["name"]: item for item in tools()}
    if name not in definitions:
        return {
            "schema": "scirel.consumer-response",
            "command": name,
            "outcome": "invalid_request",
            "error": "unknown tool",
        }
    args = (
        {} if arguments is None else dict(arguments) if isinstance(arguments, dict) else arguments
    )
    schema = definitions[name]["inputSchema"]
    if (
        not isinstance(args, dict)
        or set(args) - set(schema["properties"])
        or any(key not in args for key in schema.get("required", []))
    ):
        return {
            "schema": "scirel.consumer-response",
            "command": name,
            "outcome": "invalid_request",
            "error": "unknown or missing argument",
        }
    for key, value in args.items():
        definition = schema["properties"][key]
        invalid = "enum" in definition and value not in definition["enum"]
        if definition.get("type") == "string":
            invalid |= not isinstance(value, str)
            if isinstance(value, str):
                invalid |= (
                    not definition.get("minLength", 0)
                    <= len(value)
                    <= definition.get("maxLength", 10000)
                )
                if "pattern" in definition:
                    invalid |= re.fullmatch(definition["pattern"], value) is None
        elif definition.get("type") == "integer":
            invalid |= type(value) is not int
            if type(value) is int:
                invalid |= (
                    not definition.get("minimum", 0) <= value <= definition.get("maximum", 10**12)
                )
        if invalid:
            return {
                "schema": "scirel.consumer-response",
                "command": name,
                "outcome": "invalid_request",
                "error": "invalid argument: " + key,
            }
    try:
        consumer = Consumer(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {
            "schema": "scirel.consumer-response",
            "command": name,
            "outcome": "metadata_error",
            "error": str(error),
        }
    command = name.removeprefix(TOOL_PREFIX)
    expected_snapshot = args.pop("expected_snapshot_sha256", None)
    expected_wheel = args.pop("expected_wheel_sha256", None)
    if (
        expected_snapshot is not None
        and expected_snapshot != consumer.identity["snapshot_sha256"]
        or expected_wheel is not None
        and expected_wheel != consumer.identity["runtime"]["wheel_sha256"]
    ):
        return consumer.envelope(
            command,
            outcome="identity_mismatch",
            error="requested snapshot or wheel differs; rediscover and explicitly select a matching runtime",
        )
    try:
        if command == "describe":
            return consumer.describe()
        if command in ("browse", "search"):
            cursor, max_bytes = args.pop("cursor", ""), args.pop("max_bytes", 32768)
            args.setdefault("limit", 5)
            query_digest = sha(
                encode({"command": command, **{k: v for k, v in args.items() if k != "offset"}})
            )
            if cursor:
                try:
                    decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                    if (
                        decoded["snapshot"] != consumer.identity["snapshot_sha256"]
                        or decoded["query"] != query_digest
                        or "offset" in args
                        or type(decoded["offset"]) is not int
                        or decoded["offset"] < 0
                    ):
                        raise ValueError("cursor scope mismatch")
                    args["offset"] = decoded["offset"]
                except (ValueError, KeyError, TypeError) as error:
                    return consumer.envelope(
                        command, outcome="invalid_request", error="invalid cursor: " + str(error)
                    )
            result = consumer.query(command, **args)
            page = result["result"]
            original_count = len(page["items"])

            def continuation():
                offset = page["offset"] + len(page["items"])
                page["next_offset"] = offset if offset < page["total"] else None
                result["next_cursor"] = (
                    base64.urlsafe_b64encode(
                        encode(
                            {
                                "snapshot": consumer.identity["snapshot_sha256"],
                                "query": query_digest,
                                "offset": offset,
                            }
                        )
                    ).decode()
                    if page["next_offset"] is not None
                    else None
                )
                result["returned"] = len(page["items"])
                result["truncated"] = len(page["items"]) < original_count
                result["truncation_reason"] = (
                    "response_byte_budget" if result["truncated"] else None
                )

            continuation()
            while (
                len(json.dumps(result, ensure_ascii=False).encode()) + 100 > max_bytes
                and page["items"]
            ):
                page["items"].pop()
                continuation()
            if original_count and not page["items"]:
                return consumer.envelope(
                    command,
                    outcome="response_too_large",
                    error="one complete candidate card exceeds max_bytes; increase the budget or refine filters",
                    max_bytes=max_bytes,
                )
            result["response_bytes"] = len(json.dumps(result, ensure_ascii=False).encode())
            # Reserve framing overhead inside the declared JSON budget.
            if result["response_bytes"] + 100 > max_bytes:
                return consumer.envelope(
                    command,
                    outcome="response_too_large",
                    error="response envelope exceeds byte budget",
                )
            return result
        if command == "get":
            return consumer.get(args["asset_id"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        return consumer.envelope(command, outcome="metadata_error", error=str(error))
