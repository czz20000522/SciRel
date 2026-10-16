"""Delivery regressions use generic measurements, not benchmark answers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / 'skills/development/usage/scirel-solving/scripts/delivery.py'


@pytest.fixture
def delivery():
    spec = importlib.util.spec_from_file_location('delivery', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def case(tmp_path):
    (tmp_path/'data.csv').write_text('x_m,y_T\n-0.01,2\n0,4\n0.01,2\n')
    (tmp_path/'request.txt').write_text('请比较保存的数据，不假定设备接线。')
    spec = {'schema':'scirel.result-delivery.v1',
            'tables': {'data': {'path':'data.csv','units':{'x_m':'m','y_T':'T'},'coordinates':['x_m'],
                                'expected_rows':3}},
            'premises':[{'path':'request.txt','quote':'请比较保存的数据，不假定设备接线。'}],
            'claims':[{'op':'range','table':'data','column':'y_T'},
                      {'op':'relative_deviation','table':'data','column':'y_T','at':{'x_m':0}},
                      {'op':'threshold','table':'data','column':'y_T','relation':'>','value':3}],
            'plots':[{'table':'data','x':'x_m','y':'y_T'}]}
    path=tmp_path/'spec.json';path.write_text(json.dumps(spec))
    return path,spec


def write(path,spec):
    path.write_text(json.dumps(spec));return path


def test_reads_saved_values_and_generates_axis_units(delivery,case,tmp_path):
    path,spec=case
    result=delivery.build(path,tmp_path/'out')
    assert result['claims'][1]['reference']==4
    assert result['claims'][1]['max_relative_deviation']==.5
    assert result['claims'][2]['count']==1
    assert result['tables']['data']['rows']==3
    assert result['plots'][0]['x_unit']=='m'
    assert result['plots'][0]['x_range']==[-.01,.01]
    assert delivery.verify(path,tmp_path/'out')['status']=='CONSISTENT'


def test_changed_csv_invalidates_report(delivery,case,tmp_path):
    path,_=case;delivery.build(path,tmp_path/'out')
    (tmp_path/'data.csv').write_text('x_m,y_T\n-0.01,2\n0,5\n0.01,2\n')
    with pytest.raises(ValueError):delivery.verify(path,tmp_path/'out')


@pytest.mark.parametrize('extra',[{'conclusion':'independently proven'}, {'status':'PASS'}, {'maximum':99}])
def test_cannot_supply_claimed_result_or_free_explanation(delivery,case,tmp_path,extra):
    path,spec=case;spec['claims'][0].update(extra)
    with pytest.raises(ValueError):delivery.build(write(path,spec),tmp_path/'out')


def test_unprovided_premise_is_rejected(delivery,case,tmp_path):
    path,spec=case;spec['premises'][0]['quote']='两台设备串联'
    with pytest.raises(ValueError):delivery.build(write(path,spec),tmp_path/'out')


def test_last_point_does_not_satisfy_whole_scan(delivery,case,tmp_path):
    path,spec=case
    (tmp_path/'data.csv').write_text('x_m,y_T\n0.01,2\n')
    with pytest.raises(ValueError,match='coverage'):delivery.build(path,tmp_path/'out')


def test_group_coverage_checks_actual_coordinates(delivery,case,tmp_path):
    path,spec=case
    spec['tables']['data']['expected_groups']={'columns':['x_m'],'values':[[-.01],[0],[.02]],'rows_each':1}
    with pytest.raises(ValueError,match='coverage'):delivery.build(write(path,spec),tmp_path/'out')


def test_failed_comparison_stays_failed(delivery,case,tmp_path):
    path,spec=case
    (tmp_path/'ref.csv').write_text('x_m,y_T\n-0.01,2\n0,40\n0.01,2\n')
    spec['tables']['ref']={**spec['tables']['data'],'path':'ref.csv'}
    spec['claims']=[{'op':'compare','table':'data','reference':'ref','column':'y_T','keys':['x_m'],'atol':0,'rtol':.001}]
    r=delivery.build(write(path,spec),tmp_path/'out')
    assert r['claims'][0]['passed'] is False
    assert r['status']=='CHECK_FAILED'
    assert delivery.verify(path,tmp_path/'out')['status']=='CHECK_FAILED'
    assert '未通过' in (tmp_path/'out/REPORT.md').read_text()


def test_reordering_is_not_called_independent(delivery,case,tmp_path):
    path,spec=case
    spec['claims']=[{'op':'compare','table':'data','reference':'data','column':'y_T','keys':['x_m'],'atol':0,'rtol':0}]
    r=delivery.build(write(path,spec),tmp_path/'out')
    assert r['claims'][0]['same_bytes'] is True
    assert '独立验证通过' not in (tmp_path/'out/REPORT.md').read_text()


@pytest.mark.parametrize('target',['REPORT.md','figure-1.png','ANSWER.md'])
def test_modified_delivery_rejected(delivery,case,tmp_path,target):
    path,_=case;out=tmp_path/'out';delivery.build(path,out)
    p=out/target;p.write_bytes(p.read_bytes()+b' invented assertion')
    with pytest.raises(ValueError):delivery.verify(path,out)


def test_final_answer_must_match_generated_answer(delivery,case,tmp_path):
    path,_=case;out=tmp_path/'out';delivery.build(path,out)
    draft=tmp_path/'draft.md';draft.write_text((out/'ANSWER.md').read_text()+'串联\n')
    with pytest.raises(ValueError):delivery.verify(path,out,draft)


def test_coordinate_tolerance_reports_actual_sample_not_requested_location(delivery,case,tmp_path):
    path,spec=case
    spec['claims']=[{'op':'relative_deviation','table':'data','column':'y_T',
                     'at':{'x_m':.001},'coordinate_atol':.002}]
    r=delivery.build(write(path,spec),tmp_path/'out')
    assert r['claims'][0]['sample_coordinates']=={'x_m':0}
    assert '实际采样坐标' in (tmp_path/'out/ANSWER.md').read_text()


@pytest.mark.parametrize('value',['nan','inf',''])
def test_nonfinite_missing_numbers_rejected(delivery,case,tmp_path,value):
    path,_=case;(tmp_path/'data.csv').write_text(f'x_m,y_T\n0,{value}\n')
    with pytest.raises(ValueError):delivery.build(path,tmp_path/'out')


def test_source_free_cli_exposes_replayable_final_text(case,tmp_path):
    path,spec=case;spec['plots']=[];write(path,spec)
    out=tmp_path/'out'
    cmd=[sys.executable,'-I',str(TOOL)]
    subprocess.run(cmd+['build',str(path),'--out',str(out)],check=True,capture_output=True)
    p=subprocess.run(cmd+['verify',str(path),'--out',str(out),'--answer',str(out/'ANSWER.md')],check=True,capture_output=True,text=True,cwd=tmp_path)
    response=json.loads(p.stdout)
    assert response['answer_text']==(out/'ANSWER.md').read_text()
    assert Path(response['spec'])==path and Path(response['out'])==out
    draft=tmp_path/'draft.md';draft.write_text(response['answer_text']+'模型已获得独立科学认证。')
    p=subprocess.run(cmd+['verify',str(path),'--out',str(out),'--answer',str(draft)],capture_output=True,text=True)
    assert p.returncode==2 and json.loads(p.stdout)['status']=='INVALID'
