"""Regression checks for project and standalone source-free validation modes."""

from pathlib import Path
from tempfile import TemporaryDirectory

from validate_source_free_bundle import (
    _find_external_path_references,
    validate_source_free_bundle,
)


def main() -> None:
    with TemporaryDirectory() as temporary:
        operator = Path(temporary) / "operator"
        operator.mkdir()
        (operator / "operator.md").write_text("# Operator\n", encoding="utf-8")
        (operator / "scientific_operator.py").write_text(
            "def run(inputs):\n    return inputs\n", encoding="utf-8"
        )
        valid = validate_source_free_bundle(operator, standalone_kind="operator")
        assert valid["valid"], valid

        (operator / "unrelated.txt").write_text("not part of the package\n", encoding="utf-8")
        invalid = validate_source_free_bundle(operator, standalone_kind="operator")
        assert not invalid["valid"], invalid
        assert any("unexpected standalone operator entry" in error for error in invalid["errors"])

        (operator / "unrelated.txt").unlink()
        (operator / "scientific_operator.py").write_text(
            "from pathlib import Path\n"
            "SOURCE = Path('/tmp/original/source.f90')\n"
            "def run(inputs):\n    return inputs\n",
            encoding="utf-8",
        )
        external_path = validate_source_free_bundle(operator, standalone_kind="operator")
        assert not external_path["valid"], external_path
        assert any("external path reference" in error for error in external_path["errors"])

        (operator / "scientific_operator.py").write_text(
            "SOURCE = r'\\(3,3'\n"
            "def run(inputs):\n    return inputs\n",
            encoding="utf-8",
        )
        regex_literal = validate_source_free_bundle(operator, standalone_kind="operator")
        assert regex_literal["valid"], regex_literal

        (operator / "scientific_operator.py").write_text(
            'with pytest.raises(ValueError, match="shape must be \\\\(3,3\\\\)"):\n'
            "    run({})\n",
            encoding="utf-8",
        )
        escaped_regex_literal = validate_source_free_bundle(
            operator, standalone_kind="operator"
        )
        assert escaped_regex_literal["valid"], escaped_regex_literal

        (operator / "scientific_operator.py").write_text(
            "MODULE = asset_ref + '/scientific_operator.py'\n"
            "def run(inputs):\n    return inputs\n",
            encoding="utf-8",
        )
        package_relative_suffix = validate_source_free_bundle(operator, standalone_kind="operator")
        assert package_relative_suffix["valid"], package_relative_suffix

        (operator / "scientific_operator.py").write_text(
            "SOURCE = r'D:\\external\\source.py'\n"
            "def run(inputs):\n    return inputs\n",
            encoding="utf-8",
        )
        windows_external_path = validate_source_free_bundle(operator, standalone_kind="operator")
        assert not windows_external_path["valid"], windows_external_path
        assert any("external path reference" in error for error in windows_external_path["errors"])

    with TemporaryDirectory() as temporary:
        task_graph = Path(temporary) / "task_graph"
        task_graph.mkdir()
        (task_graph / "task_graph.md").write_text("# Task graph\n", encoding="utf-8")
        (task_graph / "task_graph.yaml").write_text("nodes: []\n", encoding="utf-8")
        (task_graph / "graph.py").write_text(
            "def run_graph(inputs):\n    return inputs\n", encoding="utf-8"
        )
        valid = validate_source_free_bundle(task_graph, standalone_kind="task_graph")
        assert valid["valid"], valid

    with TemporaryDirectory() as temporary:
        runtime_docs = Path(temporary)
        (runtime_docs / "Dockerfile").write_text(
            "RUN mkdir -p /var/lib/apt/lists\n", encoding="utf-8"
        )
        (runtime_docs / "source_runtime.md").write_text(
            "Mount D:\\Users\\example\\source as /source:ro\n", encoding="utf-8"
        )
        (runtime_docs / "config.yaml").write_text(
            "source: /tmp/external/source.f90\n", encoding="utf-8"
        )
        findings = _find_external_path_references(runtime_docs)
        assert len(findings) == 1, findings
        assert findings[0].startswith("config.yaml: "), findings
        assert findings[0].endswith("external/source.f90"), findings

        (runtime_docs / "config.yaml").unlink()
        assert _find_external_path_references(runtime_docs) == []


if __name__ == "__main__":
    main()
