"""Minimal executable checks for the task-graph implementation-purity gate."""

from pathlib import Path
from tempfile import TemporaryDirectory

from validate_import_intake_package import _validate_task_graph_implementation_purity


YAML_WITH_ASSET = """\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
"""
TEMP_ROOT = Path(__file__).resolve().parents[1] / ".runtime" / "tmp"


def validate(yaml_text: str, graph_text: str) -> list[str]:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=TEMP_ROOT) as temporary:
        root = Path(temporary)
        graph = root / "task_graphs" / "example" / "graph.py"
        graph.parent.mkdir(parents=True)
        yaml_file = graph.with_name("task_graph.yaml")
        graph.write_text(graph_text, encoding="utf-8")
        yaml_file.write_text(yaml_text, encoding="utf-8")
        errors: list[str] = []
        _validate_task_graph_implementation_purity(graph, yaml_file=yaml_file, root=root, errors=errors)
        return errors


def main() -> None:
    clean = validate(YAML_WITH_ASSET, """\
import math
import numpy as np
from pathlib import Path
PACKAGE = Path(__file__).parent / 'operators'
def run_graph(inputs, *, operator_loader):
    result = operator_loader('example')(inputs['value'])
    if not math.isfinite(result['value']):
        raise ValueError('non-finite')
    return {'value': np.asarray([result['value']])}
""")
    assert not clean, clean
    orchestration = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: cadence
    kind: support_action
    callable: control:control_cadence
    control_contract:
      operation: cadence_gate
      ownership: explicit scheduler state machine
""", """\
def control_cadence(step, stride):
    return step % stride == 0
def run_graph(inputs):
    return {'accepted': control_cadence(inputs['step'], inputs['stride'])}
""")
    assert not orchestration, orchestration
    leaked_cadence_remainder = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: cadence
    kind: support_action
    callable: control:hidden_remainder
    control_contract:
      operation: cadence_gate
      ownership: invalid numerical payload
""", """\
def hidden_remainder(step, stride):
    return step % stride
def run_graph(inputs):
    return {'value': hidden_remainder(inputs['step'], inputs['stride'])}
""")
    assert any("cadence_gate" in error and "boolean predicate" in error for error in leaked_cadence_remainder), leaked_cadence_remainder
    hidden_orchestration_mapping = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: cadence
    kind: support_action
    callable: control:hidden_mapping
    control_contract:
      operation: cadence_gate
      ownership: invalid hidden scientific mapping
""", """\
def hidden_mapping(value):
    return value * 2.0
def run_graph(inputs):
    return {'value': hidden_mapping(inputs['x'])}
""")
    assert any("direct numerical arithmetic" in error for error in hidden_orchestration_mapping), hidden_orchestration_mapping
    numpy_orchestration_mapping = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: publish
    kind: support_action
    callable: control:publish
    control_contract:
      operation: action_plan_publication
      ownership: invalid hidden numerical payload
""", """\
import numpy as np
def publish(size):
    return np.zeros(size)
def run_graph(inputs):
    return {'value': publish(inputs['size'])}
""")
    assert any("orchestration_only" in error and "NumPy" in error for error in numpy_orchestration_mapping), numpy_orchestration_mapping
    orchestration_payload_passthrough = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: publish
    kind: support_action
    callable: control:publish
    control_contract:
      operation: action_plan_publication
      ownership: invalid scientific payload passthrough
""", """\
def publish(scientific_payload):
    return {'action': 'advance', 'scientific_payload': scientific_payload}
def run_graph(inputs):
    return publish(inputs['temperature_field'])
""")
    assert any("control-only output" in error for error in orchestration_payload_passthrough), orchestration_payload_passthrough
    invalid_orchestration = validate("""\
execution:
  orchestration_only: true
nodes:
  - id: fake
    kind: controlled_glue
    callable: glue:fake
    glue_contract:
      operation: index_mapping
      ownership: invalid control disguise
""", "def fake(value): return value\ndef run_graph(inputs): return {'value': fake(inputs['value'])}\n")
    assert any("must be support_action" in error for error in invalid_orchestration), invalid_orchestration
    hidden = validate("nodes: []\n", "def run_graph(inputs): return {'value': inputs['x'] * 2.0}\n")
    assert any("requires at least one declared scientific" in error for error in hidden), hidden
    assert any("direct numerical arithmetic" in error for error in hidden), hidden
    offset = validate(YAML_WITH_ASSET, """\
def run_graph(inputs, *, operator_loader):
    return {'value': inputs['value'] + 1}
""")
    assert any("direct numerical arithmetic" in error for error in offset), offset
    validation_arithmetic = validate(YAML_WITH_ASSET, """\
def run_graph(inputs, *, operator_loader):
    if inputs['row_count'] + 1 != inputs['pointer_count']:
        raise ValueError('incompatible row-pointer contract')
    return operator_loader('example')(inputs['value'])
""")
    assert not validation_arithmetic, validation_arithmetic
    validation_numpy = validate(YAML_WITH_ASSET, """\
import numpy as np
def run_graph(inputs, *, operator_loader):
    if not np.allclose(inputs['grid'], inputs['axis'][None, :]) or np.any(np.diff(inputs['axis']) <= 0.0):
        raise ValueError('incompatible grid contract')
    return operator_loader('example')(inputs['value'])
""")
    assert not validation_numpy, validation_numpy
    branching_validation_numpy = validate(YAML_WITH_ASSET, """\
import numpy as np
def run_graph(inputs, *, operator_loader):
    if np.allclose(inputs['left'], inputs['right']):
        return operator_loader('example')(inputs['left'])
    return operator_loader('example')(inputs['right'])
""")
    assert any("NumPy numerical mappings" in error for error in branching_validation_numpy), branching_validation_numpy
    branching_validation_arithmetic = validate(YAML_WITH_ASSET, """\
def run_graph(inputs, *, operator_loader):
    if inputs['row_count'] + 1 == inputs['pointer_count']:
        return operator_loader('example')(inputs['left'])
    return operator_loader('example')(inputs['right'])
""")
    assert any("direct numerical arithmetic" in error for error in branching_validation_arithmetic), branching_validation_arithmetic
    hidden_numpy = validate(YAML_WITH_ASSET, """\
import numpy as np
def run_graph(inputs, *, operator_loader):
    if np.exp(inputs['value']) > 0.0:
        return operator_loader('example')(inputs['value'])
    raise ValueError('invalid')
""")
    assert any("NumPy numerical mappings" in error for error in hidden_numpy), hidden_numpy
    escaped_validation_arithmetic = validate(YAML_WITH_ASSET, """\
def run_graph(inputs, *, operator_loader):
    if (hidden := inputs['value'] * 2.0) or True:
        return {'value': hidden}
""")
    assert any("direct numerical arithmetic" in error for error in escaped_validation_arithmetic), escaped_validation_arithmetic
    numeric = validate(YAML_WITH_ASSET, """\
import numpy as np
def run_graph(inputs, *, operator_loader):
    return {'value': np.exp(inputs['value'])}
""")
    assert any("NumPy numerical mappings" in error for error in numeric), numeric
    glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: convert_units
    kind: controlled_glue
    callable: glue:convert_units
    inputs: [value, scale]
    outputs: [converted_value]
    glue_contract:
      operation: unit_conversion
      ownership: caller_to_operator_port_adapter
""", """\
def convert_units(value, scale):
    return value * scale
def run_graph(inputs, *, operator_loader):
    return operator_loader('example')(convert_units(inputs['value'], inputs['scale']))
""")
    assert not glue, glue
    boundary_glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: mirror_boundary
    kind: controlled_glue
    callable: glue:mirror_boundary
    inputs: [state, pivot]
    outputs: [state]
    glue_contract:
      operation: boundary_padding
      ownership: graph-local fixed-boundary mirror; no physical mapping
""", """\
def mirror_boundary(state, pivot):
    for index in range(pivot + 1, len(state)):
        state[index] = state[pivot - index]
    return state
def run_graph(inputs, *, operator_loader):
    return operator_loader('example')(mirror_boundary(inputs['state'], inputs['pivot']))
""")
    assert not boundary_glue, boundary_glue
    block_glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: join_blocks
    kind: controlled_glue
    callable: glue:join_blocks
    inputs: [left, right]
    outputs: [joined]
    glue_contract:
      operation: block_concatenation
      ownership: graph-local CSR storage assembly; no physical mapping
""", """\
import numpy as np
def join_blocks(left, right):
    return np.concatenate((left, right))
def run_graph(inputs, *, operator_loader):
    return operator_loader('example')(join_blocks(inputs['left'], inputs['right']))
""")
    assert not block_glue, block_glue
    shape_glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: embed
    kind: controlled_glue
    callable: glue:embed
    inputs: [value, shape]
    outputs: [embedded]
    glue_contract:
      operation: shape_embedding
      ownership: graph-local shape adapter; no physical mapping
""", """\
import numpy as np
def embed(value, shape):
    return np.broadcast_to(np.asarray(value), shape)
def run_graph(inputs, *, operator_loader):
    return operator_loader('example')(embed(inputs['value'], inputs['shape']))
""")
    assert not shape_glue, shape_glue
    hidden_shape_mapping = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: embed
    kind: controlled_glue
    callable: glue:embed
    inputs: [pressure, psi]
    outputs: [pressure]
    glue_contract:
      operation: shape_embedding
      ownership: invalid hidden scientific mapping
""", """\
def embed(pressure, psi):
    return pressure * psi
def run_graph(inputs, *, operator_loader):
    return operator_loader('example')(embed(inputs['pressure'], inputs['psi']))
""")
    assert any("direct numerical arithmetic" in error for error in hidden_shape_mapping), hidden_shape_mapping
    delegated_asset_glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: bad_delegate
    kind: controlled_glue
    callable: glue:delegate_asset
    inputs: [value]
    outputs: [value]
    glue_contract:
      operation: component_selection
      ownership: invalid hidden subgraph
""", """\
def call_asset(value, operator_loader):
    return operator_loader('example')(value)
def delegate_asset(value, operator_loader):
    return call_asset(value, operator_loader)
def run_graph(inputs, *, operator_loader):
    return delegate_asset(inputs['value'], operator_loader)
""")
    assert any("may not invoke scientific asset loaders" in error for error in delegated_asset_glue), delegated_asset_glue
    broad_glue = validate("""\
nodes:
  - id: solve
    kind: scientific_operator
    asset_ref: operators/example
  - id: bad_glue
    kind: controlled_glue
    callable: glue:run_graph
    inputs: [value]
    outputs: [value]
    glue_contract:
      operation: scalar_affine_conversion
      ownership: invalid whole-graph exemption
""", """\
def run_graph(inputs, *, operator_loader):
    return {'value': inputs['value'] * 2.0}
""")
    assert any("not run_graph" in error for error in broad_glue), broad_glue
    dynamic = validate(YAML_WITH_ASSET, """\
def run_graph(inputs, *, operator_loader):
    from importlib import import_module
    return import_module('hidden_operator').run(inputs)
""")
    assert any("dynamically import sibling assets" in error for error in dynamic), dynamic


if __name__ == "__main__":
    main()
    print("task-graph purity gate: ok")
