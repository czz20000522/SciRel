"""Render exact scientific records and bound Chinese prose with SciPy's theme.

No scientific imports, autodoc execution, translation inference, or example runs.
All generated reStructuredText is a projection of reviewed input documents.
"""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def load_translations(root, documents, docs, translation_paths=None):
    """Load one exact reader set; an explicit selection keeps all binding gates.

    The default repository handbook still consumes all repository reader bundles.
    A selected scientific distribution can supply its own complete reader set
    without inheriting unrelated documents from another development selection.
    """
    records = {}
    paths = (sorted((root / 'tools/docs/zh').glob('*.json'))
             if translation_paths is None else translation_paths)
    for path in paths:
        bundle = json.loads(path.read_bytes())
        if bundle['schema'] != 'scirel.reader-translation.v1' or bundle['language'] != 'zh-CN':
            raise ValueError('invalid reader translation: ' + str(path))
        for item in bundle['records']:
            if item['asset_id'] in records:
                raise ValueError('duplicate reader translation: ' + item['asset_id'])
            records[item['asset_id']] = item
    ids = {doc['asset_id'] for doc in docs}
    if set(records) != ids:
        raise ValueError('Chinese reader coverage differs from exact document set')
    for doc in docs:
        asset = doc['asset_id']; item = records[asset]
        digest = hashlib.sha256((documents / (asset + '.json')).read_bytes()).hexdigest()
        if item['source_sha256'] != digest:
            raise ValueError('stale Chinese reader translation: ' + asset)
        for side in ('inputs', 'outputs'):
            if [x['name'] for x in item[side]] != [x['name'] for x in doc[side]]:
                raise ValueError('translated port names/order differ: ' + asset)
            for port in item[side]:
                for key in ('description', 'constraints', 'dtype'):
                    if not isinstance(port[key], str) or not port[key].strip():
                        raise ValueError('empty translated port field: ' + asset)
        for key in ('summary', 'definition', 'model', 'boundary'):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError('empty translated description: ' + asset)
        for side, fields in [('applicability', ('preconditions', 'supported', 'excluded')),
                             ('verification', ('scope', 'known_limitations'))]:
            for key in fields:
                if len(item[side][key]) != len(doc[side][key]):
                    raise ValueError('translation dropped a contract clause: ' + asset + ':' + key)
                if any(not isinstance(x, str) or not x.strip() for x in item[side][key]):
                    raise ValueError('empty translated contract clause: ' + asset + ':' + key)
        if len(item['assumptions']) != len(doc['identity']['assumptions']):
            raise ValueError('translation dropped a model assumption: ' + asset)
        if any(not isinstance(x, str) or not x.strip() for x in item['assumptions']):
            raise ValueError('empty translated assumption: ' + asset)
        for key in ('invalid_input', 'runtime_failure', 'nonconvergence', 'partial_results'):
            if not item['failure_semantics'][key].strip():
                raise ValueError('missing failure semantics: ' + asset)
        if not item['verification']['evidence_ceiling'].strip():
            raise ValueError('missing translated evidence ceiling: ' + asset)
        for key in ('description', 'expected'):
            if not item['example'][key].strip():
                raise ValueError('missing translated example: ' + asset)
        conflicts = item.get('source_conflicts', [])
        if not isinstance(conflicts, list) or any(not isinstance(x, str) or not x.strip() for x in conflicts):
            raise ValueError('invalid source conflict annotation: ' + asset)
    return records


def plain(text):
    """Render explicit inline math/code; escape all other prose as reST text."""
    def escape(value):
        return value.replace('\\', '\\\\').replace('`', '\\`').replace('*', '\\*').replace('|', '\\|').replace('_', '\\_').replace('\n', ' ')
    result = []
    for part in re.split(r'(\$[^$\n]+\$|`[^`\n]+`)', str(text)):
        if part.startswith('$') and part.endswith('$') and len(part) > 2:
            from latex2mathml.converter import convert
            node = ET.fromstring(convert(part[1:-1]))
            allowed = {'math', 'mi', 'mo', 'mn', 'mrow', 'msup', 'msub', 'msubsup',
                       'mfrac', 'msqrt', 'mroot', 'mover', 'munder', 'munderover',
                       'mtext', 'mtable', 'mtr', 'mtd', 'mspace', 'menclose',
                       'mpadded', 'mstyle', 'mmultiscripts', 'mprescripts', 'none', 'mphantom'}
            for element in node.iter():
                if element.tag.rsplit('}', 1)[-1] not in allowed or any(
                    key.lower().startswith('on') or key.lower().endswith('href')
                    for key in element.attrib
                ):
                    raise ValueError('unsupported MathML in scientific prose')
            ET.register_namespace('', 'http://www.w3.org/1998/Math/MathML')
            node.set('aria-label', part[1:-1])
            markup = ET.tostring(node, encoding='unicode').replace('`', '&#96;').replace('\\', '\\\\')
            result.append(' :scirel-math:`' + markup + '` ')
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            result.append(' ``' + part[1:-1] + '`` ')
        else:
            result.append(escape(part))
    return ''.join(result)


def title(text, char='='):
    return text + '\n' + char * (len(text) * 2 + 4) + '\n\n'


def bullets(items):
    return ''.join('* ' + plain(x) + '\n' for x in items) + '\n'


def code(text, language='python'):
    return '.. code-block:: ' + language + '\n\n' + '\n'.join('   ' + line for line in text.splitlines()) + '\n\n'


def toctree(paths, hidden=False, maxdepth=2):
    return ('.. toctree::\n   :maxdepth: ' + str(maxdepth) + '\n' +
            ('   :hidden:\n' if hidden else '') + '\n' + ''.join('   ' + p + '\n' for p in paths) + '\n')


def api_path(asset):
    return '/reference/generated/' + asset


def doclink(label, path):
    return ':doc:`' + label.replace('`', '') + ' <' + path + '>`'


def function_table(records, translations):
    """One linked callable and its bound Chinese purpose per row."""
    out = '.. list-table::\n   :header-rows: 1\n   :widths: 40 60\n   :class: scirel-api-summary\n\n   * - 函数 / 复合入口\n     - 用途\n'
    for doc in records:
        label = doc['public_api']['python']['symbol']
        purpose = plain(translations[doc['asset_id']]['summary'])
        if doc['kind'] == 'task_graph':
            purpose += ' **（复合入口）**'
        out += '   * - ' + doclink(label, api_path(doc['asset_id'])) + '\n     - ' + purpose + '\n'
    return out + '\n'


def ports(doc, translated, side):
    out = ''
    for original, zh in zip(doc[side], translated[side], strict=True):
        name = original['name']; typ = plain(zh['dtype'])
        optional = '，可选' if not original.get('required', True) else ''
        out += '``' + name + '`` : ' + typ + optional + '\n'
        out += '    ' + plain(zh['description']) + '\n\n'
        out += '    单位：' + plain(str(original['units'])) + '；形状：' + plain(str(original['shape'])) + '。\n\n'
        if 'default' in original:
            out += '    默认值：``' + str(original['default']) + '``。\n\n'
        out += '    ' + plain(zh['constraints']) + '\n\n'
    label = '参数' if side == 'inputs' else '返回值'
    return ':' + label + ':\n' + ''.join('    ' + line + '\n' if line else '\n' for line in out.splitlines()) + '\n'


def render_api(doc, zh, related):
    py = doc['public_api']['python']; asset = doc['asset_id']
    out = plain(doc['title']['zh']) + '。' + plain(zh['summary']) + '\n\n'
    if zh.get('source_conflicts'):
        out += '.. warning::\n\n   原正式文档含有待修正的内部矛盾。以下为阅读提示，不改变原合同或科学资格。\n\n'
        out += ''.join('   * ' + plain(item) + '\n' for item in zh['source_conflicts']) + '\n'
    out += '实现版本：``' + doc['version']['implementation_version'] + '``。'
    out += '复合任务入口。\n\n' if doc['kind'] == 'task_graph' else '科学关系函数。\n\n'
    out += ports(doc, zh, 'inputs') + ports(doc, zh, 'outputs')
    out += title('异常与失败行为', '-')
    for key, label in [('invalid_input', '无效输入'), ('runtime_failure', '运行失败'),
                       ('nonconvergence', '不收敛'), ('partial_results', '部分结果')]:
        out += '**' + label + '**\n    ' + plain(zh['failure_semantics'][key]) + '\n\n'
    out += title('说明', '-') + plain(zh['definition']) + '\n\n'
    out += '**模型：** ' + plain(zh['model']) + '\n\n'
    out += '**边界约定：** ' + plain(zh['boundary']) + '\n\n' + bullets(zh['assumptions'])
    out += title('适用范围', '-') + '**使用前提**\n\n' + bullets(zh['applicability']['preconditions'])
    out += '**支持的范围**\n\n' + bullets(zh['applicability']['supported'])
    out += '**不支持的范围**\n\n' + bullets(zh['applicability']['excluded'])
    out += title('相关函数', '-')
    if related:
        out += ''.join('* ' + doclink(d['public_api']['python']['symbol'], api_path(d['asset_id'])) + ' — ' + plain(d['title']['zh']) + '\n' for d in related) + '\n'
    else:
        out += '请返回所属领域的 API 参考，按科学问题选择其他关系。\n\n'
    out += title('示例', '-') + plain(zh['example']['description']) + '\n\n'
    out += code(doc['example']['code'])
    out += '**预期行为：** ' + plain(zh['example']['expected']) + '\n\n'
    out += '以上代码来自正式合同，预期行为与本轮实际运行结果分别记录。完整的已运行案例见用户指南。\n\n'
    out += title('验证与限制', '-') + plain(zh['verification']['evidence_ceiling']) + '\n\n'
    out += '**已有验证范围**\n\n' + bullets(zh['verification']['scope'])
    out += '**已知限制**\n\n' + bullets(zh['verification']['known_limitations'])
    out += title('参考资料', '-')
    refs = doc['provenance'].get('public_references', [])
    for ref in refs:
        out += '* ' + plain(json.dumps(ref, ensure_ascii=False) if isinstance(ref, dict) else ref) + '\n'
    out += '\n`读取正式合同 JSON </api/asset?id=' + asset + '>`_ · '
    out += '`读取同源中文说明 </api/reader?id=' + asset + '>`_\n\n'
    out += '中文说明绑定正式合同摘要 ``' + zh['source_sha256'] + '``。来源与许可状态保留在原合同中。\n'
    # Match numpydoc's field-list and rubric structure used by SciPy. The
    # Chinese prose remains a projection; no scientific module is imported.
    for label in ('异常与失败行为', '说明', '适用范围', '相关函数', '示例', '验证与限制', '参考资料'):
        out = out.replace(title(label, '-'), '.. rubric:: ' + label + '\n\n')
    heading = '.. raw:: html\n\n   <p class="scirel-module">' + py['module'] + '.</p>\n\n' + title(py['symbol'])
    return heading + '.. py:function:: ' + py['signature'] + '\n   :no-index-entry:\n\n' + ''.join('   ' + line + '\n' if line else '\n' for line in out.splitlines())


def render_tutorial(chapter):
    c = chapter; r = c['results']
    out = title(c['title']) + c['introduction'] + '\n\n' + c['prerequisites'] + '\n\n'
    out += title('模型与准备', '-') + bullets(c['conventions']) + code(c['imports'])
    out += '以下小节按顺序运行，共享变量。完整脚本与执行记录在本页末尾提供。\n\n'
    for s in c['sections']:
        out += '.. _' + s['id'] + ':\n\n' + title(s['title'], '-')
        out += s['problem'] + '\n\n' + s['method'] + '\n\n'
        if s.get('formula_mathml'):
            out += '.. raw:: html\n\n   <div class="scirel-formula">' + s['formula_mathml'] + '</div>\n\n'
            out += s['formula_note'] + '\n\n'
        out += code(s['code']) + title('运行结果', '~')
        key = s['result_key']
        if key == 'single':
            out += f"中心 Bz = {r['center_single_T'] * 1000:.6f} mT；141 个轴上点与解析公式的最大绝对差为 {r['checks']['axis_max_abs_error_T']:.3e} T。\n\n"
        elif key == 'pair':
            out += f"每环 1000 A 同向通电时，中心 Bz = {r['center_pair_T'] * 1000:.6f} mT；反向通电时，中心 Bz = {r['opposed_BZ_T'][70] * 1000:.6f} mT。\n\n"
        elif key == 'rectangle':
            out += f"每组 64 根细丝，共 128 根；观测网格为 101 × 61。中心 Bz = {r['refinement_center_T'][2] * 1000:.6f} mT。\n\n"
        elif key == 'checks':
            out += '.. list-table:: 中心观测点的离散加密检查\n   :header-rows: 1\n\n   * - 每组离散\n     - 中心 Bz / mT\n     - 相对上一行变化\n'
            for i, n in enumerate(r['refinement_n']):
                change = '—' if i == 0 else f"{(r['refinement_center_T'][i]/r['refinement_center_T'][i-1]-1)*100:.4f}%"
                out += f"   * - {n} × {n}\n     - {r['refinement_center_T'][i]*1000:.6f}\n     - {change}\n"
            out += '\n轴上公式、几何对称性、电流线性叠加和有限值检查均通过。\n\n'
        if s.get('figure'):
            out += '.. figure:: /_static/examples/' + s['figure'] + '\n   :alt: ' + s['caption'] + '\n\n   ' + s['caption'] + '\n\n'
        out += title('结果解释', '~') + s['interpretation'] + '\n\n'
    out += '.. _limits:\n\n' + title('适用范围与常见误用', '-') + bullets(c['limitations'])
    out += '.. _reference:\n\n' + title('复现与函数参考', '-') + c['run'] + '\n\n'
    out += '`下载完整 Python 脚本 </chapters/magnetostatics/example.py>`_ · `下载实际结果 </chapters/magnetostatics/results.json>`_\n\n'
    out += ''.join('* ' + doclink(x['purpose'], api_path(x['id'])) + '\n' for x in c['assets']) + '\n'
    out += '`读取实际执行绑定与完整章节 </api/chapter?id=magnetostatics>`_\n'
    return out


def render_site(root, docs, book, translations, chapter, *, figure_files):
    """Return only generated public site bytes; staging sources stay temporary."""
    # Sphinx otherwise silently builds a Chinese search index of Latin words only.
    jieba_version = version('jieba')
    by_id = {d['asset_id']: d for d in docs}
    with tempfile.TemporaryDirectory(prefix='scirel-sphinx-') as temp:
        stage = Path(temp); source = stage/'source'; output = stage/'html'
        shutil.copytree(root/'tools/docs/sphinx', source, ignore=shutil.ignore_patterns('requirements.txt'))
        def write(path, text):
            p = source/(path + '.rst'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
        home = title('SciRel 中文文档')
        home += 'SciRel 是面向科学计算的 Python 关系库。按要解决的物理问题，选择单个科学函数，或使用组合多个关系的复合求解入口。\n\n'
        home += '.. grid:: 1 2 2 2\n   :gutter: 3\n\n'
        if not any(t.get('tutorial_id') == 'kinetic-initial-value' for c in book['chapters'] for t in c['topics']):
            (source/'tutorials/kinetic-initial-value.rst').unlink(missing_ok=True)
        else:
            proof = json.loads((root/'provenance/validation/kinetic-tutorial-current-wheel-20261015.json').read_bytes())
            bound_paths = dict(proof['source_files'], **proof['document_files'])
            bound_paths['tools/docs/sphinx/tutorials/kinetic-initial-value.rst'] = proof['tutorial_rst_sha256']
            if not proof['results']['all_checks_passed'] or proof['environment']['exit_code'] != 0:
                raise ValueError('kinetic tutorial has no successful execution')
            for relative, digest in bound_paths.items():
                if hashlib.sha256((root/relative).read_bytes()).hexdigest() != digest:
                    raise ValueError('kinetic tutorial execution binding changed: ' + relative)
        for label, target, description in [('用户指南','user-guide/index','从科学概念与输入约定入手，阅读领域导读和完整计算案例。'),('API 参考','reference/index','按科学领域查询调用签名、参数、返回值、失败行为、适用范围及示例。'),('开始使用','getting-started','了解精确安装包、单位约定，以及如何选择并验证一个科学关系。'),('Agent 查询','agent','按主题或精确资产标识读取与页面绑定的正式合同及中文说明。')]:
            home += '   .. grid-item-card:: ' + label + '\n      :link: ' + target + '\n      :link-type: doc\n\n      ' + description + '\n\n'
        home += '当前为开发文档。各函数保留自己的实现版本；请按 API 页的适用范围和具体安装包使用。\n\n'
        home += toctree(['getting-started','user-guide/index','reference/index','agent'], hidden=True)
        write('index', home)
        write('getting-started', (root/'tools/docs/sphinx/getting-started.rst').read_text())
        write('agent', (root/'tools/docs/sphinx/agent.rst').read_text())
        write('user-guide/index', title('用户指南') + '用户指南解释科学问题、模型选择与组合方式。函数的完整参数、单位和失败行为见 API 参考。\n\n' + toctree([c['id'] for c in book['chapters']]) + title('完整计算案例','-') + toctree(['/tutorials/magnetostatics'] + (['/tutorials/kinetic-initial-value'] if any(t.get('tutorial_id') == 'kinetic-initial-value' for c in book['chapters'] for t in c['topics']) else [])))
        write('reference/index', title('API 参考') + '按科学领域查阅函数与复合入口。选择左侧领域，在正文中按问题浏览函数及用途，点击函数名查看参数、返回值、适用范围与示例。\n\n' + toctree([c['id'] for c in book['chapters']], maxdepth=1))
        for c in book['chapters']:
            write('user-guide/'+c['id'], title(c['title']) + c['introduction'] + '\n\n' + toctree(['topics/'+t['id'] for t in c['topics']]))
            ref = title(c['title']) + c['introduction'] + '\n\n'
            for topic in c['topics']:
                records = [by_id[a] for a in topic['assets']]
                intro = title(topic['title']) + topic['introduction'] + '\n\n'
                intro += title('选择计算入口','-')
                intro += function_table(records, translations)
                intro += title('模型与使用条件','-')
                for d in records:
                    z = translations[d['asset_id']]
                    intro += title(d['title']['zh'], '~') + plain(z['definition']) + '\n\n' + plain(z['boundary']) + '\n\n'
                    intro += bullets(z['applicability']['preconditions'])
                    intro += '详见 ' + doclink(d['public_api']['python']['symbol'], api_path(d['asset_id'])) + ' 的参数、输出和失败行为。\n\n'
                intro += title('验证与使用边界','-')
                for d in records:
                    z = translations[d['asset_id']]
                    intro += '**' + plain(d['title']['zh']) + '**\n\n' + plain(z['verification']['evidence_ceiling']) + '\n\n' + bullets(z['verification']['known_limitations'])
                if topic.get('tutorial_id'):
                    tutorial_id = topic['tutorial_id']
                    tutorial_title = {'magnetostatics': '轴对称线圈磁场：代码、实际结果与解释', 'kinetic-initial-value': '静电根与线性初值演化：实际结果及解释'}[tutorial_id]
                    intro += title('计算案例','-') + doclink(tutorial_title, '/tutorials/' + tutorial_id) + '\n'
                write('user-guide/topics/'+topic['id'], intro)
                ref += title(topic['title'], '-') + topic['introduction'] + '\n\n'
                ref += function_table(records, translations)
                ref += toctree(['generated/'+d['asset_id'] for d in records], hidden=True, maxdepth=1)
                for d in records:
                    related_ids = [x['asset_id'] for x in records if x['asset_id'] != d['asset_id']]
                    for dependency in d['version'].get('dependencies', []):
                        dependency_id = dependency['asset_id']
                        if dependency_id not in related_ids:
                            related_ids.append(dependency_id)
                    write('reference/generated/'+d['asset_id'], render_api(d, translations[d['asset_id']], [by_id[a] for a in related_ids]))
            write('reference/'+c['id'], ref)
        write('tutorials/magnetostatics', render_tutorial(chapter))
        examples = source/'_static/examples'; examples.mkdir()
        for name in ('single.svg','pair.svg','rectangle.svg'):
            (examples/name).write_bytes(figure_files[name])
        result = subprocess.run([sys.executable, '-m', 'sphinx', '-b', 'html', '-W', '--keep-going', '-q', str(source), str(output)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Sphinx build failed:\n' + result.stdout + result.stderr)
        files = {'web/'+str(p.relative_to(output)): p.read_bytes() for p in output.rglob('*') if p.is_file() and '.doctrees' not in p.parts and p.name != '.buildinfo'}
        renderer = {'sphinx': version('Sphinx'), 'pydata_sphinx_theme': version('pydata-sphinx-theme'),
                    'sphinx_copybutton': version('sphinx-copybutton'), 'sphinx_design': version('sphinx-design'),
                    'pygments': version('Pygments'), 'jieba': jieba_version,
                    'latex2mathml': version('latex2mathml'), 'language': 'zh-CN',
                    'warnings_as_errors': True, 'science_imports': False,
                    'reference': 'https://docs.scipy.org/doc/scipy/', 'source_documents': len(docs)}
        files['renderer.json'] = (json.dumps(renderer, ensure_ascii=False, indent=2)+'\n').encode()
        return files
