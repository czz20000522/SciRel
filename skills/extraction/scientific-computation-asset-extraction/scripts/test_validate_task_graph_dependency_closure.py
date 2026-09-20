from pathlib import Path
from tempfile import TemporaryDirectory

from validate_import_intake_package import _validate_task_graph_dependency_closure


def _write_graph(root: Path, name: str, asset_ref: str | None = None) -> Path:
    graph_dir = root / "task_graphs" / name
    graph_dir.mkdir(parents=True, exist_ok=True)
    ref = f"\n  asset_ref: {asset_ref}" if asset_ref else ""
    (graph_dir / "task_graph.yaml").write_text(
        "kind: scientific_task_graph\n"
        "nodes:\n"
        "- id: node\n"
        "  name: node\n"
        "  kind: nested_task_graph\n"
        "  callable: asset:run_graph\n"
        f"{ref}\n",
        encoding="utf-8",
    )
    return graph_dir / "task_graph.yaml"


def test_rejects_nested_task_graph_cycle():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        a = _write_graph(root, "A", "task_graphs/B")
        b = _write_graph(root, "B", "task_graphs/A")
        errors: list[str] = []

        _validate_task_graph_dependency_closure(
            root, task_graph_yaml_files=[a, b], errors=errors
        )

        assert any("nested dependency cycle" in error for error in errors)


def test_rejects_missing_nested_graph_and_operator():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        graph_dir = root / "task_graphs" / "A"
        graph_dir.mkdir(parents=True)
        yaml_file = graph_dir / "task_graph.yaml"
        yaml_file.write_text(
            "kind: scientific_task_graph\n"
            "nodes:\n"
            "- id: missing_graph\n"
            "  asset_ref: task_graphs/Missing\n"
            "- id: missing_operator\n"
            "  asset_ref: operators/Missing\n",
            encoding="utf-8",
        )
        errors: list[str] = []

        _validate_task_graph_dependency_closure(
            root, task_graph_yaml_files=[yaml_file], errors=errors
        )

        assert any("missing task graph" in error for error in errors)
        assert any("missing operator" in error for error in errors)


def test_accepts_existing_acyclic_nested_graph_and_operator():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        operator_dir = root / "operators" / "Leaf"
        operator_dir.mkdir(parents=True)
        (operator_dir / "operator.md").write_text("contract", encoding="utf-8")
        leaf = _write_graph(root, "LeafGraph")
        parent = _write_graph(root, "Parent", "task_graphs/LeafGraph")
        # Add an operator ref to the parent graph without changing the graph edge.
        parent.write_text(
            parent.read_text(encoding="utf-8")
            + "- id: operator\n  asset_ref: operators/Leaf\n",
            encoding="utf-8",
        )
        errors: list[str] = []

        _validate_task_graph_dependency_closure(
            root, task_graph_yaml_files=[leaf, parent], errors=errors
        )

        assert errors == []


def test_standalone_task_graph_does_not_assume_sibling_assets():
    with TemporaryDirectory() as temporary:
        root = Path(temporary) / "single_graph"
        root.mkdir()
        yaml_file = root / "task_graph.yaml"
        yaml_file.write_text(
            "kind: scientific_task_graph\n"
            "nodes:\n"
            "- id: operator\n"
            "  asset_ref: operators/ProvidedByResolver\n",
            encoding="utf-8",
        )
        errors: list[str] = []

        _validate_task_graph_dependency_closure(
            root, task_graph_yaml_files=[yaml_file], errors=errors
        )

        assert errors == []


if __name__ == "__main__":
    test_rejects_nested_task_graph_cycle()
    test_rejects_missing_nested_graph_and_operator()
    test_accepts_existing_acyclic_nested_graph_and_operator()
    test_standalone_task_graph_does_not_assume_sibling_assets()
    print("4 passed")
