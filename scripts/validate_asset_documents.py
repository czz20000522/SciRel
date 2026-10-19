"""Validate framework-neutral SciRel asset documents."""

from __future__ import annotations

import argparse
import ast
import importlib
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ASSET_SCHEMA = "scirel.asset-document"
ASSET_ID_RE = re.compile(r"^scirel\.[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
FEEDBACK_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")

TOP_LEVEL_KEYS = {
    "schema",
    "asset_id",
    "kind",
    "title",
    "summary",
    "taxonomy",
    "aliases",
    "identity",
    "inputs",
    "outputs",
    "applicability",
    "failure_semantics",
    "provenance",
    "public_api",
    "version",
    "example",
    "verification",
    "graph",
}
REQUIRED_TOP_LEVEL_KEYS = TOP_LEVEL_KEYS - {"graph"}
PORT_KEYS = {
    "name",
    "description",
    "units",
    "shape",
    "dtype",
    "required",
    "constraints",
    "default",
}
REQUIRED_PORT_KEYS = PORT_KEYS - {"default"}
IDENTITY_KEYS = {
    "relation",
    "direction",
    "definition",
    "model",
    "geometry",
    "coordinates",
    "boundary",
    "assumptions",
}
FORBIDDEN_PUBLIC_KEYS = {
    "admission_ref",
    "case_ref",
    "decision_ref",
    "tenant_id",
    "candidate_ref",
    "version_commit_ref",
    "source_project_path",
}


class AssetDocumentError(ValueError):
    pass


def _fail(location: str, message: str) -> None:
    raise AssetDocumentError(f"{location}: {message}")


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(location, "must be an object")
    return value


def _list(value: Any, location: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        _fail(location, "must be a nonempty array" if nonempty else "must be an array")
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(location, "must be a nonempty string")
    return value


def _exact_keys(
    value: dict[str, Any], required: set[str], allowed: set[str], location: str
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        _fail(location, f"missing fields: {', '.join(missing)}")
    if unknown:
        _fail(location, f"unknown fields: {', '.join(unknown)}")


def _reject_private_keys(value: Any, location: str = "document") -> None:
    if isinstance(value, dict):
        forbidden = sorted(FORBIDDEN_PUBLIC_KEYS & value.keys())
        if forbidden:
            _fail(location, f"contains private governance fields: {', '.join(forbidden)}")
        for key, child in value.items():
            _reject_private_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_keys(child, f"{location}[{index}]")


def _validate_string_list(value: Any, location: str, *, nonempty: bool = False) -> list[str]:
    items = _list(value, location, nonempty=nonempty)
    for index, item in enumerate(items):
        _text(item, f"{location}[{index}]")
    if len(items) != len(set(items)):
        _fail(location, "must not contain duplicates")
    return items


def _validate_ports(value: Any, location: str, *, nonempty: bool = False) -> set[str]:
    ports = _list(value, location, nonempty=nonempty)
    names = set()
    for index, raw in enumerate(ports):
        item_location = f"{location}[{index}]"
        port = _object(raw, item_location)
        _exact_keys(port, REQUIRED_PORT_KEYS, PORT_KEYS, item_location)
        name = _text(port["name"], f"{item_location}.name")
        if not name.isidentifier():
            _fail(f"{item_location}.name", "must be a Python identifier")
        if name in names:
            _fail(location, f"duplicate port: {name}")
        names.add(name)
        for field in ("description", "units", "shape", "dtype", "constraints"):
            _text(port[field], f"{item_location}.{field}")
        if not isinstance(port["required"], bool):
            _fail(f"{item_location}.required", "must be boolean")
        if port["required"] and "default" in port:
            _fail(item_location, "required ports must not declare a default")
        if not port["required"] and "default" not in port:
            _fail(item_location, "optional ports must declare a default")
        if "default" in port:
            _validate_json_value(port["default"], f"{item_location}.default")
    return names


def _validate_json_value(value: Any, location: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail(location, "must be a finite JSON value")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(location, "JSON object keys must be strings")
            _validate_json_value(item, f"{location}.{key}")
        return
    _fail(location, "must be JSON-compatible")


def _validate_identity(value: Any) -> None:
    identity = _object(value, "identity")
    _exact_keys(identity, IDENTITY_KEYS, IDENTITY_KEYS, "identity")
    for field in IDENTITY_KEYS - {"assumptions"}:
        _text(identity[field], f"identity.{field}")
    _validate_string_list(identity["assumptions"], "identity.assumptions")


def _validate_applicability(value: Any) -> None:
    item = _object(value, "applicability")
    keys = {"preconditions", "supported", "excluded"}
    _exact_keys(item, keys, keys, "applicability")
    for field in keys:
        _validate_string_list(
            item[field], f"applicability.{field}", nonempty=field != "excluded"
        )


def _validate_failures(value: Any) -> None:
    item = _object(value, "failure_semantics")
    keys = {"invalid_input", "runtime_failure", "nonconvergence", "partial_results"}
    _exact_keys(item, keys, keys, "failure_semantics")
    for field in keys:
        _text(item[field], f"failure_semantics.{field}")


def _validate_provenance(value: Any) -> None:
    provenance = _object(value, "provenance")
    keys = {"lineage_summary", "source_kinds", "public_references", "license_status"}
    _exact_keys(provenance, keys, keys, "provenance")
    _text(provenance["lineage_summary"], "provenance.lineage_summary")
    _validate_string_list(
        provenance["source_kinds"], "provenance.source_kinds", nonempty=True
    )
    _validate_string_list(
        provenance["public_references"], "provenance.public_references"
    )
    _text(provenance["license_status"], "provenance.license_status")


def _validate_public_api(value: Any) -> tuple[str, str, str]:
    public_api = _object(value, "public_api")
    _exact_keys(public_api, {"python"}, {"python"}, "public_api")
    python_api = _object(public_api["python"], "public_api.python")
    keys = {
        "module",
        "symbol",
        "signature",
        "canonical_module",
        "canonical_symbol",
    }
    _exact_keys(
        python_api,
        {"module", "symbol", "signature"},
        keys,
        "public_api.python",
    )
    module = _text(python_api["module"], "public_api.python.module")
    symbol = _text(python_api["symbol"], "public_api.python.symbol")
    signature = _text(python_api["signature"], "public_api.python.signature")
    if not module.startswith("scirel.") or not all(part.isidentifier() for part in module.split(".")):
        _fail("public_api.python.module", "must be an importable scirel module")
    if not symbol.isidentifier():
        _fail("public_api.python.symbol", "must be a Python identifier")
    has_canonical_module = "canonical_module" in python_api
    has_canonical_symbol = "canonical_symbol" in python_api
    if has_canonical_module != has_canonical_symbol:
        _fail(
            "public_api.python",
            "canonical_module and canonical_symbol must be provided together",
        )
    if has_canonical_module:
        canonical_module = _text(
            python_api["canonical_module"], "public_api.python.canonical_module"
        )
        canonical_symbol = _text(
            python_api["canonical_symbol"], "public_api.python.canonical_symbol"
        )
        if not canonical_module.startswith("scirel.") or not all(
            part.isidentifier() for part in canonical_module.split(".")
        ):
            _fail(
                "public_api.python.canonical_module",
                "must be an importable scirel package module",
            )
        if not canonical_symbol.isidentifier():
            _fail(
                "public_api.python.canonical_symbol",
                "must be a Python identifier",
            )
    try:
        parsed = ast.parse(f"def {signature}:\n    pass\n")
    except SyntaxError as error:
        _fail("public_api.python.signature", f"is not a valid Python signature: {error.msg}")
    if parsed.body[0].name != symbol:
        _fail("public_api.python.signature", "must name the declared symbol")
    return module, symbol, signature


def _validate_version(value: Any) -> set[str]:
    version = _object(value, "version")
    keys = {"implementation_version", "dependencies"}
    _exact_keys(version, keys, keys, "version")
    _text(version["implementation_version"], "version.implementation_version")
    dependency_ids = set()
    for index, raw in enumerate(_list(version["dependencies"], "version.dependencies")):
        location = f"version.dependencies[{index}]"
        dependency = _object(raw, location)
        dependency_keys = {"asset_id"}
        _exact_keys(dependency, dependency_keys, dependency_keys, location)
        asset_id = _text(dependency["asset_id"], f"{location}.asset_id")
        if not ASSET_ID_RE.fullmatch(asset_id):
            _fail(f"{location}.asset_id", "has an invalid stable asset ID")
        if asset_id in dependency_ids:
            _fail("version.dependencies", f"duplicate dependency: {asset_id}")
        dependency_ids.add(asset_id)
    return dependency_ids


def _validate_example(value: Any) -> None:
    example = _object(value, "example")
    keys = {"description", "code", "expected"}
    _exact_keys(example, keys, keys, "example")
    for field in keys:
        _text(example[field], f"example.{field}")
    try:
        compile(example["code"], "<asset-example>", "exec")
    except SyntaxError as error:
        _fail("example.code", f"must compile: {error.msg}")


def _validate_verification(value: Any) -> None:
    verification = _object(value, "verification")
    keys = {"scope", "tests", "evidence_ceiling", "known_limitations"}
    _exact_keys(verification, keys, keys, "verification")
    _validate_string_list(verification["scope"], "verification.scope", nonempty=True)
    _validate_string_list(verification["tests"], "verification.tests", nonempty=True)
    _text(verification["evidence_ceiling"], "verification.evidence_ceiling")
    _validate_string_list(
        verification["known_limitations"],
        "verification.known_limitations",
        nonempty=True,
    )


def _has_cycle(nodes: set[str], edges: list[tuple[str, str]]) -> bool:
    outgoing = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    for source, target in edges:
        if target not in outgoing[source]:
            outgoing[source].add(target)
            indegree[target] += 1
    queue = [node for node, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        node = queue.pop()
        visited += 1
        for target in outgoing[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return visited != len(nodes)


def _validate_graph(
    value: Any, input_ports: set[str], output_ports: set[str], dependency_ids: set[str]
) -> None:
    graph = _object(value, "graph")
    graph_keys = {"nodes", "edges", "execution"}
    _exact_keys(graph, graph_keys, graph_keys, "graph")
    nodes = {}
    scientific_nodes = set()
    for index, raw in enumerate(_list(graph["nodes"], "graph.nodes", nonempty=True)):
        location = f"graph.nodes[{index}]"
        node = _object(raw, location)
        keys = {"id", "kind", "asset_id", "description", "inputs", "outputs"}
        required = keys - {"asset_id"}
        _exact_keys(node, required, keys, location)
        node_id = _text(node["id"], f"{location}.id")
        if not node_id.isidentifier() or node_id in nodes:
            _fail(f"{location}.id", "must be a unique identifier")
        kind = node["kind"]
        if kind not in {"operator", "task_graph", "controlled_glue", "caller_port"}:
            _fail(f"{location}.kind", "has an unsupported node kind")
        asset_id = node.get("asset_id")
        if kind in {"operator", "task_graph"}:
            if not isinstance(asset_id, str) or asset_id not in dependency_ids:
                _fail(f"{location}.asset_id", "must name a declared dependency")
            scientific_nodes.add(asset_id)
        elif asset_id is not None:
            _fail(f"{location}.asset_id", "is allowed only for scientific nodes")
        _text(node["description"], f"{location}.description")
        node_inputs = set(_validate_string_list(node["inputs"], f"{location}.inputs"))
        node_outputs = set(_validate_string_list(node["outputs"], f"{location}.outputs"))
        nodes[node_id] = {"inputs": node_inputs, "outputs": node_outputs}
    if scientific_nodes != dependency_ids:
        missing = sorted(dependency_ids - scientific_nodes)
        _fail("graph.nodes", f"does not bind every declared dependency: {', '.join(missing)}")

    ordinary_edges = []
    feedback_edge_ids = set()
    consumed_graph_inputs = set()
    connected_node_inputs = set()
    connected_graph_outputs = set()
    endpoint_keys = {"node", "port"}
    required_edge_keys = {
        "from",
        "to",
        "description",
        "condition",
        "transform",
        "kind",
        "required",
    }
    edge_keys = required_edge_keys | {"feedback_id"}
    for index, raw in enumerate(_list(graph["edges"], "graph.edges", nonempty=True)):
        location = f"graph.edges[{index}]"
        edge = _object(raw, location)
        _exact_keys(edge, required_edge_keys, edge_keys, location)
        source = _object(edge["from"], f"{location}.from")
        target = _object(edge["to"], f"{location}.to")
        _exact_keys(source, endpoint_keys, endpoint_keys, f"{location}.from")
        _exact_keys(target, endpoint_keys, endpoint_keys, f"{location}.to")
        source_node = _text(source["node"], f"{location}.from.node")
        target_node = _text(target["node"], f"{location}.to.node")
        source_port = _text(source["port"], f"{location}.from.port")
        target_port = _text(target["port"], f"{location}.to.port")
        if source_node == "$input":
            if source_port not in input_ports:
                _fail(f"{location}.from.port", "is not a graph input")
            consumed_graph_inputs.add(source_port)
        elif source_node not in nodes or source_port not in nodes[source_node]["outputs"]:
            _fail(f"{location}.from", "does not name a node output")
        if target_node == "$output":
            if target_port not in output_ports:
                _fail(f"{location}.to.port", "is not a graph output")
            connected_graph_outputs.add(target_port)
        elif target_node not in nodes or target_port not in nodes[target_node]["inputs"]:
            _fail(f"{location}.to", "does not name a node input")
        else:
            connected_node_inputs.add((target_node, target_port))
        for field in ("description", "condition", "transform"):
            _text(edge[field], f"{location}.{field}")
        if edge["kind"] not in {"data", "control", "feedback"}:
            _fail(f"{location}.kind", "must be data, control, or feedback")
        if not isinstance(edge["required"], bool):
            _fail(f"{location}.required", "must be boolean")
        if edge["kind"] == "feedback":
            if "feedback_id" not in edge:
                _fail(location, "feedback edge is missing feedback_id")
            feedback_id = _text(edge["feedback_id"], f"{location}.feedback_id")
            if not FEEDBACK_ID_RE.fullmatch(feedback_id):
                _fail(f"{location}.feedback_id", "has an invalid stable feedback ID")
            feedback_edge_ids.add(feedback_id)
        elif "feedback_id" in edge:
            _fail(f"{location}.feedback_id", "is allowed only for feedback edges")
        if source_node in nodes and target_node in nodes and edge["kind"] != "feedback":
            ordinary_edges.append((source_node, target_node))
    if _has_cycle(set(nodes), ordinary_edges):
        _fail("graph.edges", "ordinary data/control edges must be acyclic")
    if consumed_graph_inputs != input_ports:
        missing = sorted(input_ports - consumed_graph_inputs)
        _fail("graph.edges", f"does not consume graph inputs: {', '.join(missing)}")
    missing_node_inputs = sorted(
        f"{node}.{port}"
        for node, contract in nodes.items()
        for port in contract["inputs"]
        if (node, port) not in connected_node_inputs
    )
    if missing_node_inputs:
        _fail("graph.edges", f"does not connect node inputs: {', '.join(missing_node_inputs)}")
    if connected_graph_outputs != output_ports:
        missing = sorted(output_ports - connected_graph_outputs)
        _fail("graph.edges", f"does not produce graph outputs: {', '.join(missing)}")

    execution = _object(graph["execution"], "graph.execution")
    execution_keys = {
        "mode",
        "ordering",
        "branches",
        "state_ownership",
        "failure_propagation",
        "feedback",
    }
    _exact_keys(execution, execution_keys, execution_keys, "graph.execution")
    for field in ("mode", "ordering", "state_ownership", "failure_propagation"):
        _text(execution[field], f"graph.execution.{field}")
    _validate_string_list(execution["branches"], "graph.execution.branches")
    feedback = _list(execution["feedback"], "graph.execution.feedback")
    feedback_keys = {
        "id",
        "state",
        "initialization",
        "update_order",
        "continue_when",
        "stop_when",
        "iteration_bound",
        "nonconvergence",
    }
    feedback_contract_ids = set()
    for index, raw in enumerate(feedback):
        location = f"graph.execution.feedback[{index}]"
        contract = _object(raw, location)
        _exact_keys(contract, feedback_keys, feedback_keys, location)
        for field in feedback_keys:
            _text(contract[field], f"{location}.{field}")
        feedback_id = contract["id"]
        if not FEEDBACK_ID_RE.fullmatch(feedback_id):
            _fail(f"{location}.id", "has an invalid stable feedback ID")
        if feedback_id in feedback_contract_ids:
            _fail("graph.execution.feedback", f"duplicate feedback contract: {feedback_id}")
        feedback_contract_ids.add(feedback_id)
    missing_contracts = sorted(feedback_edge_ids - feedback_contract_ids)
    if missing_contracts:
        _fail(
            "graph.execution.feedback",
            f"missing contracts for feedback edges: {', '.join(missing_contracts)}",
        )
    orphan_contracts = sorted(feedback_contract_ids - feedback_edge_ids)
    if orphan_contracts:
        _fail(
            "graph.execution.feedback",
            f"contracts without feedback edges: {', '.join(orphan_contracts)}",
        )


def validate_document(document: Any, *, location: str = "document") -> dict[str, Any]:
    item = _object(document, location)
    _reject_private_keys(item, location)
    _exact_keys(item, REQUIRED_TOP_LEVEL_KEYS, TOP_LEVEL_KEYS, location)
    if item["schema"] != ASSET_SCHEMA:
        _fail(f"{location}.schema", f"must be {ASSET_SCHEMA}")
    asset_id = _text(item["asset_id"], f"{location}.asset_id")
    if not ASSET_ID_RE.fullmatch(asset_id):
        _fail(f"{location}.asset_id", "has an invalid stable asset ID")
    if item["kind"] not in {"operator", "task_graph"}:
        _fail(f"{location}.kind", "must be operator or task_graph")
    title = _object(item["title"], f"{location}.title")
    _exact_keys(title, {"en", "zh"}, {"en", "zh"}, f"{location}.title")
    _text(title["en"], f"{location}.title.en")
    _text(title["zh"], f"{location}.title.zh")
    _text(item["summary"], f"{location}.summary")
    _validate_string_list(item["taxonomy"], f"{location}.taxonomy", nonempty=True)
    _validate_string_list(item["aliases"], f"{location}.aliases")
    _validate_identity(item["identity"])
    input_ports = _validate_ports(item["inputs"], f"{location}.inputs")
    output_ports = _validate_ports(item["outputs"], f"{location}.outputs", nonempty=True)
    _validate_applicability(item["applicability"])
    _validate_failures(item["failure_semantics"])
    _validate_provenance(item["provenance"])
    _validate_public_api(item["public_api"])
    dependency_ids = _validate_version(item["version"])
    _validate_example(item["example"])
    _validate_verification(item["verification"])
    if item["kind"] == "task_graph":
        if "graph" not in item:
            _fail(location, "task_graph requires graph")
        _validate_graph(item["graph"], input_ports, output_ports, dependency_ids)
    else:
        if "graph" in item:
            _fail(location, "operator must not contain graph")
    return item


def load_document_set(
    directory: Path, *, additional_directories: tuple[Path, ...] = ()
) -> list[dict[str, Any]]:
    """Validate an explicitly supplied complete set; never discover siblings."""
    paths = sorted(directory.glob("*.json"))
    for additional in additional_directories:
        additional_paths = sorted(additional.glob("*.json"))
        if not additional_paths:
            raise AssetDocumentError(f"{additional}: contains no asset documents")
        paths.extend(additional_paths)
    if not paths:
        raise AssetDocumentError(f"{directory}: contains no asset documents")
    documents = []
    asset_ids = set()
    callables = set()
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AssetDocumentError(f"{path}: cannot read JSON: {error}") from error
        validate_document(document, location=path.name)
        asset_id = document["asset_id"]
        callable_name = (
            f"{document['public_api']['python']['module']}."
            f"{document['public_api']['python']['symbol']}"
        )
        if asset_id in asset_ids:
            _fail(str(directory), f"duplicate asset_id: {asset_id}")
        if callable_name in callables:
            _fail(str(directory), f"duplicate public callable: {callable_name}")
        asset_ids.add(asset_id)
        callables.add(callable_name)
        documents.append(document)
    for document in documents:
        for dependency in document["version"]["dependencies"]:
            if dependency["asset_id"] not in asset_ids:
                _fail(
                    document["asset_id"],
                    f"dependency is outside the document set: {dependency['asset_id']}",
                )
    return documents


def resolve_test_reference(reference: str, source_root: Path) -> Path:
    """Check a repository test file, preserving any opaque pytest node selector.

    Pytest resolves the selected case during collection/execution; filesystem
    existence applies only to the path before ``::``, never to the whole node ID.
    """
    filename, separator, selector = reference.partition("::")
    if not filename or (separator and any(not part for part in selector.split("::"))):
        raise ValueError(f"invalid test reference: {reference}")
    candidate = (source_root / filename).resolve()
    if Path(filename).is_absolute() or not candidate.is_relative_to(source_root.resolve()):
        raise ValueError(f"test path escapes the repository: {reference}")
    if not candidate.is_file():
        raise ValueError(f"declared test is missing: {reference}")
    return candidate


def validate_runtime(
    document: dict[str, Any],
    source_root: Path = ROOT,
    *,
    installed_runtime: bool = False,
) -> None:
    python_api = document["public_api"]["python"]
    source_path = str(source_root / "src")
    if not installed_runtime and source_path not in sys.path:
        sys.path.insert(0, source_path)
    module = importlib.import_module(python_api["module"])
    if installed_runtime:
        module_path = Path(module.__file__).resolve()
        if module_path.is_relative_to((source_root / "src").resolve()):
            _fail(document["asset_id"], "installed runtime resolved to the source checkout")
    function = getattr(module, python_api["symbol"], None)
    if not callable(function):
        _fail(document["asset_id"], "documented Python callable is unavailable")
    exports = getattr(module, "__all__", None)
    if not isinstance(exports, (list, tuple)) or python_api["symbol"] not in exports:
        _fail(
            document["asset_id"],
            "documented Python callable is not listed in the implementation module __all__",
        )
    if "canonical_module" in python_api:
        canonical_module = importlib.import_module(python_api["canonical_module"])
        if not hasattr(canonical_module, "__path__"):
            _fail(
                document["asset_id"],
                "canonical Python module must be a package",
            )
        canonical_function = getattr(
            canonical_module, python_api["canonical_symbol"], None
        )
        if not callable(canonical_function):
            _fail(
                document["asset_id"],
                "canonical documented Python callable is unavailable",
            )
        canonical_exports = getattr(canonical_module, "__all__", None)
        if (
            not isinstance(canonical_exports, (list, tuple))
            or python_api["canonical_symbol"] not in canonical_exports
        ):
            _fail(
                document["asset_id"],
                "canonical documented Python callable is not listed in the canonical module __all__",
            )
        if canonical_function is not function:
            _fail(
                document["asset_id"],
                "canonical Python callable differs from implementation binding",
            )
    signature = inspect.signature(function)
    actual_signature = f"{python_api['symbol']}{signature}"
    if actual_signature != python_api["signature"]:
        _fail(
            document["asset_id"],
            f"runtime signature differs: expected {python_api['signature']}, got {actual_signature}",
        )
    _validate_runtime_inputs(document, signature, function=function)
    for test_path in document["verification"]["tests"]:
        try:
            resolve_test_reference(test_path, source_root)
        except ValueError as error:
            _fail(document["asset_id"], str(error))


def _explicit_mapping_signature(document: dict[str, Any], function: Any) -> inspect.Signature | None:
    """Use a reviewed complex mapping only while every bound module is unchanged."""
    path = Path(__file__).with_name("mapping_interface_bindings.json")
    if not path.is_file():
        return None
    binding = next((row for row in json.loads(path.read_text())["records"]
                    if row["asset_id"] == document["asset_id"]), None)
    if binding is None:
        return None
    if binding["callable"] != f"{function.__module__}.{function.__name__}":
        _fail(document["asset_id"], "complex mapping callable binding differs")
    for name, expected in binding["modules"].items():
        module = importlib.import_module(name)
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != expected:
            _fail(document["asset_id"], f"complex mapping source binding differs: {name}")
    actual = [{key: port[key] for key in ("name", "required", "default") if key in port}
              for port in document["inputs"]]
    if actual != binding["ports"]:
        _fail(document["asset_id"], "complex mapping scientific ports/defaults differ")
    return inspect.Signature([inspect.Parameter(port["name"], inspect.Parameter.KEYWORD_ONLY,
            default=inspect.Parameter.empty if port["required"] else port["default"])
            for port in binding["ports"]])


def _mapping_delegate(document: dict[str, Any], function: Any) -> Any:
    """Resolve a transparent ``return relation(**inputs)`` adapter without calling it.

    An opaque mapping signature cannot establish scientific port identity. Only
    the actual installed adapter's simple forwarding body is accepted here;
    general workflow implementations need their own explicit binding contract.
    """
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        definition = tree.body[0]
        body = definition.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        if len(body) != 1 or not isinstance(body[0], ast.Return):
            raise ValueError("not a transparent return")
        call = body[0].value
        if (not isinstance(call, ast.Call) or call.args or len(call.keywords) != 1
                or call.keywords[0].arg is not None
                or not isinstance(call.keywords[0].value, ast.Name)
                or call.keywords[0].value.id != "inputs"):
            raise ValueError("not an exact **inputs forwarding call")
        reference = call.func
        attributes = []
        while isinstance(reference, ast.Attribute):
            attributes.append(reference.attr)
            reference = reference.value
        if not isinstance(reference, ast.Name):
            raise ValueError("delegate is not a static name")
        delegate = function.__globals__[reference.id]
        for attribute in reversed(attributes):
            # Resolve module namespaces, never execute arbitrary descriptors.
            if not inspect.ismodule(delegate):
                raise ValueError("delegate traversal is not a module namespace")
            delegate = vars(delegate)[attribute]
        if not callable(delegate) or delegate is function:
            raise ValueError("delegate is unavailable or recursive")
        return delegate
    except (OSError, TypeError, AttributeError, KeyError, SyntaxError, ValueError, IndexError) as error:
        _fail(document["asset_id"], f"TaskGraph mapping lacks a verifiable scientific delegate: {error}")


def _validate_runtime_inputs(
    document: dict[str, Any], signature: inspect.Signature, *, function: Any = None
) -> None:
    mapping = signature.parameters.get("inputs")
    accepts_keywords = any(parameter.kind is inspect.Parameter.VAR_KEYWORD
                           for parameter in signature.parameters.values())
    if document.get("kind") == "task_graph" and mapping is not None:
        if function is None:
            _fail(document["asset_id"], "TaskGraph mapping requires its actual callable binding")
        bound_signature = _explicit_mapping_signature(document, function)
        if bound_signature is None and (len(signature.parameters) != 1
                or mapping.default is not inspect.Parameter.empty
                or mapping.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                        inspect.Parameter.KEYWORD_ONLY)):
            _fail(document["asset_id"], "TaskGraph inputs mapping must be its one required callable parameter")
        signature = bound_signature if bound_signature is not None else inspect.signature(_mapping_delegate(document, function))
        if any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
               for p in signature.parameters.values()):
            _fail(document["asset_id"], "TaskGraph scientific delegate must expose explicit ports")
        documented_names = {port["name"] for port in document["inputs"]}
        missing = {name for name, parameter in signature.parameters.items()
                   if parameter.default is inspect.Parameter.empty and name not in documented_names}
        if missing:
            _fail(document["asset_id"], f"required scientific inputs are undocumented: {sorted(missing)}")
    elif document.get("kind") == "task_graph" and accepts_keywords:
        if function is None:
            _fail(document["asset_id"], "TaskGraph keywords require their actual callable binding")
        bound_signature = _explicit_mapping_signature(document, function)
        if bound_signature is None:
            _fail(document["asset_id"], "TaskGraph keywords require an explicit scientific port binding")
        signature = bound_signature
    accepts_keywords = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    for port in document["inputs"]:
        name = port["name"]
        parameter = signature.parameters.get(name)
        if parameter is None:
            if not accepts_keywords:
                _fail(document["asset_id"], f"documented input is not callable: {name}")
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            _fail(document["asset_id"], f"documented input is positional-only: {name}")
        runtime_required = parameter.default is inspect.Parameter.empty
        if port["required"] != runtime_required:
            _fail(document["asset_id"], f"required status differs for input: {name}")
        documented_default = port.get("default")
        runtime_default = parameter.default
        if not runtime_required:
            # JSON arrays preserve the values of public tuple defaults.
            try:
                runtime_default = json.loads(json.dumps(runtime_default))
            except (TypeError, ValueError):
                pass
        if not runtime_required and documented_default != runtime_default:
            _fail(document["asset_id"], f"default differs for input: {name}")


def execute_example(
    document: dict[str, Any],
    source_root: Path = ROOT,
    *,
    installed_runtime: bool = False,
) -> None:
    environment = os.environ.copy()
    command = [sys.executable, "-c", document["example"]["code"]]
    if installed_runtime:
        environment.pop("PYTHONPATH", None)
        command.insert(1, "-I")
    else:
        environment["PYTHONPATH"] = str(source_root / "src")
    completed = subprocess.run(
        command,
        cwd=Path.cwd() if installed_runtime else source_root,
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        _fail(
            document["asset_id"],
            "example failed:\n" + (completed.stderr or completed.stdout).strip(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents_dir", type=Path)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--execute-examples", action="store_true")
    parser.add_argument("--installed-runtime", action="store_true")
    args = parser.parse_args()
    if args.installed_runtime and not args.check_runtime:
        parser.error("--installed-runtime requires --check-runtime")
    try:
        documents = load_document_set(args.documents_dir.resolve())
        if args.check_runtime:
            for document in documents:
                validate_runtime(
                    document, installed_runtime=args.installed_runtime
                )
        if args.execute_examples:
            for document in documents:
                execute_example(
                    document, installed_runtime=args.installed_runtime
                )
    except (AssetDocumentError, ImportError, AttributeError) as error:
        print(f"asset document validation failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "schema": "scirel.asset-document-validation",
                "asset_count": len(documents),
                "asset_ids": sorted(document["asset_id"] for document in documents),
                "runtime_checked": args.check_runtime,
                "runtime_origin": (
                    "installed" if args.installed_runtime else "source"
                ) if args.check_runtime else None,
                "examples_executed": args.execute_examples,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
