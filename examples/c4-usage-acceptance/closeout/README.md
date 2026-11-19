# C4 使用验收 · 收口轮（独立消费者）

这是 #249 C4 的第三轮、也是收口轮：**只拿新打的分发包**，把
[../tasklist.json](../tasklist.json) 里 73 条冻结任务全部重跑一遍，另外把
"上一轮之后改过的三处"逐处复核到能回答"改对了没有"的程度。

这页的统计和下面的“逐字节相同”描述的是历史收口轮（当时的装置见提交 `5dcdf944`），不是当前装置的统计。后续单任务复跑及不覆盖历史结果的命令见 [EQDSK 消费复跑](../eqdsk-replay/README.md)。

本轮不继承上一轮的结论，只继承它的**装置**：`checks/` 与 `harness.py` 是
[../round2/](../round2/) 的逐字节拷贝（`diff` 为空，见下），因此本轮与上一轮的数字差
**不可能是判据改写造成的**。新增的检查全部在 `audits.py` 里，与本轮 73 条任务的
272 条判据分开计。

| 轮次 | 包源 revision | `package_sufficient` | 判据 pass/fail/not-run |
| --- | --- | --- | --- |
| round2（历史回执，未改动） | `4b5b4aaa` | 48 / 73 | 224 / 41 / 7（272 条） |
| **closeout（本轮）** | **`d429359d`** | **48 / 73** | **225 / 40 / 7（272 条）** |

差的 1 条判据是 `physics-coulomb-logarithms.fields`（fail → pass），原因是
`physics.thermal-energy` 现在返回 `Result`、其字段名与合同声明的三个输出一致。
除此之外 73 条任务**没有任何一条**判据改变、没有任何一个数值改变。

## 包指纹

| 项 | 值 |
| --- | --- |
| wheel | `scirel-0.0.0-py3-none-any.whl`，929589 B |
| `wheel_sha256`（= `runtime.json → runtime.wheel_sha256`） | `f1501a3efbdaba7b18c9af7be06ff30d9a33caf2777534de71f6833b93938b2a` |
| `snapshot_sha256` | `7572961c553ecca28c506a392297d514b714eb1fcdffccfff262618d75b60bf3` |
| `source_revision` | `d429359dcfbf37aedf09aa64cfa78b89da3b3623` |
| `asset_count` / 包内合同数 | 249 / 249 |
| `tasks_digest`（冻结清单摘要） | `2c55ae00de0f60e4930df508d87ae150416a006032809a5cf96890e3470198d3` |
| 消费者解释器 | CPython 3.14.7，numpy 2.5.4，scipy 1.18.1，mpmath 1.4.1 |

`validate_installed_wheel`（`scripts/validate_installed_wheel.py`，输出在
`.runtime/c4close/installed-wheel-validation.json`，不进仓库）的结论：
`status: PASS`、`errors: []`、`artifact.sha256` 与包内 `runtime.json` **逐字相同**、
`package.in_source_tree: false`、`runtime.is_virtualenv: true`、`runtime.external_site_paths: []`。

包的源 revision 是 `d429359d`。`origin/main` 在本轮运行期间前进到 `9d5aad1c`，
两者之间只改了 `docs/maintainer/resource-recovery-plan.md` 一个文件
（`git diff --name-status d429359d..origin/main` 仅此一行），该文件不进交付包，
所以本轮的包内容与当前 `main` 的分发包内容一致。

## 从零复跑

全部命令在 clone 根目录（`<wt>` 为本 worktree）执行，新目录、不覆盖任何已有回执。

```sh
git fetch origin
git worktree add .worktrees/c4co -b agent/c4-closeout origin/main
cd .worktrees/c4co
python3 scripts/dev.py prepare

# 1. wheel 与交付包
python3 scripts/dev.py run uv build --wheel --out-dir .runtime/c4close/wheel
python3 scripts/dev.py run python -B scripts/build_pure_delivery.py \
  --wheel .runtime/c4close/wheel/scirel-0.0.0-py3-none-any.whl \
  --output .runtime/c4close/scirel-delivery-close

# 2. 隔离 venv，只装包里的 wheel 与它自己的 requirements
export UV_PYTHON_INSTALL_DIR=$PWD/.runtime/python UV_CACHE_DIR=$PWD/.runtime/cache/uv
uv venv --seed --python 3.14.7 .runtime/c4close/venv-consumer
uv pip install --python .runtime/c4close/venv-consumer/bin/python \
  .runtime/c4close/scirel-delivery-close/wheel/scirel-0.0.0-py3-none-any.whl \
  -r .runtime/c4close/scirel-delivery-close/runtime-requirements.txt

# 3. 已装 wheel 校验
.runtime/c4close/venv-consumer/bin/python -I scripts/validate_installed_wheel.py \
  --expected-python 3.14 \
  --wheel .runtime/c4close/scirel-delivery-close/wheel/scirel-0.0.0-py3-none-any.whl \
  --catalog-root . \
  --source-revision d429359dcfbf37aedf09aa64cfa78b89da3b3623 \
  --output .runtime/c4close/installed-wheel-validation.json

# 4. 先自检装置，再跑 73 条
export SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close
.runtime/c4close/venv-consumer/bin/python -I examples/c4-usage-acceptance/closeout/selfcheck.py
.runtime/c4close/venv-consumer/bin/python -I examples/c4-usage-acceptance/closeout/run.py

# 5. 三处重点复核
.runtime/c4close/venv-consumer/bin/python -I examples/c4-usage-acceptance/closeout/audits.py

# 6. 覆盖矩阵与本回执
python3 examples/c4-usage-acceptance/closeout/coverage.py
python3 examples/c4-usage-acceptance/closeout/make_receipt.py
```

退出码按仓库惯例区分：`selfcheck.py` 0 = 全通过；`run.py` 0 = 每条子任务的
readback 都通过（本轮 4 条子任务返回 1，见下"本轮结果"）；`audits.py` 0 = 全部判据
观测到了，**1 = 判据失败（这是包的问题，不是装置崩溃；崩溃会打 traceback 且不写产物）**。

## 本轮结果

| 指标 | 值 |
| --- | --- |
| 任务 | 73 / 73 执行（每条一个独立解释器进程） |
| `package_sufficient` | **48 true / 25 false** |
| 判据 | **272 条：225 pass、40 fail、7 not-run** |
| 按 kind | nominal 25/43、failure 21/23、inapplicable 1/1、cross **1/6** |
| 装置自检 | `selfcheck.py` 19/19 pass，`ruff` PASS |
| 子任务 readback 返回 1 | 4 条：`neutrals-velocity-mesh`、`collisions-rate-coefficients`、`collisions-rate-averages`、`numerics-splines-and-inverse`（与 round2 完全相同的 4 条；原因记在各自 `tasks/*.json` 的 `gaps`） |

覆盖矩阵由 `coverage.py` 从 `tasks/*.json` 现算，下面这段是它的**原始输出**（不是手抄）：

```text
domain            tasks  ran  sufficient  criteria(pass/total)  fail  not-run
closures             2    2          2          6/6              0       0
collisions           4    4          2          6/8              2       0
configurations       2    2          2          8/8              0       0
cross                6    6          1         18/29             9       2
diagnostics          2    2          2          7/8              1       0
dielectric           2    2          1          6/7              0       1
electromagnetism     2    2          2          8/9              1       0
equilibrium          3    3          2         10/11             0       1
field                3    3          3         13/13             0       0
fusion               2    2          1          5/6              1       0
fvm                  2    2          2          8/8              0       0
geometry             8    8          6         27/29             2       0
inference            2    2          1          6/7              1       0
io                   2    2          0          3/10             7       0
kinetic             10   10          6         27/38             8       3
mirror               3    3          3         11/12             1       0
neoclassical         2    2          1          6/7              1       0
neutrals             6    6          3         16/20             4       0
numerics             3    3          2          9/10             1       0
physics              2    2          1          6/7              1       0
plasma               2    2          2          7/7              0       0
source               3    3          3         12/12             0       0

kind            ran  sufficient
nominal          43          25
failure          23          21
inapplicable      1           1
cross             6           1

TOTAL tasks=73 sufficient=48 insufficient=25 criteria=272 pass=225 fail=40 not-run=7
```

> 上一轮 README 里那张同格式的表与它自己 `round2/results.json` 有 15 行不一致
> （例如 `cross` 写 sufficient 0，而 results.json 是 1）。本轮的表是脚本输出，
> 逐格可用 `coverage.py` 复算；差异本身记在 [GAPS.md](GAPS.md) 第四节。

## 与 round2 逐任务 diff

`make_receipt.py` 把两轮的**每条判据 id** 与**每个 answer 值**逐项比对，结果写进
[receipt.json](receipt.json) 的 `diff_vs_round2`：

| 类别 | 条数 | 明细 |
| --- | --- | --- |
| 判据从 fail 变 pass | **1** | `physics-coulomb-logarithms :: fields` |
| 判据从 pass 变 fail（反向变差） | **0** | — |
| 其它判据变化（pass↔not-run 等） | 0 | — |
| answer 数值发生变化 | **0** | — |
| answer 里非数值的差异 | 2 条任务 | `configurations-retained-geometries`（对象 repr 里的内存地址）、`io-rejects-bad-and-missing-input`（临时目录路径）；由 `make_receipt.py::_repr_only` 识别并单列，不计为测量变化 |

**反向变差为零的归因**：`closeout/checks/` 与 `round2/checks/` 逐字节相同
（`diff -r` 除 `__pycache__` 外无输出），`harness.py` 也逐字节相同
（`diff` 无输出），因此在判据装上两轮是同一个装置；剩下的唯一变量是包。

## 三处重点复核

完整数据在 [focus-audit.json](focus-audit.json) 与 [contract-audit.json](contract-audit.json)，
下面只写结论和可粘贴的最小复现。

### 1. `physics.thermal-energy` 改成返回 `Result`：改形状未改数值

- **按名取到值**：`W_el=7.8`、`W_ion=11.7`、`W_tot=19.5`（`attribute` 与 `item` 两条路径同值，差值 0）。
- **独立复算**：按合同 `identity.definition` 的 `1.5*sum(p*vpr*drho_norm)`，用
  `fractions.Fraction` 从**合同 example 的字面参数**（`p_el=[2,2]`、`p_ion=[3,3]`、
  `p_tot=[5,5]`、`vpr=[2.0,3.0]`、`drho_norm=[0.4,0.6]`）精确算出
  `7.8 / 11.7 / 19.5`，与按名读到的值相对偏差 **0.0**。
- **两条与 example 无关的关系**：`p_tot = p_el + p_ion` 时 `W_tot - (W_el+W_ion)` 相对偏差 **0.0**；
  把 `vpr` 加倍后三个通道同时加倍，相对偏差 **0.0**。

复现（原文）：

```sh
SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close \
  .runtime/c4close/venv-consumer/bin/python -I -c "
from scirel.physics import calculate_stored_thermal_energy as f
r = f([2,2],[3,3],[5,5],[2.,3.],[.4,.6])
print(type(r).__name__, list(r), r.W_el, r.W_ion, r.W_tot)"
```

> **上一轮记录的数值不能当基线**：`round2/tasks/physics-coulomb-logarithms.json` 的第 3 次调用
> 记的是 `returned_type: "tuple"`、`returned_fields: null`，**没有存任何数值**
> （`calls.jsonl` 同样不存返回值）。所以"数值没变"这句话不能引 round2 作证，
> 只能由合同定义 + 精确复算给出；这也是本审计把 oracle 写在消费者侧（`audits.py::exact_energy`）的原因。

### 2. 单输出合同"按位置返回"：只看合同能不能拿到值

本轮对**包内全部 249 份合同**做了通道审计，其中 138 份只声明 1 个输出：

| 合同文本怎么说 | 份数 | 运行时是否一致 |
| --- | --- | --- |
| `outputs[0].description` 明写 `single positional value` | **13** | 13/13 一致（返回的不是 mapping） |
| `outputs[0].description` 明写 `Field of the returned … Result mapping` | 5 | 5/5 一致（返回 `Result`，且声明名就是键） |
| 沿用既有写法 `returned directly as an array`（`numerics.faddeeva`，上一轮之前就有） | 1 | 一致 → 与上一项合计"已声明"14 份，19 条运行时全部一致 |
| **完全没写返回通道** | **119** | 见下表 |

那 119 份里，只看合同会遇到什么（`contract-audit.json` 每行的 `runtime.verdict` 与 `keys_named_in` 是逐份记录）：

| 运行时行为 | 份数 | 契约读者能否拿到值 |
| --- | --- | --- |
| 直接返回裸值（"单输出按位置"的常识解读成立） | 84 | 能 |
| 返回 mapping，合同声明的输出名正好是键（`dtype`/`shape` 已写 `mapping`） | 8 | 能，但要先知道"去键里取"——通道本身仍没写 |
| 返回 mapping，声明名不是键，**键名在 `constraints`/`dtype`/`shape` 里逐个列全** | 19 | 能，靠散文（例：`neutrals.thermal-speed-scale` 的 `constraints` 写明 "Carries exactly one field thermal_speed_m_s"） |
| 键是调用方给的轮廓层级（`constraints`："Keys … follow contourset.levels/allsegs"） | 2 | 能，合同给了取键的规则，天然不可能列全 |
| **`kinetic.fluid-case-state`：返回 31 个键，散文只出现其中 1 个（`kz`）** | 1 | **不能**枚举 |
| **`kinetic.multifluid-frequency-solve`：返回 12 个键，`constraints`+`shape` 只覆盖 5–6 个** | 1 | **不能**枚举（`componentwise_backward_errors`、`refinement`、`state_scales`、`zero_structure` 等没在合同里出现） |
| **`io.eqdsk-class`：构造出来是空 mapping，键集属于 EQDSK 规范，本合同的散文没列**（`io.read-geqdsk` 的 description 列了，但那是另一份合同） | 1 | **不能**从本合同拿到键 |
| 合同 example 需要一个先存在的文件（`io.read-eqdsk`/`read-geqdsk`/`write-eqdsk`），本次审计**未观测** | 3 | 未观测 |

所以"单输出合同读不到值"的硬结论只有 **3 份**（两个 mapping 键集不全 + 一个空 mapping），
比"119 份都没写通道"这个统计数字小得多：没写通道不等于读不出值，**但"要读散文才知道怎么读"本身是缺口**。

**关于本轮任务书里"21 份"这个数字**：包内实际把"按位置返回"写进单输出合同 `outputs[0].description` 的是 **13 份**
（`8f52863b` 批 1 的 11 份 + 批 2 的两个 `meridional-polar-*`），加上既有写法的 `faddeeva` 共 14 份；
`21` 是那次"逐份裁决"的范围（其中 `physics.thermal-energy` 改成 `Result`、`field.circular-filament-green` 判无需改动）。
本轮的 13 无关紧要地一致，但 21 这个数在包里**对不上**——按 21 去找会少 8 份。

复现（`kinetic.fluid-case-state`：合同只说 "Complete species scales and source material metadata"，
实际返回 31 个键）：

```sh
SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close \
  .runtime/c4close/venv-consumer/bin/python -I -c "
import json, sys; sys.path.insert(0, 'examples/c4-usage-acceptance/closeout')
import harness as H
a = 'scirel.kinetic.fluid-case-state'
o = H.contract(a)['outputs'][0]
print('declared name/dtype/shape:', o['name'], '|', o['dtype'], '|', o['shape'])
r = H.Ctx({'id': 'x'}).call(a, H.Ctx({'id': 'x'}).named(a))
print('runtime keys:', len(r['returned_fields']), r['returned_fields'][:6], '...')"
```

再对照 `contract-audit.json → channels.rows[]` 里该资产的 `runtime.keys` 与 `runtime.keys_named_in`：
后者为空即"合同里没有这些键名"。

### 3. 五份新增证据子句：子句说的事，只靠包能不能验

17 条可判定的子句，**14 条 pass、0 条与公共行为矛盾、3 条无法只靠包验证**：

| 合同 | 可验且一致 | 无法验证（记 `not-observed`） |
| --- | --- | --- |
| `field.poloidal-field-from-flux` | 返回 `Result` 且 attribute/键同值；二次通量闭式解 `B_R=-R(e+2bZ)`、`B_Z=2(a+eZ+bZ²)`；单幂族 `R^aZ^b` 与有理数闭式在 2.8 eps 内吻合；散度恒等式在返回数组上收在 1.7e-15（项尺度）；常数参考量不改变 `B_R/B_Z` | 子句里的 80/120 位 Biot–Savart 积分对比（包内没有该可调用体，子句也没印出积分式）；子句自称的"6.0 eps"数值界（1.7e-15 ≈ 7.6 eps，差在"term scale"的定义，既不能确认也不能否认） |
| `geometry.path-distance` | 3-4-5 折线精确得到 `(0,3,7)`；二分坐标下整四分之一转角后**逐位相同**；无理长度 `√2` 相对偏差在 4 eps 内（非逐位） | — |
| `numerics.clamped-cubic-spline` | 端点斜率与数据一致时精确复现三次多项式（相对偏差 ≤ 64 eps）；把 `yp` 改成 `(0,0)` 就**不再**精确（说明子句不是空话） | — |
| `numerics.natural-cubic-spline` | 线性函数精确复现（`M=0` 端点，数据与边界条件一致）；同一条三次多项式**不**精确（`O(h^4)` 的说法确实是条件性的） | — |
| `numerics.truncated-svd-inverse` | 恰好落在 cutoff 上的奇异值保留、下一个被丢弃；宽矩阵返回转置形状 `(n,m)` | "手工 SVD 构造只覆盖排列×对角谱"——这句话讲的是维护者测试怎么写的，包里没有可见产物 |

结论：**子句与其声称的公共行为一致（0 条矛盾）**，但其中 3 条不是"只靠包可验"的事实：
2 条讲证据是怎么构造的，1 条印了一个没有印出 stencil 的数值界。这三条在
[GAPS.md](GAPS.md) 记为"影响可信度"级缺口，而**不**计入 pass。

## 消费者只用了什么

允许：包目录（`catalog/contracts`、`catalog/capability-index.json`、`wheel/`、`skills/`、
`runtime.json`、两份 requirements）、只用这些建出的 venv、冻结任务清单。

没有读：本仓库的 `src/`、`tests/`、`docs/maintainer/`、`catalog/review/`。
`harness.py`、`checks/`、`audits.py`、`selfcheck.py`、`coverage.py`、`make_receipt.py`
是本目录下消费者**自己写的**验算代码，不是库的一部分。
`catalog/` 与 `round2/`（本目录内的历史回执）之外的仓库内容只被
`scripts/dev.py`、`scripts/build_pure_delivery.py`、`scripts/validate_installed_wheel.py`
（打包与安装校验）读过——那是本轮规定的重打包步骤，不用于判定库的行为。

## 产物

| 文件 | 内容 |
| --- | --- |
| `tasks/<task-id>.json` | 逐条结果：`calls`（参数/状态/异常/警告/返回字段）、`answer`、`independent_check`、`criteria`、`package_sufficient`、`gaps` |
| `results.json` | 包指纹 + 环境版本 + 逐任务索引 + 汇总 |
| `calls.jsonl` | 全部公开调用按执行顺序逐行记录 |
| `receipt.json` | 包指纹 + 逐任务索引 + **与 round2 的 diff** + 三处重点复核 + `supersedes: ../round2/receipt.json` |
| `contract-audit.json` | 249 份合同的返回通道审计（含 138 份单输出合同的运行时对照） |
| `focus-audit.json` | thermal-energy 数值证据、五份合同 17 条子句的判定、A/B/C 判据 |
| `GAPS.md` | 本轮缺口、与 round2 的对比、仍未关闭的项 |
| `harness.py`、`checks/` | 从 round2 逐字节拷贝的驱动与逐任务验算代码（**未改**，以便 diff 可比） |
| `audits.py`、`selfcheck.py`、`coverage.py`、`make_receipt.py` | 本轮新增/沿用装置；`selfcheck.py` 覆盖 `checks/` 与 `audits.py` 的分支 |

## 这份记录不证明什么

- 不证明物理正确性。C4 只判"能不能按合同正确使用"，物理归 C1；本轮对五份证据子句的判定
  是"子句与公共行为是否一致"，不是"证据是否成立"。
- 不证明全库覆盖。73 条是清单声明的代表任务；`family` 字段只有 3 份合同有，族级覆盖无法核对。
- 判据只落在 `pass` / `fail` / `not-observed`（任务侧叫 `not-run`）三态，`not-observed` 一律不计为通过。
- 本轮 7 条 `not-run` 判据、3 条 `not-observed` 子句、7 份"合同没写通道也读不出值"的单输出合同，
  都是缺口而不是通过：逐条写在 [GAPS.md](GAPS.md)。
