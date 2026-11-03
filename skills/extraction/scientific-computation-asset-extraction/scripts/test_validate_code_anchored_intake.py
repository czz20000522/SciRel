"""D1 discovers runnable assets without requiring publication documents."""

from pathlib import Path
import json

import pytest

from validate_import_intake_package import validate_import_intake_package
from validate_source_free_bundle import validate_source_free_bundle
from validate_asset_entry import validate as validate_asset_entry
from validate_library_api import validate as validate_library_api


def write_operator(root: Path) -> Path:
    operator = root / "operators" / "square"
    operator.mkdir(parents=True)
    (operator / "scientific_operator.py").write_text(
        '"""Square a finite scalar; dimensionless input and output. Source: upstream/model.py:3-4."""\n'
        "def scientific_operator(x):\n    return {'value': x * x}\n",
        encoding="utf-8",
    )
    (operator / "test_scientific_operator.py").write_text(
        "from scientific_operator import scientific_operator\n"
        "def test_square():\n    assert scientific_operator(3)['value'] == 9\n",
        encoding="utf-8",
    )
    return operator


def write_graph(root: Path) -> Path:
    graph = root / "task_graphs" / "apply_square"
    graph.mkdir(parents=True)
    (graph / "task_graph.yaml").write_text(
        "inputs:\n  - {name: x, meaning: finite scalar, shape: scalar, units: dimensionless}\n"
        "outputs:\n  - {name: value, meaning: squared scalar, shape: scalar, units: dimensionless}\n"
        "nodes:\n  - id: square\n    name: square\n    kind: scientific_operator\n"
        "    asset_ref: operators/square\n    callable: scientific_operator\n"
        "    inputs: [x]\n    outputs: [value]\n"
        "edges: []\nexecution: {order: [square]}\n",
        encoding="utf-8",
    )
    (graph / "graph.py").write_text(
        '"""Apply the source composition at upstream/model.py:6-8."""\n'
        "from pathlib import Path\nimport yaml\n"
        "def run_graph(inputs, *, operator_loader):\n"
        "    contract = yaml.safe_load(Path(__file__).with_name('task_graph.yaml').read_text())\n"
        "    return operator_loader(contract['nodes'][0]['asset_ref'])(inputs['x'])\n",
        encoding="utf-8",
    )
    (graph / "test_task_graph.py").write_text(
        "from graph import run_graph\n"
        "def test_graph():\n"
        "    result = run_graph({'x': 3}, operator_loader=lambda _: lambda x: {'value': x*x})\n"
        "    assert result == {'value': 9}\n",
        encoding="utf-8",
    )
    return graph


def test_discovers_code_and_yaml_without_formal_markdown(tmp_path):
    write_operator(tmp_path)
    write_graph(tmp_path)
    result = validate_import_intake_package(tmp_path)
    assert result["valid"], result["errors"]
    assert result["operator_packages"] == ["operators/square"]
    assert result["task_graph_packages"] == ["task_graphs/apply_square"]
    assert result["validation_scope"] == "structure_and_source_mapping"
    assert result["scientific_validation"] == "requires_source_and_numerical_review"


def test_document_layout_and_test_comment_order_do_not_gate_d1(tmp_path):
    operator = write_operator(tmp_path)
    (operator / "operator.md").write_text("Legacy notes in any language.\n", encoding="utf-8")
    result = validate_import_intake_package(tmp_path)
    assert result["valid"], result["errors"]


@pytest.mark.parametrize("filename", ["scientific_operator.py", "test_scientific_operator.py"])
def test_missing_or_empty_executable_material_is_not_an_asset_pass(tmp_path, filename):
    operator = write_operator(tmp_path)
    (operator / filename).write_text("", encoding="utf-8")
    result = validate_import_intake_package(tmp_path)
    assert not result["valid"]
    assert any(filename in error for error in result["errors"])


def test_no_assets_cannot_pass(tmp_path):
    (tmp_path / "operators").mkdir()
    (tmp_path / "task_graphs").mkdir()
    assert not validate_import_intake_package(tmp_path)["valid"]


def test_absent_source_mapping_does_not_claim_source_verification(tmp_path):
    operator = write_operator(tmp_path)
    (operator / "scientific_operator.py").write_text(
        "def scientific_operator(x):\n    return {'value': x*x}\n", encoding="utf-8"
    )
    result = validate_import_intake_package(tmp_path)
    assert not result["valid"]
    assert any("source anchor" in error for error in result["errors"])


def test_code_anchor_must_match_supplied_source_index(tmp_path):
    write_operator(tmp_path)
    index = tmp_path / "source_index.json"
    index.write_text(json.dumps({"source_index": [{"source_path": "unrelated.py"}]}), encoding="utf-8")
    result = validate_import_intake_package(tmp_path, source_index_path=index)
    assert not result["valid"]
    assert any("source-index" in error for error in result["errors"])


def test_existing_matrix_row_can_own_source_mapping_without_copying_it(tmp_path):
    operator = write_operator(tmp_path)
    (operator / "scientific_operator.py").write_text(
        "def scientific_operator(x):\n    return {'value': x*x}\n", encoding="utf-8"
    )
    matrix = tmp_path / "capability_evidence_matrix.md"
    matrix.write_text("| upstream/model.py:3-4 | operators/square | source replay evidence |\n", encoding="utf-8")
    result = validate_import_intake_package(tmp_path, evidence_matrix_path=matrix)
    assert result["valid"], result["errors"]
    matrix.write_text("| upstream/model.py:3-4 | operators/square_other | source replay evidence |\n", encoding="utf-8")
    assert not validate_import_intake_package(tmp_path, evidence_matrix_path=matrix)["valid"]


def test_intake_does_not_execute_candidate_python(tmp_path):
    operator = write_operator(tmp_path)
    path = operator / "scientific_operator.py"
    path.write_text(path.read_text(encoding="utf-8") + "\nraise RuntimeError('must never execute')\n", encoding="utf-8")
    result = validate_import_intake_package(tmp_path)
    assert result["valid"], result["errors"]
    assert result["scientific_validation"] == "requires_source_and_numerical_review"


def test_comment_only_test_is_not_executable_evidence(tmp_path):
    operator = write_operator(tmp_path)
    (operator / "test_scientific_operator.py").write_text("# test passed\n", encoding="utf-8")
    result = validate_import_intake_package(tmp_path)
    assert not result["valid"]
    assert any("no executable test material" in error for error in result["errors"])


def test_source_free_project_accepts_one_family_before_final_report(tmp_path):
    write_operator(tmp_path)
    for name in ("extraction_ledger.md", "program_framework_map.md"):
        (tmp_path / name).write_text("Source scope and evidence references", encoding="utf-8")
    result = validate_source_free_bundle(tmp_path)
    assert result["valid"], result["errors"]


def test_d1_discovers_c_profile_and_requires_header(tmp_path):
    operator = tmp_path / "operators" / "square"
    operator.mkdir(parents=True)
    (operator / "scientific_operator.c").write_text(
        "/* Square a dimensionless scalar. Source: upstream/model.c:1-3. */\n"
        "double scientific_operator(double x) { return x*x; }\n", encoding="utf-8"
    )
    (operator / "scientific_operator.h").write_text("double scientific_operator(double x);\n", encoding="utf-8")
    (operator / "test_scientific_operator.c").write_text(
        '#include <assert.h>\n#include "scientific_operator.h"\n'
        "int main(void) { assert(scientific_operator(3) == 9); return 0; }\n", encoding="utf-8"
    )
    result = validate_import_intake_package(tmp_path)
    assert result["valid"], result["errors"]
    (operator / "scientific_operator.h").unlink()
    assert not validate_import_intake_package(tmp_path)["valid"]


def test_graph_dependencies_are_checked_without_documentation(tmp_path):
    graph = write_graph(tmp_path)
    result = validate_import_intake_package(tmp_path)
    assert not result["valid"]
    assert any("missing operator" in error for error in result["errors"])
    (graph / "task_graph.yaml").unlink()
    assert any("task_graph.yaml" in error for error in validate_import_intake_package(tmp_path)["errors"])


def test_standalone_source_free_package_does_not_require_markdown(tmp_path):
    operator = write_operator(tmp_path)
    result = validate_source_free_bundle(operator, standalone_kind="operator")
    assert result["valid"], result["errors"]
    (operator / "scientific_operator.py").unlink()
    assert not validate_source_free_bundle(operator, standalone_kind="operator")["valid"]


@pytest.mark.parametrize("kind", ["operator", "task_graph"])
def test_asset_entry_accepts_a_single_nonempty_family(tmp_path, monkeypatch, kind):
    monkeypatch.setenv("CODEFUSION_ASSET_SANDBOX", "1")
    (tmp_path / "asset_entry.py").write_text(
        f"KIND = {kind!r}\n"
        "class Bundle:\n"
        "    def list_assets(self): return [{'kind': KIND, 'name': 'only'}]\n"
        "    def describe_asset(self, kind, name):\n"
        "        if '/' in name: raise ValueError('unsafe')\n"
        "        return {'name': name, 'contract': 'Code anchored scientific description'}\n"
        "    def find_assets(self, query, kind): return self.list_assets()\n"
        "def load_asset_bundle(root): return Bundle()\n", encoding="utf-8"
    )
    validate_asset_entry(tmp_path, int(kind == "operator"), int(kind == "task_graph"))


def test_asset_entry_cannot_accept_zero_assets(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEFUSION_ASSET_SANDBOX", "1")
    (tmp_path / "asset_entry.py").write_text(
        "class Bundle:\n    def list_assets(self): return []\n"
        "def load_asset_bundle(root): return Bundle()\n", encoding="utf-8"
    )
    with pytest.raises(AssertionError, match="at least one"):
        validate_asset_entry(tmp_path, 0, 0)


@pytest.mark.parametrize("kind", ["operator", "task_graph"])
def test_library_entry_resolves_each_present_family(tmp_path, monkeypatch, kind):
    monkeypatch.setenv("CODEFUSION_ASSET_SANDBOX", "1")
    (tmp_path / "asset_entry.py").write_text(
        f"KIND = {kind!r}\n"
        "class Bundle:\n"
        "    def list_assets(self, kind=None): return [{'kind': KIND, 'name': 'only'}] if kind == KIND else []\n"
        "    def describe_asset(self, *args): return {}\n"
        "    def find_assets(self, *args): return []\n"
        "    def operator_callable(self, ref):\n"
        "        assert KIND == 'operator'\n"
        "        return lambda x: x\n"
        "    def task_graph_callable(self, ref, callable_name='run_graph'):\n"
        "        assert KIND == 'task_graph'\n"
        "        return lambda x: x\n"
        "    def asset_callable(self, ref): return lambda x: x\n"
        "def load_asset_bundle(root): return Bundle()\n"
        "def load_operator(*args): return lambda x: x\n"
        "def load_task_graph(*args): return lambda x: x\n", encoding="utf-8"
    )
    validate_library_api(tmp_path)
