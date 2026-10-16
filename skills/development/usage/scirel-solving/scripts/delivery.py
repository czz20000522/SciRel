"""Portable scientific result-to-statement checks; no agent or host authority.

Build and replay bounded numerical statements from saved CSVs. This checks data
and statements, not the truth of a model, a supplied unit, or a user's intent.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import math
import operator
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(obj, required, optional=()):
    require(isinstance(obj, dict), 'expected object')
    require(set(required) <= obj.keys() and obj.keys() <= set(required) | set(optional),
            'missing or unsupported fields: ' + str(sorted(obj)))


def number(value):
    require(not isinstance(value, bool), 'boolean is not a measurement')
    result = float(value)
    require(math.isfinite(result), 'nonfinite measurement')
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def fmt(value):
    return f'{value:.9g}'


def load_table(base, declaration):
    fields(declaration, ['path', 'units', 'coordinates'], ['expected_rows', 'expected_groups'])
    data = (base / declaration['path']).read_bytes()
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    units = declaration['units']
    require(bool(units) and isinstance(units, dict), 'units required for measured columns')
    require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), 'duplicate/missing CSV headers')
    require(set(units) <= set(reader.fieldnames), 'declared column absent')
    for name, unit in units.items():
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is not None, 'use identifier CSV column names')
        require(isinstance(unit, str) and re.fullmatch(r'[A-Za-z0-9_/*^(). -]{1,40}', unit) is not None,
                'unit must be a short scientific unit expression; use 1 for dimensionless')
    coords = declaration['coordinates']
    require(isinstance(coords, list) and set(coords) <= units.keys() and len(set(coords)) == len(coords), 'invalid coordinates')
    raw = list(reader)
    require(bool(raw) and all(None not in r and all(v is not None for v in r.values()) for r in raw), 'empty/ragged CSV')
    rows = [{key: number(row[key]) for key in units} for row in raw]
    if 'expected_rows' in declaration:
        require(len(rows) == declaration['expected_rows'], 'coverage: row count mismatch')
    if 'expected_groups' in declaration:
        groups = declaration['expected_groups']
        fields(groups, ['columns', 'values', 'rows_each'])
        require(groups['columns'] and set(groups['columns']) <= set(coords), 'group keys must be coordinates')
        actual = collections.Counter(tuple(r[k] for k in groups['columns']) for r in rows)
        expected = [tuple(number(v) for v in group) for group in groups['values']]
        require(all(len(g) == len(groups['columns']) for g in expected) and len(set(expected)) == len(expected), 'invalid expected groups')
        require(set(actual) == set(expected) and all(n == groups['rows_each'] for n in actual.values()), 'coverage: group mismatch')
    scope = {k: sorted({r[k] for r in rows}) for k in coords}
    return rows, dict(sha256=digest(data), rows=len(rows), units=units, coordinates=scope)


def evaluate(spec_path, out):
    spec_path = Path(spec_path)
    raw_spec = spec_path.read_bytes()
    spec = json.loads(raw_spec)
    fields(spec, ['schema', 'tables', 'claims'], ['premises', 'plots'])
    require(spec['schema'] == 'scirel.result-delivery.v1', 'unsupported schema')
    require(spec['tables'] and spec['claims'], 'tables and claims required')
    tables, facts = {}, {}
    for name, declaration in spec['tables'].items():
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is not None, 'invalid table identifier')
        tables[name], facts[name] = load_table(spec_path.parent, declaration)
    premises = []
    for premise in spec.get('premises', []):
        fields(premise, ['path', 'quote'])
        data = (spec_path.parent / premise['path']).read_bytes()
        require(isinstance(premise['quote'], str) and premise['quote'].strip() and premise['quote'] in data.decode(), 'unprovided premise')
        premises.append(dict(quote=premise['quote'], sha256=digest(data)))
    claims, lines = [], []
    for request in spec['claims']:
        op = request['op']
        common = ['op', 'table', 'column']
        extra = {'range': [], 'relative_deviation': ['at'], 'threshold': ['relation','value'],
                 'compare': ['reference','keys','atol','rtol']}
        require(op in extra, 'unsupported scientific inference; no free-form verified claim')
        fields(request, common + extra[op], ['coordinate_atol'] if op == 'relative_deviation' else [])
        table, col = request['table'], request['column']
        rows, scope = tables[table], facts[table]
        values = [r[col] for r in rows]
        unit = scope['units'][col]
        result = dict(op=op, table=table, column=col, rows=len(rows), unit=unit)
        lead = f'{table} 的 {col}（{unit}，全部 {len(rows)} 行）'
        if op == 'range':
            result.update(min=min(values), max=max(values), max_abs=max(map(abs, values)))
            lines.append(f'{lead}：最小值 {fmt(result["min"])}，最大值 {fmt(result["max"])}，最大绝对值 {fmt(result["max_abs"])}。')
        elif op == 'threshold':
            relation = request['relation']
            relations = {'>':operator.gt, '>=':operator.ge, '<':operator.lt, '<=':operator.le}
            require(relation in relations, 'unsupported threshold relation')
            threshold = number(request['value'])
            count = sum(relations[relation](v, threshold) for v in values)
            result.update(relation=relation, threshold=threshold, count=count)
            lines.append(f'{lead}：满足 {col} {relation} {fmt(threshold)} {unit} 的数据行为 {count}/{len(rows)}；'
                         + ('没有满足该条件的数据行。' if count == 0 else '存在满足该条件的数据行。'))
        elif op == 'relative_deviation':
            at = request['at']; tol = number(request.get('coordinate_atol', 0))
            require(at and set(at) <= scope['coordinates'].keys() and tol >= 0, 'invalid reference coordinates')
            match = [i for i,r in enumerate(rows) if all(abs(r[k]-number(v)) <= tol for k,v in at.items())]
            require(len(match) == 1, 'reference coordinate must identify exactly one saved row')
            reference = values[match[0]]
            require(reference != 0, 'relative deviation undefined for zero reference')
            deviations = [abs((v-reference)/reference) for v in values]
            maximum = max(deviations)
            sample = {k:rows[match[0]][k] for k in scope['coordinates']}
            result.update(reference=reference, at=at, sample_coordinates=sample, coordinate_atol=tol, max_relative_deviation=maximum,
                          extrema=[{k:rows[i][k] for k in scope['coordinates']} for i,d in enumerate(deviations) if d == maximum])
            lines.append(f'{lead}：实际采样坐标 {json.dumps(sample, ensure_ascii=False)} 的参考值为 {fmt(reference)} {unit}'
                         f'（目标 {json.dumps(at, ensure_ascii=False)}，坐标绝对容差 {fmt(tol)}）；'
                         f'相对该值的最大绝对偏差为 {fmt(maximum*100)}%。这不自动判定应用是否合格。')
        else:
            ref = request['reference']; keys = request['keys']
            require(keys and len(set(keys)) == len(keys) and set(keys) <= set(scope['coordinates']), 'comparison needs coordinate keys')
            require(set(keys) <= set(facts[ref]['coordinates']), 'reference coordinate mismatch')
            require(all(facts[ref]['units'][k] == scope['units'][k] for k in keys+[col]), 'comparison unit mismatch')
            keyed = lambda rs: {tuple(r[k] for k in keys):r[col] for r in rs}
            left, right = keyed(rows), keyed(tables[ref])
            require(len(left) == len(rows) and len(right) == len(tables[ref]) and left.keys() == right.keys(), 'coverage: comparison keys must match uniquely and completely')
            atol, rtol = number(request['atol']), number(request['rtol'])
            require(atol >= 0 and rtol >= 0, 'negative tolerance')
            errors = [abs(left[k]-right[k]) for k in left]
            passed = all(abs(left[k]-right[k]) <= atol+rtol*abs(right[k]) for k in left)
            result.update(reference=ref, atol=atol, rtol=rtol, passed=passed, max_absolute_error=max(errors), same_bytes=scope['sha256'] == facts[ref]['sha256'])
            lines.append(f'{lead}：与 {ref} 按 {keys} 完整逐行比较，标准 |差| ≤ {fmt(atol)} + {fmt(rtol)}×|参考值|，'
                         f'最大绝对差 {fmt(max(errors))} {unit}，{"通过" if passed else "未通过"}。'
                         + ('两表字节相同。' if result['same_bytes'] else '')
                         + '这是数据一致性比较，不证明算法或物理模型独立。')
        # Overflow during derived arithmetic must not turn into a usable report.
        encoded(result)
        claims.append(result)
    plots = []
    for plot in spec.get('plots', []):
        fields(plot, ['table','x','y'])
        table,x,y = plot['table'],plot['x'],plot['y']
        rows,scope = tables[table],facts[table]
        require(x in scope['coordinates'] and y in scope['units'], 'plot coordinates/measurement not declared')
        xs = [r[x] for r in rows]
        require(len(set(xs)) == len(xs), 'plot must have unique x coordinates')
        plots.append(dict(table=table,x=x,y=y,x_unit=scope['units'][x],y_unit=scope['units'][y],x_range=[min(xs),max(xs)]))
    status = 'CHECK_FAILED' if any(c.get('passed') is False for c in claims) else 'CONSISTENT'
    result = dict(schema=spec['schema'],status=status,spec_sha256=digest(raw_spec),tables=facts,premises=premises,claims=claims,plots=plots)
    lines.insert(0, '以下结论来自保存的数据；' + ('有数据比较未通过。' if status == 'CHECK_FAILED' else '已核对下列数值陈述与保存数据一致。'))
    lines.append('覆盖范围：' + '；'.join(f'{name} 共 {f["rows"]} 行，坐标 '+str({k:(v if len(v)<=12 else {"min":min(v),"max":max(v),"distinct":len(v)}) for k,v in f['coordinates'].items()}) for name,f in facts.items())+'。')
    lines.append('单位按输入声明；仅覆盖这些保存数据。模型适用性、条件翻译和额外物理机制不由本检查证明。')
    if premises:
        lines.append('提供的条件原文：\n'+ '\n'.join('> '+p['quote'].replace('\n','\n> ') for p in premises))
    links = [f'[{name} CSV](<{(spec_path.parent / declaration["path"]).resolve()}>)'
             for name,declaration in spec['tables'].items()]
    links += [f'[图 {i}](<{Path(out).resolve() / f"figure-{i}.png"}>)' for i in range(1,len(plots)+1)]
    lines.append('文件：'+' · '.join(links))
    answer = '\n\n'.join(lines)+'\n'
    artifacts = {'ANSWER.md':answer.encode(), 'REPORT.md':('# 数值结果与检查\n\n'+answer).encode()}
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import pyplot as plt
        for i,p in enumerate(plots,1):
            rows = sorted(tables[p['table']],key=lambda r:r[p['x']])
            fig,ax=plt.subplots(figsize=(7,4.2))
            ax.plot([r[p['x']] for r in rows],[r[p['y']] for r in rows],'o-',markersize=4)
            ax.set(xlabel=f'{p["x"]} ({p["x_unit"]})',ylabel=f'{p["y"]} ({p["y_unit"]})',title='Saved numerical results')
            ax.ticklabel_format(useOffset=False);ax.grid(alpha=.3);fig.tight_layout()
            stream=io.BytesIO();fig.savefig(stream,format='png',dpi=150,metadata={'Software':'SciRel delivery'});plt.close(fig)
            artifacts[f'figure-{i}.png']=stream.getvalue()
    result['artifact_sha256']={name:digest(data) for name,data in artifacts.items()}
    return result,artifacts


def build(spec_path, out):
    result,artifacts=evaluate(spec_path, out)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # Do not overwrite any declared source or spec with generated filenames.
    spec_path=Path(spec_path).resolve();spec=json.loads(spec_path.read_bytes())
    sources={spec_path} | {(spec_path.parent/x['path']).resolve() for x in [*spec['tables'].values(),*spec.get('premises',[])]}
    require(all((out/name).resolve() not in sources for name in [*artifacts,'checks.json']), 'output would overwrite input')
    for name,data in artifacts.items():(out/name).write_bytes(data)
    (out/'checks.json').write_bytes(encoded(result))
    return result


def verify(spec_path,out,answer=None):
    result,artifacts=evaluate(spec_path, out)
    out=Path(out)
    require((out/'checks.json').read_bytes() == encoded(result), 'result, specification or check record changed')
    for name,data in artifacts.items():
        require((out/name).read_bytes() == data, 'generated artifact changed: '+name)
    if answer is not None:
        # Transport may omit a terminal newline; prose and scientific values may not change.
        require(Path(answer).read_text().strip() == artifacts['ANSWER.md'].decode().strip(), 'answer contains unverified edits or claims')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['build','verify'])
    parser.add_argument('spec',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--answer',type=Path,help='verify the exact answer body to deliver; file links can be sent separately')
    args=parser.parse_args()
    try:
        require(args.command == 'verify' or args.answer is None, '--answer is only for verify')
        result=build(args.spec,args.out) if args.command == 'build' else verify(args.spec,args.out,args.answer)
        response = {'status':result['status'], 'spec':str(args.spec.resolve()), 'out':str(args.out.resolve()),
                    'answer':str(args.out/'ANSWER.md'),'report':str(args.out/'REPORT.md')}
        if args.command == 'verify':
            response['answer_text'] = (args.out/'ANSWER.md').read_text()
        print(json.dumps(response,ensure_ascii=False))
        return 3 if result['status']=='CHECK_FAILED' else 0
    except (ValueError,KeyError,TypeError,OSError,OverflowError) as error:
        print(json.dumps({'status':'INVALID','error':str(error)},ensure_ascii=False))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
