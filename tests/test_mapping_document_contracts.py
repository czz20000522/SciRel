"""Scientific ports remain checked behind transparent TaskGraph mappings."""
import inspect
import pytest
from scripts.validate_asset_documents import _validate_runtime_inputs


def relation(density, *, temperature=2.0):
    return density * temperature


def graph(inputs):
    """One mapping is the public graph entry; relation owns the ports."""
    return relation(**inputs)


def bad_default(inputs=None):
    return relation(**inputs)


def bad_extra(inputs, ignored=0):
    return relation(**inputs)


def opaque(inputs):
    copied = dict(inputs)
    return relation(**copied)


def renamed_forward(inputs):
    return relation(density=inputs['rho'])


def contract(kind='task_graph'):
    return {'asset_id': 'scirel.test.graph', 'kind': kind, 'inputs': [
        {'name': 'density', 'required': True},
        {'name': 'temperature', 'required': False, 'default': 2.0}]}


def check(document, function):
    _validate_runtime_inputs(document, inspect.signature(function), function=function)


def test_mapping_ports_bind_actual_relation_and_call():
    check(contract(), graph)
    assert graph({'density': 3}) == 6
    assert graph({'density': 3, 'temperature': 5}) == 15


def test_ordinary_function_contract_is_unchanged():
    check(contract('operator'), relation)
    bad = contract('operator'); bad['inputs'][0]['name'] = 'rho'
    with pytest.raises(ValueError, match='documented input is not callable'):
        check(bad, relation)


@pytest.mark.parametrize('function',[bad_default,bad_extra])
def test_invalid_mapping_signature_rejected(function):
    with pytest.raises(ValueError, match='one required callable parameter'):
        check(contract(), function)


@pytest.mark.parametrize('function',[opaque,renamed_forward])
def test_unbound_or_transformed_mapping_rejected(function):
    with pytest.raises(ValueError, match='verifiable scientific delegate'):
        check(contract(), function)


def test_graph_schema_consistent_but_wrong_scientific_port_rejected():
    bad = contract(); bad['inputs'].append({'name': 'rho', 'required': False, 'default': None})
    with pytest.raises(ValueError, match='documented input is not callable: rho'):
        check(bad, graph)


def test_missing_required_scientific_port_rejected():
    bad = contract(); bad['inputs'] = bad['inputs'][1:]
    with pytest.raises(ValueError, match='required scientific inputs are undocumented'):
        check(bad, graph)


@pytest.mark.parametrize('field,value,expected',[
    ('required',True,'required status differs'),
    ('default',3.0,'default differs')])
def test_required_status_and_default_rejected(field,value,expected):
    bad = contract(); bad['inputs'][1][field] = value
    with pytest.raises(ValueError, match=expected):
        check(bad, graph)


def test_signature_without_actual_adapter_is_not_evidence():
    with pytest.raises(ValueError, match='actual callable binding'):
        _validate_runtime_inputs(contract(), inspect.signature(graph))

@pytest.mark.parametrize('asset_id',[
    'scirel.kinetic.pdrk-fluid-scan',
    'scirel.kinetic.pdrk-rational-reassemble-original-program'])
def test_exact_complex_binding_rejects_changed_port_and_default(asset_id):
    import json,importlib,copy
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    d=json.loads((root/'catalog/pdrk-mac-pilot'/f'{asset_id}.json').read_text())
    api=d['public_api']['python'];f=getattr(importlib.import_module(api['module']),api['symbol'])
    check(d,f)
    for field,value in [('name','unbound_port'),('required',True),('default','wrong')]:
        bad=copy.deepcopy(d);bad['inputs'][1][field]=value
        with pytest.raises(ValueError,match='ports/defaults differ'):
            check(bad,f)

@pytest.mark.parametrize('change',['extra','missing','renamed','required','default'])
def test_complex_mapping_all_contract_drift_fails(change):
    import json,importlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    d=json.loads((root/'catalog/pdrk-mac-pilot/scirel.kinetic.pdrk-fluid-scan.json').read_text())
    f=importlib.import_module(d['public_api']['python']['module']).scan_fluid_corrected
    if change=='extra':d['inputs'].append({'name':'extra','required':True})
    elif change=='missing':d['inputs'].pop(0)
    elif change=='renamed':d['inputs'][0]['name']='different_state'
    elif change=='required':d['inputs'][0]['required']=False
    else:d['inputs'][1]['default']=3
    with pytest.raises(ValueError,match='ports/defaults differ'):check(d,f)


def test_complex_mapping_module_drift_fails(tmp_path,monkeypatch):
    import json,importlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    d=json.loads((root/'catalog/pdrk-mac-pilot/scirel.kinetic.pdrk-fluid-scan.json').read_text())
    module=importlib.import_module(d['public_api']['python']['module'])
    changed=tmp_path/'changed.py';changed.write_bytes(Path(module.__file__).read_bytes()+b'\n# changed binding\n')
    monkeypatch.setattr(module,'__file__',str(changed))
    with pytest.raises(ValueError,match='source binding differs'):check(d,module.scan_fluid_corrected)
