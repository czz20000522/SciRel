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

@pytest.mark.parametrize('change',[None,'extra','missing','renamed','required','default','source'])
def test_equilibrium_grid_mapping_binding_rejects_contract_or_source_drift(change,tmp_path,monkeypatch):
    import json, importlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    d=json.loads((root/'catalog/examples/scirel.geometry.axisymmetric-equilibrium-grid-support.json').read_text())
    module=importlib.import_module(d['public_api']['python']['module'])
    f=getattr(module,d['public_api']['python']['symbol'])
    if change is None:
        check(d,f)
        with pytest.raises(ValueError,match='missing'):
            f({})
        return
    if change=='extra': d['inputs'].append({'name':'extra','required':True})
    elif change=='missing': d['inputs'].pop(0)
    elif change=='renamed': d['inputs'][0]['name']='different_equilibrium'
    elif change=='required': d['inputs'][0]['required']=False
    elif change=='default': d['inputs'][0]['default']=None
    else:
        changed=tmp_path/'changed.py';changed.write_bytes(Path(module.__file__).read_bytes()+b'\n# changed binding\n')
        monkeypatch.setattr(module,'__file__',str(changed))
    with pytest.raises(ValueError,match='source binding differs' if change=='source' else 'ports/defaults differ'):
        check(d,f)


def unbound_keywords(inputs=None, **kwargs):
    return relation(**inputs)


def test_unbound_keyword_mapping_cannot_bypass_scientific_ports():
    with pytest.raises(ValueError,match='one required callable parameter'):
        check(contract(),unbound_keywords)

@pytest.mark.parametrize('asset_id',[
    'scirel.closures.mirror-quasineutral-closure',
    'scirel.equilibrium.axisymmetric-anisotropic-picard',
    'scirel.equilibrium.free-boundary-anisotropic-picard',
    'scirel.equilibrium.kinetic-mirror-hall-equilibrium',
    'scirel.equilibrium.reduced-hall-anisotropic-picard',
    'scirel.field.multi-coil-vacuum-field',
    'scirel.kinetic.frank-egedal-pressure-closure',
    'scirel.kinetic.grid-mirror-kinetic-closure'])
def test_existing_composed_graph_ports_remain_exact(asset_id,tmp_path,monkeypatch):
    import json,importlib,copy
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    d=next(json.loads(path.read_text()) for path in (root/'catalog/examples').glob('*.json') if json.loads(path.read_text()).get('asset_id') == asset_id)
    api=d['public_api']['python']
    module=importlib.import_module(api['module']);f=getattr(module,api['symbol']);check(d,f)
    for mutation in ('extra','missing','renamed','required','default'):
        bad=copy.deepcopy(d)
        if mutation=='extra':bad['inputs'].append({'name':'extra','required':True})
        elif mutation=='missing':bad['inputs'].pop(0)
        elif mutation=='renamed':bad['inputs'][0]['name']='different'
        elif mutation=='required':bad['inputs'][0]['required']=not bad['inputs'][0]['required']
        else:bad['inputs'][0]['default']='wrong'
        with pytest.raises(ValueError,match='ports/defaults differ'):check(bad,f)
    changed=tmp_path/'changed.py';changed.write_bytes(Path(module.__file__).read_bytes()+b'\n# changed binding\n')
    monkeypatch.setattr(module,'__file__',str(changed))
    with pytest.raises(ValueError,match='source binding differs'):check(d,f)



def keyword_graph(density, **parameters):
    return relation(density, **parameters)


def test_unbound_taskgraph_keywords_fail_closed():
    with pytest.raises(ValueError, match='explicit scientific port binding'):
        check(contract(), keyword_graph)
