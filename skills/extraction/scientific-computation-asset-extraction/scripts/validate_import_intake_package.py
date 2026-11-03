from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml


BANNED_OPERATOR_SECTIONS = (
    "admission",
    "admission classification",
    "operator source",
    "source scenario",
    "source path",
    "scientific intent",
    "evidence",
    "numerical contract",
    "implementation",
    "parent sub-task",
    "evidence chunk ids",
    "self-test evidence",
    "gaps",
)

GENERIC_IO_IDENTIFIERS = {
    "input_detail_1",
    "output_detail_1",
    "return_value",
    "mapping",
    "dict",
}

PORT_SHAPE_TERMS = (
    "shape", "形状", "轴序", "标量", "scalar", "array", "vector", "matrix",
    "mapping", "object", "float", "integer", "bool", "string", "table", "[",
)

CHINESE_OPERATOR_HEADINGS = (
    "语法",
    "说明",
    "输入参数",
    "输出参数",
    "科学或数值定义",
    "行为与边界",
    "验证与溯源",
)

CHINESE_OPERATOR_SECTIONS = {
    "inputs": "输入参数",
    "outputs": "输出参数",
    "boundaries": "行为与边界",
    "evidence": "验证与溯源",
}

CHINESE_TASK_GRAPH_HEADINGS = (
    "概述",
    "框架映射",
    "科学目的",
    "输入",
    "输出",
    "组成",
    "行为与边界",
    "验证与溯源",
)
PORT_UNIT_TERMS = (
    "units", "unit", "单位", "无量纲", "dimensionless", "inherit",
    "source convention", "source-defined",
)
PORT_CONSTRAINT_TERMS = (
    "constraint", "valid", "finite", "范围", "约束", "取值", "必须", "不得",
    "禁止", "有限", "nonnegative", "positive", "clamp", "fail", "reject", "error",
    "required", "optional", "caller",
)
SHARED_PORT_TERMS = ("all", "each", "every", "所有", "全部", "各", "上述")

# Source aliases and source-order language are useful provenance, but they are not a standalone
# scientific contract. Keep the check narrow so a physical "source term" or a literal identifier in
# a code block is not rejected.
SOURCE_COUPLED_PUBLIC_PROSE_RE = re.compile(
    r"(?:源码变量|源码索引|源码分支|源码调用顺序|source[- ](?:order|defined|backed|code)|"
    r"source\s+(?:variable|name|alias|convention))",
    re.IGNORECASE,
)
SOURCE_PATH_LITERAL_RE = re.compile(r"`[^`\n]*(?:\.py|\.f(?:90)?|\.c|\.h)(?::\d[^`]*)?`", re.IGNORECASE)

BANNED_PROFILE_ARTIFACT_NAMES = {
    "operator.py",
    "test_operator.py",
    "operator.c",
    "operator.h",
    "test_operator.c",
}

ALLOWED_PROJECT_MARKDOWN_NAMES = {
    "batch_index.md",
    "extraction_ledger.md",
    "extraction_report.md",
    "program_framework_map.md",
    "run_index.md",
}

ALLOWED_SUPPORT_MARKDOWN_NAMES = {
    "adapter.md",
    "config_schema.md",
    "relation.md",
}

SUPPORT_ASSET_DIR_NAMES = {
    "adapters",
    "capability_claims",
    "configs",
    "relations",
    "states",
}

GENERATED_ARTIFACT_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    ".cache",
    "htmlcov",
    "build",
    "dist",
    "cmakefiles",
}

GENERATED_ARTIFACT_FILE_NAMES = {
    ".coverage",
    "coverage.xml",
    "a.out",
    "test_scientific_operator",
    "test_operator",
    "pytestdebug.log",
}

GENERATED_ARTIFACT_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".o",
    ".obj",
    ".exe",
    ".dll",
    ".dylib",
    ".so",
    ".gcda",
    ".gcno",
    ".profraw",
    ".profdata",
    ".log",
}

LOCAL_RUNTIME_TERMS_RE = re.compile(
    r"(?im)^\s*(?:docker\s+run|podman\s+run)\b|(?:[A-Za-z]:\\\\|--mount\b|\s-v\s+\S+:/)",
)
SOURCE_STATUS_RE = re.compile(r"源码对照状态[：:]\s*(?P<status>[^\n\r]+)")

LINE_REF_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:)?[^\s`]+?\."
    r"(?:py|pyi|f|f90|for|pro|c|cc|cpp|h|hpp|i|inc|m|jl))"
    r":(?P<start>\d+)(?:-(?P<end>\d+))?",
    re.IGNORECASE,
)

ASSET_ROOT_NAMES = {"operators", "task_graphs"}
ALLOWED_TASK_GRAPH_NODE_KINDS = {
    "scientific_operator",
    "nested_task_graph",
    "controlled_glue",
    "configuration",
    "support_action",
    "io_config_action",
    "blocked_gap",
}
CONTROLLED_GLUE_OPERATIONS = {
    "block_concatenation",
    "boundary_padding",
    "component_selection",
    "index_base_conversion",
    "index_mapping",
    "real_imag_projection",
    "scalar_affine_conversion",
    "shape_embedding",
    "shape_reshape",
    "unit_conversion",
    "axis_permutation",
}
ORCHESTRATION_CONTROL_OPERATIONS = {
    "cadence_gate",
    "counter_state_transition",
    "action_plan_publication",
}
ALLOWED_EDGE_CLOSURES = {
    "asset",
    "controlled_glue",
    "orchestration",
    "ai_completable_glue",
    "configuration_or_schema_need",
    "validation_oracle_gap",
    "extraction_gap",
}

def _package_directories(root: Path, kind: str) -> list[Path]:
    """Discover packages from their asset directories, never from prose files."""
    family = "operators" if kind == "operator" else "task_graphs"
    container = root if root.name == family else root / family
    if container.is_dir():
        return sorted(path for path in container.iterdir() if path.is_dir())
    markers = (
        ("scientific_operator.py", "scientific_operator.c", "scientific_operator.h", "operator.md")
        if kind == "operator" else ("task_graph.yaml", "graph.py", "task_graph.md")
    )
    return [root] if any((root / name).is_file() for name in markers) else []


def _validate_package_source_mapping(
    directory: Path, *, root: Path, source_index: dict[str, set[str]] | None,
    evidence_matrix: str, errors: list[str],
) -> None:
    # Read existing anchors in implementation, tests, YAML or legacy documents.
    # A matrix row can be the sole source mapping; do not duplicate it per asset.
    texts = [
        path.read_text(encoding="utf-8") for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".py", ".c", ".h", ".yaml", ".md"}
    ]
    asset_ref = directory.relative_to(root).as_posix()
    if asset_ref == ".":
        family = "task_graphs" if (directory / "task_graph.yaml").is_file() else "operators"
        asset_ref = f"{family}/{directory.name}"
    row_pattern = re.compile(r"(?<![\w/])" + re.escape(asset_ref) + r"(?![\w/])")
    texts.extend(line for line in evidence_matrix.splitlines() if row_pattern.search(line))
    refs = [
        match.group("path").strip("`").replace("\\", "/")
        for match in LINE_REF_RE.finditer("\n".join(texts))
        if Path(match.group("path").strip("`")).name not in {
            "scientific_operator.py", "scientific_operator.c", "scientific_operator.h",
            "graph.py", "test_scientific_operator.py", "test_scientific_operator.c", "test_task_graph.py",
        }
    ]
    if not refs:
        errors.append(f"package requires an original-source anchor in code, tests or its existing evidence-matrix row: {asset_ref}")
    elif source_index is not None and not any(
        ref in source_index["source_paths"] or Path(ref).name in source_index["source_paths"]
        for ref in refs
    ):
        errors.append(f"package source anchors must match the supplied source-index: {asset_ref}")


def _validate_python_material(path: Path, *, root: Path, test: bool, errors: list[str]) -> None:
    if not path.is_file() or path.suffix != ".py":
        return
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        errors.append(f"invalid Python asset: {path.relative_to(root)}:{exc.lineno}")
        return
    if test:
        executable = [node for node in ast.walk(tree) if isinstance(node, (ast.Assert, ast.Call))]
        if not executable:
            errors.append(f"test artifact contains no executable test material: {path.relative_to(root)}")
    else:
        public = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not node.name.startswith("_")]
        expected = "run_graph" if path.name == "graph.py" else "scientific_operator"
        if expected not in public and not (expected == "scientific_operator" and len(public) == 1):
            errors.append(f"implementation requires {expected} or an unambiguous operator callable: {path.relative_to(root)}")


def validate_import_intake_package(
    root: Path,
    *,
    source_index_path: Path | None = None,
    operator_only: bool = False,
    evidence_matrix_path: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not root.is_dir():
        return {"valid": False, "errors": [f"root is not a directory: {root}"]}
    if root.is_symlink() or any(path.is_symlink() for path in root.rglob("*")):
        return {"valid": False, "errors": ["candidate packages may not contain symlinks"]}
    source_index = _load_source_index(source_index_path, errors=errors)
    evidence_matrix = ""
    if evidence_matrix_path is not None:
        try:
            evidence_matrix = evidence_matrix_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"evidence matrix is not readable: {exc}")
    operator_dirs = _package_directories(root, "operator")
    graph_dirs = _package_directories(root, "task_graph")
    for directory in operator_dirs:
        implementation = directory / "scientific_operator.py"
        required = [implementation]
        if not implementation.is_file() and (directory / "scientific_operator.c").is_file():
            required = [directory / "scientific_operator.c", directory / "scientific_operator.h"]
        for path in required:
            _require_non_empty_file(path, root=root, errors=errors)
            _validate_python_material(path, root=root, test=False, errors=errors)
        tests = sorted(path for path in directory.iterdir() if path.is_file()
                       and path.name.startswith("test") and path.suffix in {".py", ".c"})
        if not tests:
            errors.append(f"operator requires a direct test artifact: {directory.relative_to(root)}")
        for path in tests:
            _require_non_empty_file(path, root=root, errors=errors)
            _validate_python_material(path, root=root, test=True, errors=errors)
        _validate_package_source_mapping(directory, root=root, source_index=source_index,
                                         evidence_matrix=evidence_matrix, errors=errors)
    yaml_files = []
    for directory in graph_dirs:
        yaml_files.append(directory / "task_graph.yaml")
        _validate_task_graph_package(directory, directory / "task_graph.md", root=root, errors=errors)
        _validate_package_source_mapping(directory, root=root, source_index=source_index,
                                         evidence_matrix=evidence_matrix, errors=errors)
    _validate_task_graph_framework_mapping_membership(root, task_graph_yaml_files=yaml_files, errors=errors)
    if _has_asset_tree(root):
        _validate_task_graph_dependency_closure(root, task_graph_yaml_files=yaml_files, errors=errors)
    if not operator_dirs and not graph_dirs:
        errors.append("no operator or task-graph candidate package found")
    if operator_only and graph_dirs:
        errors.append("operator-only delivery must not contain task-graph packages")
    return {
        "valid": not errors,
        "errors": errors,
        "validation_scope": "structure_and_source_mapping",
        "scientific_validation": "requires_source_and_numerical_review",
        "relation_packages": [],
        "operator_packages": sorted(path.relative_to(root).as_posix() for path in operator_dirs),
        "task_graph_packages": sorted(path.relative_to(root).as_posix() for path in graph_dirs),
        "gap_notes": [],
    }


def _validate_task_graph_dependency_closure(
    root: Path,
    *,
    task_graph_yaml_files: list[Path],
    errors: list[str],
) -> None:
    """Reject dangling asset references and cycles between nested task graphs.

    Package-local contract checks cannot see dependencies owned by sibling packages. A
    project freeze therefore needs a second, deterministic pass over the complete
    bundle. This pass only follows machine-readable ``asset_ref`` values; arbitrary
    callable names remain package-local implementation concerns.
    """
    if not _has_asset_tree(root):
        return
    graph_dirs = {
        path.parent.name: path.parent
        for path in task_graph_yaml_files
        if path.is_file()
    }
    operator_dirs = {
        path.name: path for path in _package_directories(root, "operator")
    }
    graph_edges: dict[str, set[str]] = {name: set() for name in graph_dirs}

    for yaml_file in task_graph_yaml_files:
        if not yaml_file.is_file():
            continue
        try:
            document = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError):
            continue
        if not isinstance(document, dict):
            continue
        graph_name = yaml_file.parent.name
        for index, node in enumerate(document.get("nodes") or []):
            if not isinstance(node, dict):
                continue
            asset_ref = node.get("asset_ref")
            if not isinstance(asset_ref, str) or not asset_ref:
                continue
            prefix, separator, target = asset_ref.partition("/")
            if not separator or prefix not in ASSET_ROOT_NAMES or not target:
                continue
            if prefix == "task_graphs":
                target_dir = graph_dirs.get(target)
                if target_dir is None:
                    errors.append(
                        "task_graph.yaml asset_ref resolves to a missing task graph: "
                        f"{yaml_file.relative_to(root)} node#{index + 1} asset_ref={asset_ref}"
                    )
                else:
                    graph_edges[graph_name].add(target)
            elif operator_dirs.get(target) is None:
                errors.append(
                    "task_graph.yaml asset_ref resolves to a missing operator: "
                    f"{yaml_file.relative_to(root)} node#{index + 1} asset_ref={asset_ref}"
                )

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(graph_name: str) -> None:
        state[graph_name] = 1
        stack.append(graph_name)
        for dependency in sorted(graph_edges[graph_name]):
            if state.get(dependency, 0) == 0:
                visit(dependency)
            elif state.get(dependency) == 1:
                cycle_start = stack.index(dependency)
                cycle = stack[cycle_start:] + [dependency]
                errors.append(
                    "task_graph.yaml nested dependency cycle: "
                    + " -> ".join(cycle)
                )
        stack.pop()
        state[graph_name] = 2

    for graph_name in sorted(graph_dirs):
        if state.get(graph_name, 0) == 0:
            visit(graph_name)


def _has_asset_tree(root: Path) -> bool:
    return root.name in ASSET_ROOT_NAMES or any(
        (root / name).is_dir() for name in ASSET_ROOT_NAMES
    )


def _validate_task_graph_framework_mapping_membership(
    root: Path,
    *,
    task_graph_yaml_files: list[Path],
    errors: list[str],
) -> None:
    """Keep task-graph ownership aligned with an authoritative Level-1 ledger."""
    framework_map = root / "program_framework_map.md"
    if not framework_map.is_file():
        return
    text = framework_map.read_text(encoding="utf-8")
    ledger_match = re.search(
        r"(?ms)^##\s+Normalized Level 1 Node Ledger \(authoritative\)\s*$"
        r"(.*?)(?=^##\s|\Z)",
        text,
    )
    if not ledger_match:
        return
    known_nodes = set(re.findall(r"(?m)^\|\s*(N\d+)\b", ledger_match.group(1)))
    if not known_nodes:
        return
    for yaml_file in task_graph_yaml_files:
        if not yaml_file.is_file():
            continue
        yaml_text = yaml_file.read_text(encoding="utf-8")
        relpath = yaml_file.relative_to(root)
        primary = _primary_pfm_node_from_yaml(yaml_text)
        if primary and primary not in known_nodes:
            errors.append(
                "task_graph.yaml primary_pfm_node is absent from the authoritative "
                f"Level-1 ledger: {relpath} primary_pfm_node={primary}"
            )
        mapping = _yaml_top_level_section(yaml_text, "framework_mapping")
        related_match = re.search(r"(?m)^\s+related_pfm_nodes\s*:\s*\[([^]]*)\]", mapping)
        if not related_match:
            continue
        for related in re.findall(r"N\d+", related_match.group(1)):
            if related not in known_nodes:
                errors.append(
                    "task_graph.yaml related_pfm_nodes must use authoritative Level-1 "
                    f"nodes; retain source-local ids in source_subgraph_refs instead: "
                    f"{relpath} related_pfm_node={related}"
                )


def _asset_roots(root: Path) -> list[Path]:
    """Return only asset containers; project sidecars stay outside validation."""
    if root.name.casefold() in ASSET_ROOT_NAMES:
        return [root]
    roots = [root / name for name in ASSET_ROOT_NAMES if (root / name).is_dir()]
    return sorted(roots) if roots else [root]


def _is_allowed_markdown_artifact(path: Path, *, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = {part.casefold() for part in rel.parts}
    if path.name in {"operator.md", "task_graph.md"} or path.name.startswith("gap-"):
        return True
    if (
        path.name in ALLOWED_PROJECT_MARKDOWN_NAMES
        and not parts.intersection({"operators", "task_graphs"})
    ):
        return True
    if path.name in ALLOWED_SUPPORT_MARKDOWN_NAMES and parts.intersection(SUPPORT_ASSET_DIR_NAMES):
        return True
    return "validation_harnesses" in parts


def _validate_operator_only_root_files(root: Path, *, errors: list[str]) -> None:
    for root_file in root.iterdir():
        if root_file.is_file():
            errors.append(
                "operator-only delivery must not contain root-level files: "
                f"{root_file.relative_to(root)}"
            )


def _validate_no_generated_artifacts(root: Path, *, errors: list[str]) -> None:
    generated: set[Path] = set()
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        for index, part in enumerate(rel.parts):
            if part.casefold() in GENERATED_ARTIFACT_DIR_NAMES:
                generated.add(Path(*rel.parts[: index + 1]))
                break
        else:
            if not path.is_file():
                continue
            name = path.name.casefold()
            suffix = path.suffix.casefold()
            if (
                name in GENERATED_ARTIFACT_FILE_NAMES
                or suffix in GENERATED_ARTIFACT_SUFFIXES
            ):
                generated.add(rel)
    for rel in sorted(generated, key=lambda item: item.as_posix()):
        errors.append(
            "generated validation/test/build byproduct must be removed before "
            f"delivery: {rel.as_posix()}"
        )


def _require_non_empty_file(path: Path, *, root: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(root)}")
        return
    if not path.read_bytes().strip():
        errors.append(f"empty required file: {path.relative_to(root)}")


def _validate_test_artifact(
    path: Path,
    *,
    root: Path,
    require_header: bool,
    errors: list[str],
) -> None:
    if not require_header or not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    first_lines = "\n".join(text.splitlines()[:60])
    required_labels = (
        "测试结果",
        "工作目录",
        "命令",
        "环境变量",
        "结果",
        "对照依据",
        "源码对照状态",
        "证据来源",
        "数值差异",
        "运行环境",
    )
    missing_labels = [label for label in required_labels if label not in first_lines]
    if missing_labels:
        errors.append(
            "candidate test artifact requires standardized top-of-file "
            f"test result comments ({', '.join(missing_labels)} missing): "
            f"{path.relative_to(root)}"
        )
    positions = [
        match.start()
        for label in required_labels
        if (match := re.search(rf"(?m)^\s*#\s*{re.escape(label)}\s*[：:]", first_lines))
    ]
    if not missing_labels and positions != sorted(positions):
        errors.append(
            "candidate test artifact test-result fields must use the canonical order: "
            f"{path.relative_to(root)}"
        )
    status_match = SOURCE_STATUS_RE.search(first_lines)
    if status_match:
        status = status_match.group("status").strip()
        if (
            status != "direct_source_runnable"
            and not status.startswith("source_unavailable:")
            and not status.startswith(("source_free", "source-free", "source free", "脱离源码"))
        ):
            errors.append(
                "test artifact source comparison status must state direct source replay "
                "or an explicit source-free/unavailable boundary: "
                f"{path.relative_to(root)}"
            )
        if status == "direct_source_runnable" and (
            "max_abs" not in first_lines or "max_rel" not in first_lines
        ):
            errors.append(
                "direct_source_runnable test header must report numerical "
                "difference metrics including max_abs and max_rel: "
                f"{path.relative_to(root)}"
            )


def _validate_task_graph_package(
    task_graph_dir: Path,
    task_graph_file: Path,
    *,
    root: Path,
    errors: list[str],
) -> None:
    task_graph_relpath = task_graph_dir.relative_to(root).as_posix()
    for required_name in ("task_graph.yaml", "graph.py"):
        _require_non_empty_file(
            task_graph_dir / required_name,
            root=root,
            errors=errors,
        )
    yaml_file = task_graph_dir / "task_graph.yaml"
    graph_file = task_graph_dir / "graph.py"
    if yaml_file.is_file():
        _validate_task_graph_yaml_contract(
            yaml_file,
            root=root,
            errors=errors,
        )
    if graph_file.is_file():
        _validate_python_material(graph_file, root=root, test=False, errors=errors)
        _validate_graph_entrypoint_contract(
            graph_file,
            root=root,
            errors=errors,
        )
        if yaml_file.is_file():
            _validate_task_graph_implementation_purity(
                graph_file,
                yaml_file=yaml_file,
                root=root,
                errors=errors,
            )
            _validate_task_graph_yaml_inputs_against_entrypoint(
                graph_file,
                yaml_file=yaml_file,
                source_path=task_graph_relpath,
                errors=errors,
            )
    test_artifacts = [
        artifact for artifact in task_graph_dir.iterdir()
        if artifact.is_file() and artifact.name.casefold().startswith("test")
    ]
    if not test_artifacts:
        errors.append(
            "task graph package requires at least one test-like artifact name "
            "(for example test_task_graph.py): "
            f"{task_graph_dir.relative_to(root)}"
        )
    for artifact in test_artifacts:
        _require_non_empty_file(artifact, root=root, errors=errors)
        _validate_python_material(artifact, root=root, test=True, errors=errors)



def _validate_task_graph_yaml_contract(
    path: Path,
    *,
    root: Path,
    errors: list[str],
) -> None:
    text = path.read_text(encoding="utf-8")
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(
            "task_graph.yaml must be valid YAML: "
            f"{path.relative_to(root)} ({exc.problem or exc.__class__.__name__})"
        )
        return
    if not isinstance(document, dict):
        errors.append(f"task_graph.yaml must contain a mapping document: {path.relative_to(root)}")
        return
    for key in ("inputs", "outputs", "nodes", "edges", "execution"):
        if not re.search(rf"(?m)^{re.escape(key)}\s*:", text):
            errors.append(
                f"task_graph.yaml requires top-level {key}: {path.relative_to(root)}"
            )
    for section in ("inputs", "outputs"):
        ports = document.get(section)
        if not isinstance(ports, list):
            errors.append(f"task_graph.yaml {section} must be a list of port mappings: {path.relative_to(root)}")
            continue
        for index, port in enumerate(ports, start=1):
            if not isinstance(port, dict):
                errors.append(
                    f"task_graph.yaml {section} port#{index} must be a mapping with name, meaning, shape, and units: "
                    f"{path.relative_to(root)}"
                )
                continue
            missing = [field for field in ("name", "meaning", "shape", "units") if not str(port.get(field, "")).strip()]
            if missing:
                errors.append(
                    f"task_graph.yaml {section} port#{index} lacks {', '.join(missing)}: {path.relative_to(root)}"
                )
    node_entries = _yaml_sequence_entries(_yaml_top_level_section(text, "nodes"))
    edge_entries = _yaml_sequence_entries(_yaml_top_level_section(text, "edges"))
    if not node_entries:
        errors.append(f"task_graph.yaml requires at least one node: {path.relative_to(root)}")
    # A direct single-node graph is a valid black-box wrapper and has no
    # inter-node payload to declare. Multi-node graphs must still expose at
    # least one explicit edge.
    if not edge_entries and len(node_entries) > 1:
        errors.append(f"task_graph.yaml requires at least one edge: {path.relative_to(root)}")
    for index, entry in enumerate(node_entries, start=1):
        for field in ("id", "name", "kind", "callable", "inputs", "outputs"):
            if not _yaml_entry_has_field(entry, field):
                errors.append(
                    "task_graph.yaml node entries require "
                    f"{field}: {path.relative_to(root)} node#{index}"
                )
        asset_ref = _yaml_entry_field_value(entry, "asset_ref")
        kind = _yaml_entry_field_value(entry, "kind")
        if kind and kind not in ALLOWED_TASK_GRAPH_NODE_KINDS:
            errors.append(
                "task_graph.yaml node kind is not canonical: "
                f"{path.relative_to(root)} node#{index} kind={kind}"
            )
        if asset_ref and not _is_safe_asset_ref(asset_ref):
            errors.append(
                "task_graph.yaml asset_ref must be a normalized bundle-relative "
                f"operators/... or task_graphs/... path: {path.relative_to(root)} node#{index}"
            )
        if asset_ref.startswith("task_graphs/") and kind != "nested_task_graph":
            errors.append(
                "task_graph.yaml nodes whose asset_ref points to task_graphs/ "
                f"must use kind: nested_task_graph: {path.relative_to(root)} node#{index}"
            )
        if kind == "nested_task_graph" and not asset_ref.startswith("task_graphs/"):
            errors.append(
                "task_graph.yaml nested_task_graph nodes require an asset_ref "
                f"under task_graphs/: {path.relative_to(root)} node#{index}"
            )
        if asset_ref.startswith("operators/") and kind != "scientific_operator":
            errors.append(
                "task_graph.yaml nodes whose asset_ref points to operators/ "
                f"must use kind: scientific_operator: {path.relative_to(root)} node#{index}"
            )
        if kind == "scientific_operator" and not asset_ref.startswith("operators/"):
            errors.append(
                "task_graph.yaml scientific_operator nodes require an asset_ref "
                f"under operators/: {path.relative_to(root)} node#{index}"
            )
        if kind == "controlled_glue":
            callable_name = _yaml_entry_field_value(entry, "callable")
            if asset_ref:
                errors.append(
                    "task_graph.yaml controlled_glue nodes must not declare asset_ref; "
                    f"they are graph-local port adapters: {path.relative_to(root)} node#{index}"
                )
            if not callable_name.startswith("glue:"):
                errors.append(
                    "task_graph.yaml controlled_glue nodes require callable: glue:<function_name>: "
                    f"{path.relative_to(root)} node#{index}"
                )
            if not _yaml_entry_has_field(entry, "glue_contract"):
                errors.append(
                    "task_graph.yaml controlled_glue nodes require an explicit glue_contract: "
                    f"{path.relative_to(root)} node#{index}"
                )
        for field in ("inputs", "outputs"):
            if _yaml_entry_field_value(entry, field) in {"[]", "[ ]"}:
                errors.append(
                    "task_graph.yaml node ports must be explicit, not empty placeholders: "
                    f"{path.relative_to(root)} node#{index} {field}"
                )
    for index, entry in enumerate(edge_entries, start=1):
        for field in (
            "from",
            "to",
            "from_output",
            "to_input",
            "condition",
            "required",
            "data",
            "transform",
            "closure",
        ):
            if not _yaml_entry_has_field(entry, field):
                errors.append(
                    "task_graph.yaml edge entries require "
                    f"{field}: {path.relative_to(root)} edge#{index}"
                )
        closure = _yaml_entry_field_value(entry, "closure")
        if closure and closure not in ALLOWED_EDGE_CLOSURES:
            errors.append(
                "task_graph.yaml edge closure is not canonical: "
                f"{path.relative_to(root)} edge#{index} closure={closure}"
            )


def _is_safe_asset_ref(value: str) -> bool:
    if "\\" in value or ":" in value:
        return False
    ref = PurePosixPath(value)
    return (
        not ref.is_absolute()
        and len(ref.parts) == 2
        and ref.parts[0] in ASSET_ROOT_NAMES
        and all(part not in {"", ".", ".."} for part in ref.parts)
    )


def _validate_task_graph_markdown_ports_against_yaml(
    markdown_text: str,
    *,
    yaml_file: Path,
    source_path: str,
    errors: list[str],
) -> None:
    yaml_text = yaml_file.read_text(encoding="utf-8")
    for yaml_section, markdown_section in (("inputs", "输入"), ("outputs", "输出")):
        yaml_ports = _yaml_top_level_port_names(yaml_text, yaml_section)
        if not yaml_ports:
            errors.append(
                f"task_graph.yaml {yaml_section} requires named black-box ports: {source_path}"
            )
            continue
        markdown_ports = {
            identifier
            for item in _section_list(markdown_text, markdown_section)
            for identifier in _contract_identifiers(item)
        }
        missing = sorted(yaml_ports - markdown_ports)
        undeclared = sorted(markdown_ports - yaml_ports)
        if missing:
            errors.append(
                f"task_graph.md {markdown_section} must document YAML ports {', '.join(missing)}: {source_path}"
            )
        if undeclared:
            errors.append(
                f"task_graph.md {markdown_section} declares non-YAML ports {', '.join(undeclared)}: {source_path}"
            )


def _yaml_top_level_port_names(text: str, section: str) -> set[str]:
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
        return set()
    ports = document.get(section) if isinstance(document, dict) else None
    if not isinstance(ports, list):
        return set()
    return {
        str(port["name"])
        for port in ports
        if isinstance(port, dict) and isinstance(port.get("name"), str)
    }


def _validate_task_graph_yaml_inputs_against_entrypoint(
    graph_file: Path,
    *,
    yaml_file: Path,
    source_path: str,
    errors: list[str],
) -> None:
    """Require declared graph inputs to cover literal reads from run_graph."""
    try:
        tree = ast.parse(graph_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    literal_reads: set[str] = set()
    for node in ast.walk(tree):
        value: ast.AST | None = None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "inputs":
            value = node.slice
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "inputs"
            and node.func.attr == "get"
            and node.args
        ):
            value = node.args[0]
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            literal_reads.add(value.value)
    missing = sorted(literal_reads - _yaml_top_level_port_names(yaml_file.read_text(encoding="utf-8"), "inputs"))
    if missing:
        errors.append(
            "task_graph.yaml Inputs must cover graph.py literal inputs "
            f"{', '.join(missing)}: {source_path}"
        )


def _validate_graph_entrypoint_contract(
    path: Path,
    *,
    root: Path,
    errors: list[str],
) -> None:
    text = path.read_text(encoding="utf-8")
    if "task_graph.yaml" not in text and "TASK_GRAPH_CONTRACT" not in text:
        errors.append(
            "graph.py must load task_graph.yaml or a package-local generated "
            f"TASK_GRAPH_CONTRACT: {path.relative_to(root)}"
        )
    if not any(
        marker in text
        for marker in ("yaml.safe_load", "_EXPECTED_TASK_GRAPH_SHA256")
    ):
        errors.append(
            "graph.py must parse task_graph.yaml or enforce an exact package-local "
            f"contract digest: {path.relative_to(root)}"
        )
    digest_match = re.search(
        r'_EXPECTED_TASK_GRAPH_SHA256\s*=\s*["\']([0-9a-fA-F]{64})["\']',
        text,
    )


    if "_EXPECTED_TASK_GRAPH_SHA256" in text and not digest_match:
        errors.append(
            "graph.py contract digest must be a literal SHA-256 value: "
            f"{path.relative_to(root)}"
        )
    elif digest_match:
        yaml_path = path.with_name("task_graph.yaml")
        if not yaml_path.is_file():
            errors.append(f"graph.py requires its bound task_graph.yaml: {path.relative_to(root)}")
            return
        actual = hashlib.sha256(yaml_path.read_bytes()).hexdigest()
        if digest_match.group(1).casefold() != actual:
            errors.append(
                "graph.py contract digest does not match task_graph.yaml: "
                f"{path.relative_to(root)}"
            )
    if "GRAPH_ORDER" in text and "task_graph.yaml" not in text:
        errors.append(
            "graph.py must not use a decorative GRAPH_ORDER without YAML-driven "
            f"execution: {path.relative_to(root)}"
        )


_GRAPH_NUMPY_CONTAINER_CALLS = {
    "all",
    "any",
    "array",
    "asarray",
    "empty",
    "empty_like",
    "full",
    "isfinite",
    "ones",
    "ones_like",
    "zeros",
    "zeros_like",
}
_GRAPH_NUMPY_GLUE_CALLS = {
    "axis_permutation": {"asarray", "moveaxis", "transpose"},
    "block_concatenation": {"asarray", "concatenate"},
    "boundary_padding": {"asarray", "vstack"},
    "component_selection": {"asarray", "squeeze", "take"},
    "index_mapping": {"asarray"},
    "shape_embedding": {"asarray", "broadcast_to", "vstack"},
    "shape_reshape": {"asarray", "expand_dims", "reshape", "squeeze"},
}
_GRAPH_NUMPY_CONTRACT_VALIDATION_CALLS = {
    "allclose",
    "array_equal",
    "diff",
    "isclose",
}


def _validate_task_graph_implementation_purity(
    graph_file: Path,
    *,
    yaml_file: Path,
    root: Path,
    errors: list[str],
) -> None:
    """Reject hidden scientific mappings in a task-graph implementation."""
    try:
        document = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        tree = ast.parse(graph_file.read_text(encoding="utf-8"))
    except (yaml.YAMLError, SyntaxError):
        return

    nodes = document.get("nodes") if isinstance(document, dict) else None
    node_mappings = [node for node in nodes if isinstance(node, dict)] if isinstance(nodes, list) else []
    scientific_nodes = [
        node for node in node_mappings
        if node.get("kind") in {"scientific_operator", "nested_task_graph"}
    ]
    declared_refs = [node.get("asset_ref") for node in scientific_nodes if isinstance(node.get("asset_ref"), str) and node["asset_ref"].strip()]
    location = graph_file.relative_to(root)
    execution = document.get("execution") if isinstance(document, dict) else None
    orchestration_only = isinstance(execution, dict) and execution.get("orchestration_only") is True
    if not declared_refs and not orchestration_only:
        errors.append(
            "task graph with graph.py requires at least one declared scientific "
            f"operator/nested-task-graph asset_ref; graph.py may not self-contain a scientific mapping: {location}"
        )
    if orchestration_only and declared_refs:
        errors.append(
            "orchestration_only task graph may not declare scientific operator/nested-task-graph asset_ref: "
            f"{location}"
        )
    for index, node in enumerate(node_mappings, start=1):
        kind = node.get("kind")
        if kind == "internal_kernel":
            errors.append(
                "task_graph.yaml may not use kind: internal_kernel; extract its stable numerical mapping as an operator "
                f"or keep only orchestration in graph.py: {yaml_file.relative_to(root)} node#{index}"
            )
        if kind in {"scientific_operator", "nested_task_graph"} and not node.get("asset_ref"):
            errors.append(
                "task_graph.yaml scientific/nested nodes require asset_ref; a callable name or internal graph helper is not an asset dependency: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )

    glue_functions: dict[str, str] = {}
    control_functions: dict[str, str] = {}
    for index, node in enumerate(node_mappings, start=1):
        if node.get("kind") != "controlled_glue":
            continue
        callable_name = node.get("callable")
        contract = node.get("glue_contract")
        if not isinstance(callable_name, str) or not callable_name.startswith("glue:"):
            errors.append(
                "controlled_glue callable must be glue:<function_name>: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
            continue
        function_name = callable_name.removeprefix("glue:")
        if not function_name.isidentifier():
            errors.append(
                "controlled_glue callable suffix must be a Python identifier: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
            continue
        if function_name == "run_graph":
            errors.append(
                "controlled_glue callable must name a graph-local adapter function, not run_graph: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
            continue
        if node.get("asset_ref"):
            errors.append(
                "controlled_glue may not declare asset_ref: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
        if not isinstance(contract, dict):
            errors.append(
                "controlled_glue requires mapping glue_contract with operation and ownership: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
            continue
        operation = contract.get("operation")
        if operation not in CONTROLLED_GLUE_OPERATIONS:
            errors.append(
                "controlled_glue operation must be one of the bounded port-adaptation operations: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
            continue
        if not str(contract.get("ownership", "")).strip():
            errors.append(
                "controlled_glue glue_contract requires explicit ownership: "
                f"{yaml_file.relative_to(root)} node#{index}"
            )
        glue_functions[function_name] = str(operation)

    if orchestration_only:
        if not node_mappings:
            errors.append(f"orchestration_only task graph requires declared support actions: {location}")
        for index, node in enumerate(node_mappings, start=1):
            if node.get("kind") != "support_action":
                errors.append(
                    "orchestration_only task graph nodes must be support_action, not scientific or controlled_glue nodes: "
                    f"{yaml_file.relative_to(root)} node#{index}"
                )
                continue
            callable_name = node.get("callable")
            contract = node.get("control_contract")
            if not isinstance(callable_name, str) or not callable_name.startswith("control:"):
                errors.append(
                    "orchestration_only support_action requires callable: control:<function_name>: "
                    f"{yaml_file.relative_to(root)} node#{index}"
                )
                continue
            function_name = callable_name.removeprefix("control:")
            if not function_name.isidentifier():
                errors.append(
                    "orchestration_only control callable suffix must be a Python identifier: "
                    f"{yaml_file.relative_to(root)} node#{index}"
                )
                continue
            if not isinstance(contract, dict) or contract.get("operation") not in ORCHESTRATION_CONTROL_OPERATIONS or not str(contract.get("ownership", "")).strip():
                errors.append(
                    "orchestration_only support_action requires control_contract with a bounded operation and ownership: "
                    f"{yaml_file.relative_to(root)} node#{index}"
                )
                continue
            control_functions[function_name] = str(contract["operation"])

    function_definitions = {
        node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    for function_name in glue_functions:
        if function_name not in function_definitions:
            errors.append(
                "controlled_glue callable must be implemented by a graph.py function: "
                f"{location} callable=glue:{function_name}"
            )
    for function_name in control_functions:
        if function_name not in function_definitions:
            errors.append(
                "orchestration_only control callable must be implemented by graph.py: "
                f"{location} callable=control:{function_name}"
            )
            continue
        operation = control_functions[function_name]
        if operation == "cadence_gate":
            returns = [
                node
                for node in ast.walk(function_definitions[function_name])
                if isinstance(node, ast.Return)
            ]
            if not returns or any(not _is_boolean_control_return(node.value) for node in returns):
                errors.append(
                    "orchestration_only cadence_gate control callable must return a boolean predicate: "
                    f"{location} callable=control:{function_name}"
                )
        elif operation == "counter_state_transition":
            returns = [
                node
                for node in ast.walk(function_definitions[function_name])
                if isinstance(node, ast.Return)
            ]
            if not returns or any(not _is_counter_control_return(node.value) for node in returns):
                errors.append(
                    "orchestration_only counter_state_transition must return a counter increment or decrement: "
                    f"{location} callable=control:{function_name}"
                )
        elif operation == "action_plan_publication":
            returns = [
                node
                for node in ast.walk(function_definitions[function_name])
                if isinstance(node, ast.Return)
            ]
            if not returns or any(not _is_literal_control_output(node.value) for node in returns):
                errors.append(
                    "orchestration_only action_plan_publication must return a literal control-only output: "
                    f"{location} callable=control:{function_name}"
                )

    if orchestration_only and (run_graph := function_definitions.get("run_graph")) is not None:
        control_result_names = {
            target.id
            for assignment in ast.walk(run_graph)
            if isinstance(assignment, (ast.Assign, ast.AnnAssign))
            for target in (
                assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            )
            if isinstance(target, ast.Name)
            and isinstance(assignment.value, ast.Call)
            and _ast_dotted_name(assignment.value.func) in control_functions
        }
        returns = [node for node in ast.walk(run_graph) if isinstance(node, ast.Return)]
        if not returns or any(
            not _is_control_only_graph_output(
                node.value,
                control_functions=set(control_functions),
                control_result_names=control_result_names,
            )
            for node in returns
        ):
            errors.append(
                "orchestration_only run_graph must return only declared control results and literal control-only output: "
                f"{location}"
            )

    # A controlled-glue adapter may translate declared ports, but may not become a
    # concealed subgraph by resolving and executing scientific assets itself.  Track
    # local helper calls as well as direct loader calls because a common bypass is
    # ``glue_* -> call(...) -> operator_loader(...)``.
    loader_parameter_names = {
        argument.arg
        for definition in function_definitions.values()
        for argument in (*definition.args.posonlyargs, *definition.args.args, *definition.args.kwonlyargs)
        if argument.arg in {"operator_loader", "asset_loader", "task_graph_loader"}
    }
    called_function_names = {
        name: {
            _ast_dotted_name(call.func)
            for call in ast.walk(definition)
            if isinstance(call, ast.Call) and _ast_dotted_name(call.func)
        }
        for name, definition in function_definitions.items()
    }
    loader_invoking_functions = {
        name for name, calls in called_function_names.items() if calls & loader_parameter_names
    }
    changed = True
    while changed:
        changed = False
        for name, calls in called_function_names.items():
            if name not in loader_invoking_functions and calls & loader_invoking_functions:
                loader_invoking_functions.add(name)
                changed = True
    for function_name in glue_functions:
        if function_name in loader_invoking_functions:
            errors.append(
                "controlled_glue may not invoke scientific asset loaders directly or through local helpers; "
                "model the composition as declared scientific_operator/nested_task_graph nodes: "
                f"{location} callable=glue:{function_name}"
            )

    def glue_operation_for(ast_node: ast.AST) -> str | None:
        for function_name, operation in glue_functions.items():
            definition = function_definitions.get(function_name)
            if definition is not None and any(descendant is ast_node for descendant in ast.walk(definition)):
                return operation
        return None

    def control_operation_for(ast_node: ast.AST) -> str | None:
        for function_name, operation in control_functions.items():
            definition = function_definitions.get(function_name)
            if definition is not None and any(descendant is ast_node for descendant in ast.walk(definition)):
                return operation
        return None

    numpy_aliases: set[str] = set()
    scipy_aliases: set[str] = set()
    importlib_aliases: set[str] = set()
    imported_dynamic_names: set[str] = set()
    imported_numeric_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name == "numpy":
                    numpy_aliases.add(alias.asname or root_name)
                if root_name == "scipy":
                    scipy_aliases.add(alias.asname or root_name)
                if root_name == "importlib":
                    importlib_aliases.add(alias.asname or root_name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_name = node.module.split(".", 1)[0]
            if root_name in {"numpy", "scipy"}:
                imported_numeric_names.update(alias.asname or alias.name for alias in node.names)
                if root_name == "scipy":
                    scipy_aliases.add("scipy")
            if root_name == "importlib":
                importlib_aliases.add(node.module)
                imported_dynamic_names.update(alias.asname or alias.name for alias in node.names)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            dotted = _ast_dotted_name(node.func)
            root_name = dotted.split(".", 1)[0] if dotted else ""
            leaf_name = dotted.rsplit(".", 1)[-1] if dotted else ""
            if orchestration_only and root_name in numpy_aliases | scipy_aliases | imported_numeric_names:
                errors.append(f"orchestration_only graph may not call NumPy/SciPy helpers: {location} line {node.lineno}")
            elif root_name in scipy_aliases or root_name in imported_numeric_names:
                errors.append(f"graph.py may not call SciPy/scientific numeric helpers directly: {location} line {node.lineno}")
            elif root_name in numpy_aliases and leaf_name not in _GRAPH_NUMPY_CONTAINER_CALLS:
                glue_operation = glue_operation_for(node)
                if leaf_name in _GRAPH_NUMPY_GLUE_CALLS.get(glue_operation, set()):
                    continue
                if (
                    leaf_name in _GRAPH_NUMPY_CONTRACT_VALIDATION_CALLS
                    and _is_contract_validation_call(node, parents)
                ):
                    continue
                errors.append(f"graph.py may not call NumPy numerical mappings directly; extract an operator: {location} line {node.lineno}")
            elif root_name in importlib_aliases or root_name in imported_dynamic_names or dotted == "__import__":
                errors.append(f"graph.py may not dynamically import sibling assets; use the injected bundle resolver: {location} line {node.lineno}")
            elif (
                dotted == "getattr"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in numpy_aliases | scipy_aliases
            ):
                errors.append(f"graph.py may not dynamically select scientific numeric helpers: {location} line {node.lineno}")
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            if orchestration_only:
                if not _is_control_arithmetic(node, control_operation_for(node)):
                    errors.append(
                        "graph.py may not implement direct numerical arithmetic mappings without a declared controlled_glue node: "
                        f"{location} line {node.lineno}"
                    )
                continue
            glue_operation = glue_operation_for(node)
            if not _is_orchestration_arithmetic(node) and not _is_contract_validation_arithmetic(node, parents) and glue_operation not in {
                "block_concatenation",
                "boundary_padding",
                "index_base_conversion",
                "index_mapping",
                "scalar_affine_conversion",
                "unit_conversion",
            }:
                errors.append(f"graph.py may not implement direct numerical arithmetic mappings without a declared controlled_glue node: {location} line {node.lineno}")


def _ast_dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _ast_dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _is_orchestration_arithmetic(node: ast.BinOp) -> bool:
    """Permit counter increments and zero-shaped state initialization only."""
    if isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
        return True  # pathlib's source-free package-relative `Path / "child"` composition.
    if isinstance(node.op, ast.Mult):
        return any(
            isinstance(value, ast.Constant) and value.value == 0
            for value in (node.left, node.right)
        )
    return False


def _is_control_arithmetic(node: ast.BinOp, operation: str | None) -> bool:
    """Permit only arithmetic intrinsic to a declared control-state operation."""
    if operation == "cadence_gate":
        return isinstance(node.op, ast.Mod)
    if operation == "counter_state_transition" and isinstance(node.op, (ast.Add, ast.Sub)):
        return isinstance(node.right, ast.Constant) and node.right.value == 1
    return False


def _is_boolean_control_return(node: ast.AST | None) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, bool)
    if isinstance(node, ast.Compare):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    if isinstance(node, ast.BoolOp):
        return all(_is_boolean_control_return(value) for value in node.values)
    return False


def _is_counter_control_return(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, (ast.Add, ast.Sub))
        and isinstance(node.left, ast.Name)
        and isinstance(node.right, ast.Constant)
        and node.right.value == 1
    )


def _is_literal_control_output(node: ast.AST | None) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (str, bool, int, type(None)))
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_literal_control_output(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            _is_literal_control_output(key) and _is_literal_control_output(value)
            for key, value in zip(node.keys, node.values, strict=True)
        )
    return False


def _is_control_only_graph_output(
    node: ast.AST | None,
    *,
    control_functions: set[str],
    control_result_names: set[str],
) -> bool:
    if _is_literal_control_output(node):
        return True
    if isinstance(node, ast.Name):
        return node.id in control_result_names
    if isinstance(node, ast.Call):
        return _ast_dotted_name(node.func) in control_functions
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(
            _is_control_only_graph_output(
                item,
                control_functions=control_functions,
                control_result_names=control_result_names,
            )
            for item in node.elts
        )
    if isinstance(node, ast.Dict):
        return all(
            _is_literal_control_output(key)
            and _is_control_only_graph_output(
                value,
                control_functions=control_functions,
                control_result_names=control_result_names,
            )
            for key, value in zip(node.keys, node.values, strict=True)
        )
    return False


def _is_contract_validation_arithmetic(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """Allow arithmetic used only to reject an incompatible graph contract."""
    current = node
    compared = False
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.NamedExpr):
            return False
        if isinstance(parent, ast.Compare):
            compared = True
        elif isinstance(parent, (ast.BoolOp, ast.UnaryOp)):
            pass
        if isinstance(parent, (ast.If, ast.Assert)):
            return (
                current is parent.test
                and compared
                and not any(
                    isinstance(descendant, ast.NamedExpr)
                    for descendant in ast.walk(parent.test)
                )
                and _is_contract_rejection(parent)
            )
        if not isinstance(parent, (ast.Compare, ast.BoolOp, ast.UnaryOp)):
            return False
        current = parent
    return False


def _is_contract_validation_call(node: ast.Call, parents: dict[ast.AST, ast.AST]) -> bool:
    """Allow array predicates used only in an if/assert rejection condition."""
    current: ast.AST = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, (ast.If, ast.Assert)):
            return current is parent.test and _is_contract_rejection(parent)
        if isinstance(parent, ast.Call):
            wrapper = _ast_dotted_name(parent.func)
            wrapper_leaf = wrapper.rsplit(".", 1)[-1] if wrapper else ""
            if wrapper_leaf in _GRAPH_NUMPY_CONTAINER_CALLS | _GRAPH_NUMPY_CONTRACT_VALIDATION_CALLS:
                current = parent
                continue
            return False
        if not isinstance(parent, (ast.Compare, ast.BoolOp, ast.UnaryOp)):
            return False
        current = parent
    return False


def _is_contract_rejection(node: ast.If | ast.Assert) -> bool:
    """Accept only assertions or a plain ``if invalid: raise`` guard."""
    if isinstance(node, ast.Assert):
        return True
    return not node.orelse and len(node.body) == 1 and isinstance(node.body[0], ast.Raise)


def _yaml_top_level_section(text: str, section_name: str) -> str:
    lines = text.splitlines()
    collected: list[str] = []
    in_section = False
    for line in lines:
        if re.match(rf"^{re.escape(section_name)}\s*:\s*$", line):
            in_section = True
            continue
        if in_section and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", line):
            break
        if in_section:
            collected.append(line)
    return "\n".join(collected)


def _primary_pfm_node_from_yaml(text: str) -> str | None:
    framework_mapping = _yaml_top_level_section(text, "framework_mapping")
    match = re.search(
        r'(?m)^\s+primary_pfm_node\s*:\s*["\']?(N\d+)["\']?\s*$',
        framework_mapping,
    )
    return match.group(1) if match else None


def _yaml_sequence_entries(section_text: str) -> list[str]:
    entries: list[list[str]] = []
    current: list[str] = []
    sequence_indent: int | None = None
    for line in section_text.splitlines():
        match = re.match(r"^(\s*)-\s+", line)
        indent = len(match.group(1)) if match else None
        if match and sequence_indent is None:
            sequence_indent = indent
        if match and indent == sequence_indent:
            if current:
                entries.append(current)
            current = [line]
        elif current and line.strip():
            current.append(line)
    if current:
        entries.append(current)
    return ["\n".join(entry) for entry in entries]


def _yaml_entry_has_field(entry: str, field: str) -> bool:
    entry = _strip_yaml_comments(entry)
    return bool(re.search(rf"(?m)(?:^|\{{|,|\s){re.escape(field)}\s*:", entry))


def _yaml_entry_field_value(entry: str, field: str) -> str:
    entry = _strip_yaml_comments(entry)
    match = re.search(
        rf"(?m)(?:^|\{{|,|\s){re.escape(field)}\s*:\s*([^,\}}\n#]+)",
        entry,
    )
    if not match:
        return ""
    return match.group(1).strip().strip("\"'")


def _strip_yaml_comments(text: str) -> str:
    return "\n".join(
        content
        for line in text.splitlines()
        if (content := line.split("#", 1)[0].rstrip())
    )


def _validate_operator_markdown(
    markdown_text: str,
    *,
    source_path: str,
    implementation_path: Path,
    errors: list[str],
) -> None:
    sections = _markdown_sections(markdown_text)
    for heading in CHINESE_OPERATOR_HEADINGS:
        if not _section_text(markdown_text, heading):
            errors.append(f"operator.md requires {heading.title()}: {source_path}")
    _validate_chinese_operator_contract(markdown_text, source_path=source_path, errors=errors)
    _validate_contract_prose_structure(
        markdown_text,
        source_path=source_path,
        asset_kind="operator.md",
        errors=errors,
    )
    _validate_operator_documentation_quality(
        markdown_text,
        source_path=source_path,
        errors=errors,
    )
    _validate_operator_ports_against_implementation(
        markdown_text,
        implementation_path=implementation_path,
        source_path=source_path,
        errors=errors,
    )

    for heading in BANNED_OPERATOR_SECTIONS:
        if heading in sections:
            errors.append(
                "operator.md must not contain internal workflow heading "
                f"{heading.title()}: {source_path}"
            )
    if LOCAL_RUNTIME_TERMS_RE.search(markdown_text):
        errors.append(
            "operator.md must not prescribe local runtime harnesses "
            "(Docker/container/mount paths belong in test headers): "
            f"{source_path}"
        )

def _validate_operator_documentation_quality(
    markdown_text: str,
    *,
    source_path: str,
    errors: list[str],
) -> None:
    """Reject documentation that has the required shape but no usable contract."""
    if _section_text(markdown_text, "SciRel 调用") or re.search(
        r"(?m)^\s*(?:from\s+scirel(?:\.|\s+import\b)|import\s+scirel(?:\.|\s|$))",
        markdown_text,
    ):
        errors.append(
            "operator.md stage-one contract must not import the maintained SciRel package; L1 remains a source-shaped candidate bundle: "
            f"{source_path}"
        )
    untranslated_lines = _untranslated_prose_line_numbers(markdown_text)
    if untranslated_lines:
        errors.append(
            "operator.md human-facing explanatory prose must use the declared zh-CN profile; preserve identifiers and code but translate prose: "
            f"{source_path}; offending lines: {', '.join(map(str, untranslated_lines))}"
        )
    if _contains_source_coupled_public_prose(markdown_text):
        errors.append(
            "operator.md public contract must explain the relation independently; source aliases, source order, and source paths belong only in 验证与溯源: "
            f"{source_path}"
        )
    if _defers_scientific_behavior(markdown_text):
        errors.append(
            "operator.md 行为与边界 must describe the calculation, assumptions, encoded boundary behavior, and failure semantics instead of deferring them to implementation or tests: "
            f"{source_path}"
        )
    repeated = _repeated_contract_descriptions(markdown_text)
    if repeated:
        errors.append(
            "operator.md must give each input/output a distinct evidence-backed meaning; repeated field boilerplate is not a scientific contract: "
            f"{source_path}"
        )


def _defers_scientific_behavior(markdown_text: str) -> bool:
    boundaries = _section_text(markdown_text, "行为与边界")
    if not boundaries:
        return False
    return bool(
        re.search(
            r"(?:具体(?:关系|计算)?\s*)?参见(?:实现|测试)"
            r"|以(?:实现|测试|emitted\s+callable).{0,20}为准"
            r"|不引入.{0,20}(?:公式|科学关系)",
            boundaries,
            flags=re.IGNORECASE,
        )
    )


def _contains_untranslated_prose(markdown_text: str) -> bool:
    return bool(_untranslated_prose_line_numbers(markdown_text))


def _untranslated_prose_line_numbers(markdown_text: str) -> list[int]:
    findings: list[int] = []
    in_code_block = False
    in_display_math = False
    in_front_matter = False
    saw_document_content = False
    for line_number, line in enumerate(markdown_text.splitlines(), start=1):
        stripped = line.strip()
        if not saw_document_content and not stripped:
            continue
        if not saw_document_content and stripped == "---":
            saw_document_content = True
            in_front_matter = True
            continue
        saw_document_content = True
        if in_front_matter:
            if stripped == "---":
                in_front_matter = False
            continue
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if stripped.startswith("\\[") or stripped.startswith("\\]") or stripped.startswith("$$"):
            in_display_math = not in_display_math
            continue
        if in_display_math:
            continue
        if in_code_block or not stripped or stripped.startswith("---"):
            continue
        # A signature or an inline expression is executable notation, not
        # explanatory prose.  Do not mistake it for untranslated English.
        if stripped.startswith("`") and stripped.endswith("`"):
            continue
        if re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_.]*\s*\(.*\)\s*(?:->\s*[A-Za-z_][A-Za-z0-9_.\[\], |]*)?",
            stripped,
        ):
            continue
        has_cjk = any("\u4e00" <= character <= "\u9fff" for character in stripped)
        ascii_words = [
            word
            for word in re.split(r"[^A-Za-z]+", stripped)
            if len(word) >= 2
        ]
        if not has_cjk and len(ascii_words) >= 4 and not stripped.startswith("|"):
            findings.append(line_number)
    return findings


def _contains_source_coupled_public_prose(markdown_text: str) -> bool:
    """Reject source-dependent explanations outside the provenance section."""
    public_sections = (
        "说明",
        "解决的问题",
        "输入参数",
        "输出参数",
        "科学或数值定义",
        "实现对应",
        "行为与边界",
    )
    for heading in public_sections:
        section = _section_text(markdown_text, heading)
        if not section:
            continue
        without_code = re.sub(r"```[\s\S]*?```", "", section)
        without_code = re.sub(r"`[^`\n]*`", "", without_code)
        if SOURCE_COUPLED_PUBLIC_PROSE_RE.search(without_code) or SOURCE_PATH_LITERAL_RE.search(without_code):
            return True
    return False


def _repeated_contract_descriptions(markdown_text: str) -> set[str]:
    """Return repeated long port descriptions that usually indicate a template fallback."""
    descriptions: list[str] = []
    for section in ("输入参数", "输出参数"):
        for entry in _section_list(markdown_text, section):
            if not _contract_identifiers(entry):
                continue
            parts = re.split(r"[：:—]", entry, maxsplit=1)
            if len(parts) != 2:
                continue
            description = re.sub(r"\s+", " ", parts[1]).strip()
            if len(description) >= 40:
                descriptions.append(description)
    return {description for description in descriptions if descriptions.count(description) >= 2}


def _validate_machine_readable_io(
    markdown_text: str,
    *,
    section_name: str,
    display_name: str,
    source_path: str,
    errors: list[str],
) -> None:
    values = _section_list(markdown_text, section_name)
    section_text = _section_text(markdown_text, section_name)
    machine_entries = 0
    for value in values:
        if value.startswith("#"):
            continue
        identifiers = _contract_identifiers(value)
        if not identifiers:
            continue
        for identifier in identifiers:
            if identifier.casefold() in GENERIC_IO_IDENTIFIERS:
                errors.append(
                    f"operator.md {display_name} must name real contract fields, not {identifier}: {source_path}"
                )
                return
        if not _has_port_detail(value, section_text, PORT_SHAPE_TERMS):
            errors.append(
                f"operator.md {display_name} field {identifier} requires shape or axis information: {source_path}"
            )
            return
        if not _has_port_detail(value, section_text, PORT_UNIT_TERMS):
            errors.append(
                f"operator.md {display_name} field {identifier} requires a unit or source-unit caveat: {source_path}"
            )
            return
        if not _has_port_detail(value, section_text, PORT_CONSTRAINT_TERMS):
            errors.append(
                f"operator.md {display_name} field {identifier} requires a validity constraint: {source_path}"
            )
            return
        machine_entries += 1
    if not machine_entries:
        errors.append(
            f"operator.md {display_name} requires at least one real machine-readable field: {source_path}"
        )


def _contract_identifiers(entry: str) -> set[str]:
    """Return literal contract port names from a Markdown list item."""
    prefix = re.split(r"[：:—]", entry, maxsplit=1)[0].strip()
    names = {
        token.strip().strip("`")
        for token in prefix.split(",")
        if token.strip().strip("`")
    }
    return {
        name
        for name in names
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name)
    }


def _has_port_detail(entry: str, section: str, terms: tuple[str, ...]) -> bool:
    entry_lower = entry.casefold()
    if any(term in entry_lower for term in terms):
        return True
    section_lower = section.casefold()
    return (
        any(term in section_lower for term in terms)
        and any(term in section_lower for term in SHARED_PORT_TERMS)
    )


def _validate_operator_ports_against_implementation(
    markdown_text: str,
    *,
    implementation_path: Path,
    source_path: str,
    errors: list[str],
) -> None:
    """Keep the reviewer contract aligned with the emitted Python callable."""
    if not implementation_path.is_file():
        return
    try:
        tree = ast.parse(implementation_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    public_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    ]
    preferred = [node for node in public_functions if node.name == "scientific_operator"]
    selected_functions = preferred or (public_functions if len(public_functions) == 1 else [])
    if not selected_functions:
        errors.append(
            "scientific_operator.py must expose scientific_operator or one unambiguous public callable: "
            f"{source_path}"
        )
        return
    callable_names = {node.name for node in selected_functions}
    parameters: set[str] = set()
    return_fields: set[str] = set()
    for node in tree.body:
        if (
            not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or node.name.startswith("_")
            or node.name not in callable_names
        ):
            continue
        arguments = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        parameters.update(argument.arg for argument in arguments if argument.arg not in {"self", "cls"})
        for returned in ast.walk(node):
            if not isinstance(returned, ast.Return) or not isinstance(returned.value, ast.Dict):
                continue
            for key in returned.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    return_fields.add(key.value)

    def identifiers(section: str) -> set[str]:
        return {
            identifier
            for item in _section_list(markdown_text, section)
            for identifier in _contract_identifiers(item)
        }

    documented_inputs = identifiers(_operator_section_name(markdown_text, "inputs"))
    missing_inputs = sorted(parameters - documented_inputs)
    if missing_inputs:
        _append_identifier_findings(
            errors,
            "operator.md Inputs must enumerate callable parameters",
            missing_inputs,
            source_path,
        )
    documented_outputs = identifiers(_operator_section_name(markdown_text, "outputs"))
    output_text = _section_text(markdown_text, _operator_section_name(markdown_text, "outputs"))
    missing_outputs = sorted(key for key in return_fields if key not in output_text)
    if return_fields and missing_outputs:
        _append_identifier_findings(
            errors,
            "operator.md Outputs must enumerate the returned mapping fields",
            missing_outputs,
            source_path,
        )


def _append_identifier_findings(
    errors: list[str],
    prefix: str,
    identifiers: list[str],
    source_path: str,
) -> None:
    """Keep every missing identifier visible without oversized validator errors."""
    chunk: list[str] = []
    for identifier in identifiers:
        candidate = [*chunk, identifier]
        message = f"{prefix} {', '.join(candidate)}: {source_path}"
        if chunk and len(message.encode("utf-8")) > 480:
            errors.append(f"{prefix} {', '.join(chunk)}: {source_path}")
            chunk = [identifier]
        else:
            chunk = candidate
    if chunk:
        errors.append(f"{prefix} {', '.join(chunk)}: {source_path}")


def _validate_gap_note(path: Path, *, root: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    classification_values = {
        value.strip()
        for value in _section_list(text, "classification")
    }
    allowed_classifications = {
        "SUPPORT_KERNEL",
        "SOLVER_WORKFLOW_REWORK",
        "REJECT",
    }
    if not classification_values.intersection(allowed_classifications):
        errors.append(f"gap note requires allowed Classification: {path.relative_to(root)}")
    for heading in ("attempted extraction", "missing evidence", "minimum next source"):
        if not _section_text(text, heading):
            errors.append(
                f"gap note requires {heading.title()}: {path.relative_to(root)}"
            )


def _load_source_index(
    source_index_path: Path | None,
    *,
    errors: list[str],
) -> dict[str, set[str]] | None:
    if source_index_path is None:
        return None
    if not source_index_path.is_file():
        errors.append(f"source index does not exist: {source_index_path}")
        return None
    try:
        payload = json.loads(source_index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"source index is not valid JSON: {source_index_path}:{exc.lineno}")
        return None
    entries = payload.get("source_index") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        errors.append(f"source index requires source_index list: {source_index_path}")
        return None
    chunk_ids: set[str] = set()
    source_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        chunk_id = entry.get("chunk_id")
        if isinstance(chunk_id, str) and chunk_id.strip():
            chunk_ids.add(chunk_id.strip())
        source_path = entry.get("source_path")
        if isinstance(source_path, str) and source_path.strip():
            normalized = source_path.strip().replace("\\", "/")
            source_paths.add(normalized)
            source_paths.add(Path(normalized).name)
    return {"chunk_ids": chunk_ids, "source_paths": source_paths}


def _declares_independent_evidence(evidence_text: str) -> bool:
    # This classifies the declared evidence, not its scientific correctness.
    # Semantic review still has to assess the implementation and verification.
    return bool(re.search(
        r"(?i)source[_ -]?unavailable|源码对照状态[^\n]*不可用|独立(?:公式|解析|制造解)验证|闭式公式核算",
        evidence_text,
    ))


def _validate_operator_evidence(
    markdown_text: str,
    *,
    source_path: str,
    source_index: dict[str, set[str]] | None,
    errors: list[str],
) -> None:
    evidence_text = (
        _section_text(markdown_text, _operator_section_name(markdown_text, "evidence"))
        or _section_text(markdown_text, "evidence and validation")
        or _section_text(markdown_text, "evidence references")
    )
    if not evidence_text:
        return
    line_refs = list(LINE_REF_RE.finditer(evidence_text))
    if not line_refs:
        if re.search(r"(?i)source[_ -]?unavailable|源码对照状态[^\n]*不可用", evidence_text):
            return
        errors.append(
            "operator.md Evidence References require concrete file line anchors "
            f"like pkg/module.py:20-30 or src/file.f90:10-50: {source_path}"
        )
        return
    if all(Path(match.group("path").strip("`").replace("\\", "/")).name in {"scientific_operator.py", "graph.py"} for match in line_refs):
        if _declares_independent_evidence(evidence_text):
            return
        errors.append(
            "operator.md Evidence References must include an original-source anchor, not only emitted package files: "
            f"{source_path}"
        )
    if source_index is None:
        return
    source_paths = source_index["source_paths"]
    normalized_refs = {
        match.group("path").strip("`").replace("\\", "/")
        for match in line_refs
    }
    if any(path in source_paths or Path(path).name in source_paths for path in normalized_refs):
        return
    errors.append(
        "operator.md Evidence References must match a source-index path when "
        "a source index is supplied: "
        f"{source_path}"
    )


def _validate_known_evidence_chunk_ids(
    markdown_text: str,
    *,
    source_path: str,
    source_index: dict[str, set[str]] | None,
    errors: list[str],
) -> bool:
    if source_index is None:
        return False
    chunk_ids = _section_list(markdown_text, "evidence chunk ids")
    if not chunk_ids:
        return False
    unknown = sorted(set(chunk_ids) - source_index["chunk_ids"])
    if unknown:
        errors.append(
            f"unknown Evidence Chunk IDs in {source_path}: " + ", ".join(unknown)
        )
        return False
    return True


def _section_text(markdown_text: str, heading: str) -> str:
    sections = _markdown_sections(markdown_text)
    return "\n".join(sections.get(heading.casefold(), [])).strip()


def _section_list(markdown_text: str, heading: str) -> list[str]:
    text = _section_text(markdown_text, heading)
    values: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        if match := re.match(r"^\s*[-*]\s+(.+)$", line):
            if current:
                values.append(current)
            current = match.group(1).strip()
        elif current and re.match(r"^\s{2,}\S", line):
            current = f"{current} {line.strip()}"
        elif not line.strip() and current:
            values.append(current)
            current = None
    if current:
        values.append(current)
    return values


def _document_language(markdown_text: str) -> str | None:
    match = re.search(r"(?m)^language:\s*(zh-CN)\s*$", markdown_text)
    return match.group(1) if match else None


def _operator_section_name(markdown_text: str, purpose: str) -> str:
    return CHINESE_OPERATOR_SECTIONS[purpose]


def _validate_chinese_operator_contract(
    markdown_text: str,
    *,
    source_path: str,
    errors: list[str],
) -> None:
    if _document_language(markdown_text) != "zh-CN":
        errors.append(
            "operator.md requires YAML front matter language: zh-CN: "
            f"{source_path}"
        )
        return
    title = next((line for line in markdown_text.splitlines() if line.startswith("# ")), "")
    if not title or " / " in title:
        errors.append(
            "Chinese operator document requires one untranslated title: "
            f"{source_path}"
        )
    headings = [
        match.group(1).strip()
        for line in markdown_text.splitlines()
        if (match := re.match(r"^##\s+(.+?)\s*$", line))
    ]
    expected = list(CHINESE_OPERATOR_HEADINGS)
    required_headings = [heading for heading in headings if heading in CHINESE_OPERATOR_HEADINGS]
    if len(required_headings) == len(expected) and required_headings != expected:
        errors.append(
            "Chinese operator document requires the canonical heading order: "
            f"{source_path}"
        )


def _validate_chinese_task_graph_contract(markdown_text: str, *, source_path: str, errors: list[str]) -> None:
    if _document_language(markdown_text) != "zh-CN":
        errors.append(f"task_graph.md requires YAML front matter language: zh-CN: {source_path}")
        return
    title = next((line for line in markdown_text.splitlines() if line.startswith("# ")), "")
    headings = [match.group(1).strip() for line in markdown_text.splitlines() if (match := re.match(r"^##\s+(.+?)\s*$", line))]
    if not title or " / " in title:
        errors.append(f"Chinese task graph requires one untranslated title: {source_path}")
    expected = list(CHINESE_TASK_GRAPH_HEADINGS)
    required_headings = [heading for heading in headings if heading in CHINESE_TASK_GRAPH_HEADINGS]
    if len(required_headings) == len(expected) and required_headings != expected:
        errors.append(f"Chinese task graph requires the canonical heading order: {source_path}")


def _validate_contract_prose_structure(
    markdown_text: str,
    *,
    source_path: str,
    asset_kind: str,
    errors: list[str],
) -> None:
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip() and not line.startswith("#")]
    repeated = sorted({line for line in lines if len(line) > 40 and lines.count(line) >= 3})
    if repeated:
        errors.append(
            f"{asset_kind} contains repeated contract prose: {source_path}"
        )


def _validate_declared_markdown_ports(
    markdown_text: str,
    *,
    source_path: str,
    asset_kind: str,
    errors: list[str],
) -> None:
    for section in ("inputs", "outputs"):
        entries = _section_list(markdown_text, section)
        section_text = _section_text(markdown_text, section)
        identifiers = [name for entry in entries for name in _contract_identifiers(entry)]
        real = identifiers
        if not real or any(name.casefold() in GENERIC_IO_IDENTIFIERS for name in real):
            errors.append(
                f"{asset_kind} {section.title()} requires real named external ports: {source_path}"
            )
            continue
        for entry in entries:
            names = _contract_identifiers(entry)
            if not names:
                continue
            if not _has_port_detail(entry, section_text, PORT_SHAPE_TERMS):
                errors.append(
                    f"{asset_kind} {section.title()} port {', '.join(sorted(names))} requires shape or axis information: {source_path}"
                )
            if not _has_port_detail(entry, section_text, PORT_UNIT_TERMS):
                errors.append(
                    f"{asset_kind} {section.title()} port {', '.join(sorted(names))} requires a unit or source-unit caveat: {source_path}"
                )
            if not _has_port_detail(entry, section_text, PORT_CONSTRAINT_TERMS):
                errors.append(
                    f"{asset_kind} {section.title()} port {', '.join(sorted(names))} requires a validity constraint: {source_path}"
                )


def _markdown_sections(markdown_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown_text.splitlines():
        heading_match = re.match(r"^##\s+(.+?)\s*$", line)
        if heading_match:
            current = heading_match.group(1).strip().casefold()
            section_lines = sections.setdefault(current, [])
            if " / " in current:
                sections.setdefault(current.split(" / ", 1)[0].strip(), section_lines)
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate D1 code/YAML package structure and existing source anchors without executing input code."
    )
    parser.add_argument("root", type=Path, help="ImportIntake package directory")
    parser.add_argument(
        "--source-index",
        type=Path,
        default=None,
        help="Optional sandbox source_index.json used to validate evidence chunk ids.",
    )
    parser.add_argument("--evidence-matrix", type=Path, default=None,
                        help="Existing capability-evidence matrix; source anchors may remain in the asset row.")
    parser.add_argument(
        "--operator-only",
        action="store_true",
        help=(
            "Require operator-only delivery without task-graph packages."
        ),
    )
    args = parser.parse_args()

    result = validate_import_intake_package(
        args.root,
        source_index_path=args.source_index,
        operator_only=args.operator_only,
        evidence_matrix_path=args.evidence_matrix,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
