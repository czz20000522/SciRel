# C4 使用验收 · 第二轮（独立消费者）

这一轮是 #249 C4 的第二轮独立消费：**只拿新打的分发包**，把
[../tasklist.json](../tasklist.json) 里 73 条预先固定的任务全部跑一遍，逐条判定
"只用这个包能不能完成"，并把缺口按级别记进 [GAPS.md](GAPS.md)。

包本体与 wheel **不进仓库**（wheel 929 KB、包 6.8 MB）。回执只写 sha256 与复跑命令，
任何人从同一提交重打一遍即可逐字节比对。

## 包指纹

| 项 | 值 |
| --- | --- |
| wheel | `scirel-0.0.0-py3-none-any.whl`，929274 B |
| `wheel_sha256`（= `runtime.runtime.wheel_sha256`） | `4fc9757a7b843cc3bce2dc96fd2280b27299cff93fbcf5b64a2321b58234f5d7` |
| `snapshot_sha256` | `cf0269b61ba19d8b2e5e008a6a4a4d80f2cd701f78c34f2fcb3b16eed9a2593c` |
| `source_revision` | `4b5b4aaa38650d8a902e4265f226175d166a426b` |
| `asset_count` / 包内合同数 | 249 / 249 |
| `tasks_digest`（冻结清单摘要） | `2c55ae00de0f60e4930df508d87ae150416a006032809a5cf96890e3470198d3` |
| 消费者解释器 | CPython 3.14.7，numpy 2.5.4，scipy 1.18.1，mpmath 1.4.1 |

`validate_installed_wheel` 的结论见 [receipt.json](receipt.json) 的
`installed_wheel_validation` 段：`status: PASS`、`errors: []`、`artifact.sha256` 与包内
`runtime.json` 逐字相同、`package.in_source_tree: false`、`runtime.is_virtualenv: true`、
`runtime.external_site_paths: []`。

## 从零复跑

全部命令在 clone 根目录执行（`<wt>` 为本 worktree）。

```sh
git fetch origin
git worktree add .worktrees/c4r2 -b agent/c4-round2 origin/main
cd .worktrees/c4r2
python3 scripts/dev.py prepare

# 1. wheel 与交付包（用全新的输出目录，不覆盖已有回执）
python3 scripts/dev.py run uv build --wheel --out-dir .runtime/c4r2/wheel
python3 scripts/dev.py run python -B scripts/build_pure_delivery.py \
  --wheel .runtime/c4r2/wheel/scirel-0.0.0-py3-none-any.whl \
  --output .runtime/c4r2/scirel-delivery-r2

# 2. 隔离 venv，只装包里的 wheel 与它自己的 requirements
export UV_PYTHON_INSTALL_DIR=$PWD/.runtime/python UV_CACHE_DIR=$PWD/.runtime/uv-cache
uv venv --seed --python 3.14.7 .runtime/c4r2/venv-consumer
uv pip install --python .runtime/c4r2/venv-consumer/bin/python \
  .runtime/c4r2/scirel-delivery-r2/wheel/scirel-0.0.0-py3-none-any.whl \
  -r .runtime/c4r2/scirel-delivery-r2/runtime-requirements.txt

# 3. 已装 wheel 校验
.runtime/c4r2/venv-consumer/bin/python -I scripts/validate_installed_wheel.py \
  --expected-python 3.14 \
  --wheel .runtime/c4r2/scirel-delivery-r2/wheel/scirel-0.0.0-py3-none-any.whl \
  --catalog-root . \
  --source-revision 4b5b4aaa38650d8a902e4265f226175d166a426b \
  --output .runtime/c4r2/installed-wheel-validation.json

# 4. 73 条任务（每条一个独立解释器进程）
SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4r2/scirel-delivery-r2 \
  .runtime/c4r2/venv-consumer/bin/python -I \
  examples/c4-usage-acceptance/round2/run.py

# 5. 覆盖矩阵
python3 examples/c4-usage-acceptance/round2/coverage.py
```

`run.py` 每条任务都起一个新进程，任务之间不共享库状态；跑完写
`tasks/<task-id>.json`、`results.json`、`calls.jsonl`。

## 本轮结果（2026-11-17 实测）

| 指标 | 值 |
| --- | --- |
| 任务 | 73 / 73 执行 |
| `package_sufficient` | **48 true / 25 false**（通道修订时 47/26；复核前 43/30） |
| 判据 | **272 条：224 pass、41 fail、7 not-run**（通道修订后 269/221/41；复核前 196/66；初版 191/77/5） |
| 按 kind | nominal 25/43 sufficient；failure 21/23；inapplicable 1/1；cross **1/6** |

> 这一版是**复核后**的数字。初版（`13cfaa00`）把 8 类阻塞缺口报得偏重，其中 6 类经最小复现
> 确认是消费者侧判据错误（因子写反、`np.size` 读标量、转置方向、调用构造、绑错调用点、
> 发明合同没有的接口），逐条见 [GAPS.md](GAPS.md) 第六节。
>
> 另有一条**判据缺口**已补：合同恰好声明 1 个输出、入口按位置返回裸值时，`fields` 判据原先
> 必然 fail。现在这类返回在类型/形状相容时判 pass，并在记录里注明
> `single declared output returned positionally`；`outputs ≥ 2` 仍判 fail。25 条判据因此
> 由 fail 转 pass（196/66 → 221/41），`package_sufficient` **一条未变**。
>
> 随后修了自己的三个工具缺陷（`review.py` 未定义的 `_val`、`check_fields` 丢失的 mapping 返回、
> residual 的 `list(float)`）。其中第一个让 `diagnostics-rejects-shape-mismatch` 自复核批次起
> 一直以"崩溃记录"冒充结果；修好后该任务变为 3 条判据、`package_sufficient: true`，
> 总数因此是 **48/25、272 条 224/41/7**。详见 GAPS 6.9.1 与 `receipt.revision.defects_fixed_in_harness`。
> 逐条见 `receipt.json` 的 `revision.single_output_channel`。

按 domain 的覆盖矩阵用 `coverage.py` 复算（每格的"已覆盖"= 该域任务全部执行，
"sufficient"= 该域里只用包就能完成的条数）：

```text
domain            tasks  ran  sufficient  criteria(pass/total)  fail  not-run
closures             2    2           2          6/6               0       0
collisions           4    4           2          6/10              4       0
configurations       2    2           2          5/8               3       0
cross                6    6           0         12/30             18       0
diagnostics          2    2           1          6/7               1       0
dielectric           2    2           1          5/7               1       1
electromagnetism     2    2           1          5/8               3       0
equilibrium          3    3           2         10/11              0       1
field                3    3           2         10/13              3       0
fusion               2    2           1          4/6               2       0
fvm                  2    2           2          7/8               1       0
geometry             8    8           5         21/29              8       0
inference            2    2           1          6/7               1       0
io                   2    2           0          3/10              7       0
kinetic             10   10           6         26/38              9       3
mirror               3    3           3         11/12              1       0
neoclassical         2    2           1          6/7               1       0
neutrals             6    6           3         15/20              5       0
numerics             3    3           2          7/10              3       0
physics              2    2           1          5/7               2       0
plasma               2    2           2          6/7               1       0
source               3    3           3          9/12              3       0
```

21 个 domain 全部执行；**没有**任何 domain 只有一条任务代表——每个 domain 的任务数由
冻结清单的配额给出（见 [../README.md](../README.md)「配额怎么来的」）。

失败路径：23 条 `failure` 任务全部**真实调用**并记录实际异常，其中 19 条的异常类型与合同
声明一致；4 条不一致（`sampling-rejects-unknown-method`、`fieldline-rejects-duplicate-vertices`、
`electromagnetism-rejects-missing-mesh`、`diagnostics-rejects-shape-mismatch`），逐条见
[GAPS.md](GAPS.md) 的 B6/B7 与流程第 2 条。

跨域（复核后）：6 条中 1 条通过（`cross-field-to-equilibrium`，flux 按网格 reshape 后
Picard 步接受它，有限差分对照偏差 0.0），其余 5 条断点逐条记在 [GAPS.md](GAPS.md) B8 与第六节。

## 消费者只用了什么

允许：包目录（`catalog/contracts`、`catalog/capability-index.json`、`wheel/`、`skills/`、
`runtime.json`、两份 requirements）、只用这些建出的 venv、本任务清单、三个使用 skill。

没有读：本仓库的 `src/`、`tests/`、`catalog/review/`、任何维护者参照值。本目录下的
`harness.py` 与 `checks/` 是消费者**自己写的**验算代码，不是库的一部分。

调用参数从合同自己的 `example` 块取：`harness.discover()` 解析该块 AST，把对入口的调用
改写成记录器，在一次性命名空间里执行，从而拿到 example 用到的**实际参数**（含依赖前序
语句构造的数组/对象）。它不替换包的任何模块属性；example 的最后一次调用若是拒绝探针，
默认取第一条声明调用，需要别的变体的检查用 `ctx.pick(...)` 显式指定。

## 产物

| 文件 | 内容 |
| --- | --- |
| `tasks/<task-id>.json` | 逐条结果：`assets_used`、`calls`（参数/状态/异常/警告/返回字段）、`answer`（数值+单位）、`independent_check`（怎么验算、差多少）、`criteria`、`package_sufficient`、`gaps` |
| `results.json` | 包指纹 + 环境版本 + 逐任务结果索引 + 汇总 |
| `calls.jsonl` | 全部公开调用按执行顺序逐行记录 |
| `GAPS.md` | 分级缺口（阻塞 / 影响可信度 / 体验 / 流程），每条写清妥协 |
| `coverage.py` | 按 domain / kind 重算覆盖矩阵 |
| `harness.py`、`checks/` | 消费者侧驱动与逐任务验算代码 |

## 这份记录不证明什么

- 不证明物理正确性。C4 只判"能不能按合同正确使用"，物理归 C1。
- 不证明全库覆盖。73 条任务覆盖的是清单声明的代表任务；`family` 字段只有 3 份合同有，
  族级覆盖无法核对（见 [../README.md](../README.md) 的已知限制）。
- 判据只能落在 `pass` / `fail` / `not-run` 三态；`not-run` 一律**不**计为通过，并且在
  [GAPS.md](GAPS.md) 里写明为什么没能评估。
- 消费者手里的输入只有合同 example 与清单冻结值；需要清单之外输入才能触发的判据，
  本轮记为 `not-run` 而不是换一个输入凑一个数。
