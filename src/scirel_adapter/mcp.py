"""SDK-free MCP adapter core over a pinned SciRel catalog."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import copy
import hashlib
import importlib
from importlib import metadata
import inspect
import json
import math
from pathlib import Path
from typing import Any


RELEASE_SCHEMA = "scirel.catalog-release.v1"
RESPONSE_SCHEMA = "scirel.thin-mcp-response.v1"
MAX_PAGE_SIZE = 100
MAX_READ_ASSETS = 20


class ThinMcpAdapterError(ValueError):
    """A stable adapter-boundary failure that transports can map to their protocol."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ThinMcpAdapterError(code, message)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class ThinMcpAdapter:
    """Translate a verified catalog snapshot into bounded adapter operations."""

    def __init__(
        self,
        catalog_root: str | Path,
        *,
        expected_root_digest: str | None = None,
    ) -> None:
        self._root = Path(catalog_root).resolve()
        self._release = self._load_json(self._root / "release.json", "invalid_snapshot")
        self._verify_release(expected_root_digest)
        self._routes = self._load_projection("routes")
        self._summaries = self._load_projection("summaries")
        self._routes_by_id = self._index_projection(self._routes, "route")
        self._summaries_by_id = self._index_projection(self._summaries, "summary")
        if set(self._routes_by_id) != set(self._summaries_by_id):
            _fail("invalid_snapshot", "route and summary asset sets differ")
        expected_count = self._release["coverage"]["included_asset_count"]
        if len(self._routes_by_id) != expected_count:
            _fail("invalid_snapshot", "catalog coverage count differs from projections")

    @staticmethod
    def _load_json(path: Path, code: str) -> dict[str, Any]:
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise ThinMcpAdapterError(code, f"cannot read {path}: {error}") from error
        return ThinMcpAdapter._parse_json(payload, str(path), code)

    @staticmethod
    def _parse_json(payload: bytes, location: str, code: str) -> dict[str, Any]:
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ThinMcpAdapterError(code, f"cannot parse {location}: {error}") from error
        if not isinstance(value, dict):
            _fail(code, f"{location} must contain a JSON object")
        return value

    def _partition_path(self, relative: Any) -> Path:
        if not isinstance(relative, str) or not relative:
            _fail("invalid_snapshot", "partition path must be a non-empty string")
        candidate = (self._root / relative).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError:
            _fail("invalid_snapshot", f"partition path escapes catalog root: {relative}")
        return candidate

    def _verify_release(self, expected_root_digest: str | None) -> None:
        release = self._release
        if release.get("schema") != RELEASE_SCHEMA:
            _fail("invalid_snapshot", f"release schema must be {RELEASE_SCHEMA}")
        declared_digest = release.get("root_digest")
        unsigned = dict(release)
        unsigned.pop("root_digest", None)
        actual_digest = _digest(_canonical_json(unsigned))
        if declared_digest != actual_digest:
            _fail("snapshot_mismatch", "catalog release root digest is invalid")
        if expected_root_digest is not None and expected_root_digest != declared_digest:
            _fail("snapshot_mismatch", "catalog release does not match expected root digest")

        for field in ("catalog_id", "release_version"):
            if not isinstance(release.get(field), str) or not release[field]:
                _fail("invalid_snapshot", f"catalog release {field} is invalid")
        coverage = release.get("coverage")
        if (
            not isinstance(coverage, dict)
            or not isinstance(coverage.get("included_asset_count"), int)
            or isinstance(coverage.get("included_asset_count"), bool)
            or coverage["included_asset_count"] < 1
        ):
            _fail("invalid_snapshot", "catalog release coverage is invalid")
        partitions = release.get("partitions")
        if not isinstance(partitions, list) or not partitions:
            _fail("invalid_snapshot", "catalog release has no partitions")
        self._partition_entries: dict[str, dict[str, Any]] = {}
        for entry in partitions:
            if not isinstance(entry, dict):
                _fail("invalid_snapshot", "partition entry must be an object")
            relative = entry.get("path")
            path = self._partition_path(relative)
            if relative in self._partition_entries:
                _fail("invalid_snapshot", f"duplicate partition path: {relative}")
            try:
                payload = path.read_bytes()
            except OSError as error:
                raise ThinMcpAdapterError(
                    "snapshot_mismatch", f"cannot read catalog partition {relative}: {error}"
                ) from error
            if entry.get("bytes") != len(payload) or entry.get("sha256") != _digest(payload):
                _fail("snapshot_mismatch", f"catalog partition differs: {relative}")
            self._partition_entries[relative] = entry

    def _read_bound_partition(self, relative: str) -> bytes:
        entry = self._partition_entries.get(relative)
        if entry is None:
            _fail("invalid_snapshot", f"partition is not bound by the release: {relative}")
        path = self._partition_path(relative)
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise ThinMcpAdapterError(
                "snapshot_mismatch", f"cannot read catalog partition {relative}: {error}"
            ) from error
        if entry.get("bytes") != len(payload) or entry.get("sha256") != _digest(payload):
            _fail("snapshot_mismatch", f"catalog partition differs: {relative}")
        return payload

    def _load_projection(self, name: str) -> list[dict[str, Any]]:
        paths = sorted(
            relative
            for relative in self._partition_entries
            if relative.startswith(f"{name}/") and relative.endswith(".jsonl")
        )
        if not paths:
            _fail("invalid_snapshot", f"catalog has no {name} projection")
        records = []
        for relative in paths:
            try:
                lines = self._read_bound_partition(relative).decode("utf-8").splitlines()
            except UnicodeDecodeError as error:
                raise ThinMcpAdapterError(
                    "invalid_snapshot", f"invalid UTF-8 in {relative}: {error}"
                ) from error
            for line_number, line in enumerate(lines, start=1):
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ThinMcpAdapterError(
                        "invalid_snapshot",
                        f"invalid {name} JSON at {relative}:{line_number}: {error}",
                    ) from error
                if not isinstance(record, dict):
                    _fail("invalid_snapshot", f"{relative}:{line_number} must be an object")
                records.append(record)
        return records

    @staticmethod
    def _index_projection(
        records: list[dict[str, Any]], projection: str
    ) -> dict[str, dict[str, Any]]:
        indexed = {}
        for record in records:
            asset_id = record.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                _fail("invalid_snapshot", f"{projection} record has no asset_id")
            if asset_id in indexed:
                _fail("invalid_snapshot", f"duplicate {projection} asset_id: {asset_id}")
            indexed[asset_id] = record
        return indexed

    def _catalog_binding(self) -> dict[str, Any]:
        return {
            "catalog_id": self._release["catalog_id"],
            "release_version": self._release["release_version"],
            "root_digest": self._release["root_digest"],
            "coverage": copy.deepcopy(self._release["coverage"]),
        }

    def _response(self, operation: str, **payload: Any) -> dict[str, Any]:
        return {
            "schema": RESPONSE_SCHEMA,
            "operation": operation,
            "catalog": self._catalog_binding(),
            **payload,
        }

    @staticmethod
    def _validate_string_keys(
        value: Mapping[Any, Any], *, code: str, label: str
    ) -> None:
        if not all(isinstance(key, str) for key in value):
            _fail(code, f"{label} names must be strings")

    @staticmethod
    def _validate_exact_keys(
        request: Mapping[str, Any], required: set[str], allowed: set[str]
    ) -> None:
        ThinMcpAdapter._validate_string_keys(
            request, code="invalid_request", label="request field"
        )
        missing = sorted(required - set(request))
        unknown = sorted(set(request) - allowed)
        if missing:
            _fail("invalid_request", f"missing request fields: {', '.join(missing)}")
        if unknown:
            _fail("invalid_request", f"unknown request fields: {', '.join(unknown)}")

    @staticmethod
    def _matches(route: dict[str, Any], filters: Mapping[str, Any]) -> bool:
        allowed = {"kind", "taxonomy", "relation", "direction", "output", "facets"}
        unknown = sorted(set(filters) - allowed)
        if unknown:
            _fail("invalid_request", f"unknown discovery filters: {', '.join(unknown)}")
        for field in ("kind", "relation", "direction"):
            expected = filters.get(field)
            if expected is not None:
                if not isinstance(expected, str):
                    _fail("invalid_request", f"discovery filter {field} must be a string")
                if route.get(field) != expected:
                    return False
        taxonomy = filters.get("taxonomy")
        if taxonomy is not None:
            if not isinstance(taxonomy, str):
                _fail("invalid_request", "discovery filter taxonomy must be a string")
            if taxonomy not in route.get("taxonomy", []):
                return False
        output = filters.get("output")
        if output is not None:
            if not isinstance(output, str):
                _fail("invalid_request", "discovery filter output must be a string")
            if output not in {
                item.get("name") for item in route.get("outputs", []) if isinstance(item, dict)
            }:
                return False
        facets = filters.get("facets")
        if facets is not None:
            if not isinstance(facets, Mapping) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in facets.items()
            ):
                _fail("invalid_request", "discovery facets must map strings to strings")
            route_facets = route.get("facets", {})
            if any(route_facets.get(key) != value for key, value in facets.items()):
                return False
        return True

    def discover(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        cursor: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            _fail("invalid_request", "cursor must be a nonnegative integer")
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or not 1 <= limit <= MAX_PAGE_SIZE
        ):
            _fail("invalid_request", f"limit must be between 1 and {MAX_PAGE_SIZE}")
        if filters is None:
            filters = {}
        if not isinstance(filters, Mapping):
            _fail("invalid_request", "filters must be an object")
        self._validate_string_keys(
            filters, code="invalid_request", label="discovery filter"
        )
        matches = [route for route in self._routes if self._matches(route, filters)]
        page = matches[cursor : cursor + limit]
        next_cursor = cursor + len(page)
        exhausted = next_cursor >= len(matches)
        return self._response(
            "catalog.discover",
            items=copy.deepcopy(page),
            cursor=cursor,
            next_cursor=None if exhausted else next_cursor,
            exhausted=exhausted,
        )

    def _asset_ids(self, asset_ids: Any) -> list[str]:
        if (
            not isinstance(asset_ids, Sequence)
            or isinstance(asset_ids, (str, bytes))
            or not 1 <= len(asset_ids) <= MAX_READ_ASSETS
        ):
            _fail(
                "invalid_request",
                f"asset_ids must contain between 1 and {MAX_READ_ASSETS} IDs",
            )
        result = []
        for asset_id in asset_ids:
            if not isinstance(asset_id, str) or not asset_id:
                _fail("invalid_request", "asset_ids must contain non-empty strings")
            if asset_id in result:
                _fail("invalid_request", f"duplicate asset_id: {asset_id}")
            if asset_id not in self._routes_by_id:
                _fail("asset_not_found", f"asset is not in the catalog: {asset_id}")
            result.append(asset_id)
        return result

    def _document(self, asset_id: str) -> dict[str, Any]:
        asset_id = self._asset_ids([asset_id])[0]
        exact = self._routes_by_id[asset_id].get("exact_record")
        if not isinstance(exact, dict) or set(exact) != {"path"}:
            _fail("invalid_snapshot", f"route has an invalid exact record: {asset_id}")
        relative = exact["path"]
        if relative not in self._partition_entries or not relative.startswith("records/"):
            _fail("invalid_snapshot", f"record is not bound by the release: {asset_id}")
        document = self._parse_json(
            self._read_bound_partition(relative), relative, "invalid_snapshot"
        )
        if document.get("asset_id") != asset_id:
            _fail("invalid_snapshot", f"record asset_id differs for {asset_id}")
        return document

    def read_assets(
        self, asset_ids: Sequence[str], *, detail: str = "summary"
    ) -> dict[str, Any]:
        selected = self._asset_ids(asset_ids)
        if detail == "summary":
            items = [copy.deepcopy(self._summaries_by_id[asset_id]) for asset_id in selected]
        elif detail == "document":
            items = [self._document(asset_id) for asset_id in selected]
        else:
            _fail("invalid_request", "detail must be summary or document")
        return self._response("asset.read", detail=detail, items=items)

    def _installed_version(self) -> str:
        try:
            return metadata.version("scirel")
        except metadata.PackageNotFoundError as error:
            raise ThinMcpAdapterError(
                "callable_mismatch", "installed SciRel distribution version is unavailable"
            ) from error

    def _resolve_callable(
        self, asset_id: str, document: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], Any, inspect.Signature]:
        if document is None:
            document = self._document(asset_id)
        expected_version = document["version"]["implementation_version"]
        actual_version = self._installed_version()
        if actual_version != expected_version:
            _fail(
                "callable_mismatch",
                f"SciRel version differs: expected {expected_version}, got {actual_version}",
            )
        python_api = document["public_api"]["python"]
        module_name = python_api.get("module")
        symbol = python_api.get("symbol")
        if (
            not isinstance(module_name, str)
            or not module_name.startswith("scirel.")
            or not all(part.isidentifier() for part in module_name.split("."))
            or not isinstance(symbol, str)
            or not symbol.isidentifier()
        ):
            _fail("invalid_snapshot", f"documented Python binding is invalid for {asset_id}")
        try:
            module = importlib.import_module(module_name)
            function = getattr(module, symbol)
        except (ImportError, AttributeError) as error:
            raise ThinMcpAdapterError(
                "callable_mismatch", f"documented callable is unavailable for {asset_id}"
            ) from error
        if not callable(function):
            _fail("callable_mismatch", f"documented symbol is not callable for {asset_id}")
        signature = inspect.signature(function)
        actual_signature = f"{python_api['symbol']}{signature}"
        if actual_signature != python_api["signature"]:
            _fail("callable_mismatch", f"runtime signature differs for {asset_id}")
        self._validate_input_binding(asset_id, document, signature)
        return document, function, signature

    @staticmethod
    def _uses_task_graph_input_mapping(
        document: Mapping[str, Any], signature: inspect.Signature
    ) -> bool:
        if document.get("kind") != "task_graph":
            return False
        port_names = {port["name"] for port in document["inputs"]}
        parameter = signature.parameters.get("inputs")
        return parameter is not None and "inputs" not in port_names

    @classmethod
    def _validate_input_binding(
        cls,
        asset_id: str,
        document: Mapping[str, Any],
        signature: inspect.Signature,
    ) -> None:
        if cls._uses_task_graph_input_mapping(document, signature):
            parameter = signature.parameters["inputs"]
            if parameter.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                _fail(
                    "callable_mismatch",
                    f"TaskGraph inputs mapping is not keyword-bindable for {asset_id}",
                )
            try:
                signature.bind(inputs={})
            except TypeError as error:
                raise ThinMcpAdapterError(
                    "callable_mismatch",
                    f"TaskGraph inputs mapping cannot bind for {asset_id}: {error}",
                ) from error
            return

        ports = document["inputs"]
        accepts_keywords = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        for port in ports:
            name = port["name"]
            parameter = signature.parameters.get(name)
            if parameter is None:
                if not accepts_keywords:
                    _fail(
                        "callable_mismatch",
                        f"documented input is not callable for {asset_id}: {name}",
                    )
                continue
            if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
                _fail(
                    "callable_mismatch",
                    f"documented input is positional-only for {asset_id}: {name}",
                )
            runtime_required = parameter.default is inspect.Parameter.empty
            if port["required"] != runtime_required:
                _fail(
                    "callable_mismatch",
                    f"required status differs for {asset_id}: {name}",
                )
            if not runtime_required:
                if "default" not in port:
                    _fail(
                        "callable_mismatch",
                        f"documented default is missing for {asset_id}: {name}",
                    )
                if port["default"] != parameter.default:
                    _fail(
                        "callable_mismatch",
                        f"default differs for {asset_id}: {name}",
                    )

    def resolve_callable(self, asset_id: str) -> dict[str, Any]:
        document, _, _ = self._resolve_callable(asset_id)
        python_api = document["public_api"]["python"]
        return self._response(
            "callable.resolve",
            asset_id=asset_id,
            implementation_version=document["version"]["implementation_version"],
            binding=copy.deepcopy(python_api),
        )

    @staticmethod
    def _materialize(value: Any) -> Any:
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                _fail("result_not_serializable", "result contains a non-finite float")
            return value
        if isinstance(value, complex):
            return {
                "real": ThinMcpAdapter._materialize(value.real),
                "imag": ThinMcpAdapter._materialize(value.imag),
            }
        if isinstance(value, Mapping):
            result = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    _fail("result_not_serializable", "result mapping keys must be strings")
                result[key] = ThinMcpAdapter._materialize(item)
            return result
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [ThinMcpAdapter._materialize(item) for item in value]
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            converted = tolist()
            if converted is value:
                _fail("result_not_serializable", "result tolist conversion made no progress")
            return ThinMcpAdapter._materialize(converted)
        _fail("result_not_serializable", f"unsupported result type: {type(value).__name__}")

    def invoke(self, asset_id: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            _fail("invalid_request", "arguments must be an object")
        self._validate_string_keys(
            arguments, code="invalid_arguments", label="argument"
        )
        document = self._document(asset_id)
        ports = {port["name"]: port for port in document["inputs"]}
        unknown = sorted(set(arguments) - set(ports))
        missing = sorted(
            name
            for name, port in ports.items()
            if port["required"] and name not in arguments
        )
        if unknown:
            _fail("invalid_arguments", f"undocumented input arguments: {', '.join(unknown)}")
        if missing:
            _fail("invalid_arguments", f"missing required input arguments: {', '.join(missing)}")
        document, function, signature = self._resolve_callable(asset_id, document)
        if self._uses_task_graph_input_mapping(document, signature):
            call_arguments = {"inputs": dict(arguments)}
        else:
            call_arguments = dict(arguments)
        try:
            signature.bind(**call_arguments)
        except TypeError as error:
            raise ThinMcpAdapterError("invalid_arguments", str(error)) from error
        try:
            value = function(**call_arguments)
        except Exception as error:
            raise ThinMcpAdapterError(
                "invocation_failed", f"{type(error).__name__}: {error}"
            ) from error
        return self._response(
            "callable.invoke",
            asset_id=asset_id,
            implementation_version=document["version"]["implementation_version"],
            evidence_ceiling=document["verification"]["evidence_ceiling"],
            result=self._materialize(value),
        )

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            _fail("invalid_request", "request must be an object")
        operation = request.get("operation")
        if operation == "catalog.discover":
            self._validate_exact_keys(
                request,
                {"operation"},
                {"operation", "filters", "cursor", "limit"},
            )
            return self.discover(
                filters=request.get("filters"),
                cursor=request.get("cursor", 0),
                limit=request.get("limit", 20),
            )
        if operation == "asset.read":
            self._validate_exact_keys(
                request,
                {"operation", "asset_ids"},
                {"operation", "asset_ids", "detail"},
            )
            return self.read_assets(
                request["asset_ids"], detail=request.get("detail", "summary")
            )
        if operation == "callable.resolve":
            self._validate_exact_keys(
                request, {"operation", "asset_id"}, {"operation", "asset_id"}
            )
            return self.resolve_callable(request["asset_id"])
        if operation == "callable.invoke":
            self._validate_exact_keys(
                request,
                {"operation", "asset_id", "arguments"},
                {"operation", "asset_id", "arguments"},
            )
            return self.invoke(request["asset_id"], request["arguments"])
        _fail("invalid_request", f"unsupported operation: {operation!r}")


__all__ = ["ThinMcpAdapter", "ThinMcpAdapterError"]
