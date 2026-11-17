# 状态快照

**本文件会随版本变，总纲不会。** 这里记的是某个 revision 上量出来的事实，不是承诺，也不是规范。
引用这里的数字时必须连同 revision 一起引用；下个版本它们大概率已经不同。

规范（判据、原则、流程）不在本文件，见 [持久规范与状态的分界](durable-vs-status.md)。

## 1 观察点

| 项 | 值 |
| --- | --- |
| 分支 | `main` |
| revision | `7f1eef8c` |
| 观察日期 | 2026-11-17 |

## 2 规模

每一行都给出复算口径，任何人在任何 checkout 上都能重跑。数字放在表格里是**故意的**：
[`test_repository_skeleton.py`](../../tests/architecture/test_repository_skeleton.py) 会判红"文档里手写目录规模"的写法，
因为这正是会漂移的那类句子；表格只提供当次分母，不宣称规模。

| 量 | 值 | 复算口径（在仓库根执行） |
| --- | --- | --- |
| 合同（`catalog/examples/`） | 249 | `ls catalog/examples/scirel.*.json \| wc -l` |
| `src/scirel` 下 `.py` 文件 | 230 | `find src/scirel -name '*.py' \| wc -l` |
| `src/scirel` 行数 | 56019 | `find src/scirel -name '*.py' -exec cat {} + \| wc -l` |
| 模块级公开函数（`def` 顶格、非下划线开头） | 294 | `grep -rh '^def [a-zA-Z]' src/scirel --include='*.py' \| wc -l` |
| 顶层子包（含 `__init__.py`） | 22 | 其中 21 个是公开领域包，`_framework_compositions` 是根级私有模块 |
| 测试文件 | 412 | `find tests -name 'test_*.py' \| wc -l` |
| 收集到的用例 | 9378 | `python -m pytest tests -q --collect-only` 尾行 |
| `def test_` 字面数量 | 3865 | `grep -rhc 'def test_' tests --include='test_*.py' \| awk '{s+=$1} END {print s}'` |

最后两行不是重复计数，而是**两种口径**：参数化会把一个 `def test_` 展开成多个用例。
"用例数"随参数表变，"函数数"随文件变，两者不可互推。

### 2.1 测试构成：证据测试与行为测试必须分开报

只有一个"测试文件数"是没有信息量的，而且会误导。我们的测试承担两种不同的职责：

| 类型 | 职责 | 判据 | 能不能砍 |
| --- | --- | --- | --- |
| **证据测试** | 真值链的第一环：证伪"这个物理关系算对了" | 闭式解、解析恒等式、精确有理重算、高位 mpmath 对照、守恒量 | **不能**。砍掉之后合同只剩"代码现在是这样" |
| **行为测试** | 回归：证伪"改动破坏了别处" | 钉住当前返回值/形状/报错的断言 | 可以按风险收敛 |
| **验收/工具测试** | 交付与流程：wheel 暴露、分发内容、文档构建、脚本行为 | 目录与产物断言 | 按交付口径管理 |

当前的实际分类口径（可复算，但**是文本估计，不是权威计数**）：

```
grep -rlE "mpmath|closed[- ]form|analytic|exact|conservation|identity|rational" tests --include='test_*.py' | wc -l
```

命中 252 个文件（占 412 的 61%）。这个数字只能说明"证据语汇出现在大半测试文件里"，
**不能**当作"证据测试的比例"——一个文件里可能既有证据断言也有行为断言。

**结论（这条是持久的）：报告测试规模时，必须先说清是哪一类，再给数字。**
把"412 个测试文件"当作成绩或债务都是错的：它对 scipy 的 0.70 测试文件/模块看起来偏高
（我们 1.79），但高出来的那部分正是 scipy 没有的一层——它只做行为回归，
正确性靠文献与社区使用；我们必须自己做证据。

真正的缺口是**没有权威分类**：现在还无法用一条命令回答"多少测试是证据、多少是回归"。
C3（一次检查给出可对账的逐项测试身份）正是为这件事开的工单。

### 2.1 关于"域有几个"：没有唯一口径

同一个仓库用不同口径会数出 21、22、23、24 四种结果，这本身就是必须写下来的状态：

| 口径 | 结果 |
| --- | --- |
| `src/scirel/` 下带 `__init__.py` 的公开子包 | 21 |
| 加上根级私有 `_framework_compositions` | 22 |
| 合同 `asset_id` 第二段的不同取值 | 23（含 `fieldline`、`sampling`，它们是 `geometry` 下的模块名） |
| 按"规范模块域"统计（包含 `numerics.interpolate` 这类子域） | 24 |

所以"领域数"不能单独引用，必须带口径。合同 ID 的领域段与规范模块域不一致（`scirel.sampling.*`、
`scirel.fieldline.*` 实际在 `scirel.geometry` 下）是已知结构债务，正在 C2 偿还。

## 3 各域的合同与模块

口径：合同按其 `public_api.python.canonical_module` 去掉 `scirel.` 前缀归域；
模块按其 `public_api.python.module` 统计；"单合同模块"= 只承载一份合同的模块数。
复算脚本见附录 A。

| 域 | 合同 | 承载模块 | 单合同模块 |
| --- | --- | --- | --- |
| kinetic | 62 | 26 | 18 |
| neutrals | 33 | 32 | 31 |
| collisions | 20 | 19 | 18 |
| geometry | 15 | 10 | 9 |
| field | 14 | 14 | 14 |
| sampling | 14 | 1 | 0 |
| numerics | 13 | 7 | 5 |
| equilibrium | 12 | 12 | 12 |
| mirror | 12 | 12 | 12 |
| closures | 7 | 7 | 7 |
| diagnostics | 7 | 7 | 7 |
| electromagnetism | 7 | 3 | 1 |
| fieldline | 7 | 1 | 0 |
| physics | 5 | 3 | 2 |
| fvm | 4 | 4 | 4 |
| io | 4 | 2 | 1 |
| configurations | 3 | 1 | 0 |
| inference | 3 | 3 | 3 |
| neoclassical | 2 | 1 | 0 |
| source | 2 | 2 | 2 |
| dielectric / fusion / plasma | 各 1 | 各 1 | 各 1 |

`fieldline` 与 `sampling` 的模块表里各只有 1 个模块（`scirel.geometry.fieldline`、
`scirel.geometry.sampling`），这不是统计错误，而是"一个模块装 7~14 份合同"的实际形态。

## 4 证据覆盖（`neither` 的构成）

口径：`scripts/c1_evidence_coverage.py --format json`。它只做文本分类，脚本自身写明
"Text match only, not a gate"——给分母，不判红。

| 分类 | 数量 |
| --- | --- |
| 记录了证据来源（basis） | 180 |
| 记录了缺口（gap） | 104 |
| 两者之一（either） | 220 |
| **两者都没有（neither）** | 29 |

`neither` 的域分布：`kinetic` 24、`numerics` 3、`field` 1、`sampling` 1。
每一项都需要人工裁决：要么指出证据来源，要么明确写成"未建立"。这是当前最大的单点债务。

## 5 领域结构进度（快照，不是承诺）

- `mirror` 已从 `kinetic` / `closures` 的交织代码中拆出，依赖方向与无环由
  [`test_domain_dependency_conformance.py`](../../tests/architecture/test_domain_dependency_conformance.py)、
  [`test_domain_import_cycles.py`](../../tests/architecture/test_domain_import_cycles.py) 检查。
- `neutrals` 已独立成域，但其与 `kinetic` 的归属划分仍未有定论。
- `geometry` 仍同时装着等离子体几何与通用数值工具（插值、基函数、非均匀差分、路径采样），
  后者按分层应下沉到 L1。
- 合同 ID 的领域段与规范模块域对齐在进行中（C2，25 份待对齐，已完成两批）。
- 能力边界冻结中：暂停接收新资产，准入中止，先还债。解除条件由维护者另行决定。

## 6 "现在做到哪了"应该去哪儿看

本文件只记录**能被命令复算的量**。不在此列、也不应该写进总纲的东西有两个固定去处：

- 待办计划：[`examples/PLAN.md`](../../examples/PLAN.md)；
- 等人工裁决的问题：`tickets/` 下 `status: open` 的工单。

## 附录 A 复算脚本

```python
import json, glob, collections

rows = []
for path in sorted(glob.glob('catalog/examples/*.json')):
    doc = json.load(open(path))
    api = doc['public_api']['python']
    domain = api['canonical_module'].replace('scirel.', '')
    rows.append((domain, api['module'], api['signature']))

contracts = collections.Counter(d for d, _, _ in rows)
modules = collections.defaultdict(set)
for d, m, _ in rows:
    modules[d].add(m)
per_module = collections.Counter(m for _, m, _ in rows)

for d in sorted(contracts, key=lambda k: -contracts[k]):
    singles = sum(1 for m in modules[d] if per_module[m] == 1)
    print(f'{d:16s} {contracts[d]:4d} {len(modules[d]):4d} {singles:4d}')

with_method = [s for _, _, s in rows if 'method' in s]
print('with method:', len(with_method))
```

`with method:` 那一行是族规则审计的分母，见同目录的族规则审计。
