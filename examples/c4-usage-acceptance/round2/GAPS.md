# C4 第二轮 · 分级缺口

> **本文件经过一次复核修订（2026-11-17）。** 初版（提交 `13cfaa00`）报的 8 类阻塞缺口里，
> 有 5 类经维护者指出、并由我逐条最小复现后确认是**消费者侧的判据错误**，另 1 类是我的
> 判据口径错误。修订后的结论：`package_sufficient` **47 true / 26 false**（初版 43/30），
> 判据 269 条 **196 pass / 66 fail / 7 not-run**（初版 273 条 / 191 / 77 / 5）。
> 被推翻的每一条在正文里保留"原判定"原文，并紧接"复核结论"；汇总见
> [第六节「复核：以下判定是消费者侧的错」](#六复核以下判定是消费者侧的错)。

本轮结论的数字（复核后）：73 条任务全部执行（每条的 `calls` 都非空或按合同不产生调用），
`package_sufficient` 47 条为 true、26 条为 false；269 条判据里 196 pass、66 fail、
7 not-run。`not-run` 不计入通过。

下面按"阻塞 / 影响可信度 / 体验 / 流程"分级。每条写清**我做了什么妥协**——妥协不是
"下次注意"，而是这次结论的适用边界。

---

## 一、阻塞（只看包的消费者做不完或有判据无法成立）

### B1. 21 份资产的合同声明了命名输出，入口返回裸值（24 条判据因此 fail）

> **复核后调整：严重度由「阻塞」下调为「影响可信度」。** 值都在，示例本身也按位置使用；问题是合同把概念名写成了字段名，`all_declared_outputs` 观察不到。仍属真缺口，但不阻塞计算。

> **补充（2026-11-17，判据侧修订）：** B1 现在只对 **`outputs ≥ 2`** 的情形成立。合同恰好声明
> **1 个**输出、入口按位置返回裸值时，判据侧补了一条合法通道（见 [6.10](#610-新增1-个声明输出--裸值-通道)）：
> 18 个任务、25 条 `fields` 判据因此由 fail 转 pass，每条都记了
> `"channel": "single declared output returned positionally"` 与所比较的 dtype/返回类型。
> 库没有变化，`package_sufficient` 一条也没有回溯改判。
>
> **分类更正：** 上表把 `field.circular-filament-green` 归进 tuple 组是错的。实测它返回
> `Result`（keys `['gBR','gBZ','gpsi']`，合同 example 也断言 `isinstance(result, Result)`），
> 我自己的 `calls.jsonl` 里记的是 `returned_type=Result`。真正返回 `tuple` 的是**另一个资产**
> `electromagnetism.circular-filament-green`（`compute_greens` 返回 `(psi, br, bz)`）。
> 上表原文保留，此处更正——**清单的分组也会错，分组需要和判定一样复核**（见 6.11）。
> 其余 tuple 组的两项 `geometry.meridional-polar-forward` / `-inverse` 与
> `physics.thermal-energy` 实测确为 tuple（后者是 3 个输出，仍按 B1 记 fail）。

合同 `outputs[]` 写的是字段名，但入口实际返回 `ndarray` / `float` / `tuple` / 对象：

| 返回类型 | 资产 |
| --- | --- |
| `ndarray` | `collisions.atomic-hydrogen-elastic-cross-section`、`collisions.atomic-hydrogen-charge-exchange-rate-coefficient`、`collisions.molecular-hydrogen-charge-exchange-rate-coefficient`、`dielectric.cold-plasma-tensor`、`electromagnetism.loop-flux-matrix`、`geometry.arclength-derivative`、`neutrals.cross-mesh-scalar-interpolation`、`numerics.modal-projection`、`source.gaussian`、`source.exponential`、`neutrals.neutral-generation-propagation` |
| `float` | `geometry.masked-toroidal-volume`、`plasma.fast-ion-heating`、`fusion.dd-neutron-lab-energy` |
| `tuple` | `field.circular-filament-green`、`geometry.meridional-polar-forward`、`-inverse`、`physics.thermal-energy` |
| 对象 | `configurations.trex-coil`、`configurations.brb`、`configurations.wham`、`numerics.orthonormal-modal-basis`（`ModalBasis`）、`fvm.cell-variable`（`CellVariable`） |

`contract_fields` 判据要求"返回字段集合等于合同声明的输出"，裸值没有字段集合，所以这
25 条判据只能记 fail。**这不是"值错了"，而是"合同声明的形状与入口返回的形状不是一回事"。**
两种可能——合同把"概念名"当成了字段名，或入口该返回映射却没返回——需要维护者裁决，
消费者不能替它选。

**妥协：** 对这类资产我用 `H.mapping()` 把裸值绑到合同声明的**唯一**输出名上继续做后续
判据（例如把返回的 `ndarray` 当作 `cross_section_m2`）。这条绑定是我加的约定，不是合同
写的；`fields` 判据仍然记 fail，`package_sufficient` 因此为 false。

### B2. `kinetic.rational-solve-matrix` 只返回 44 个声明输出中的 9 个

返回 `{V, backward_residual, d, ind, indices, omega, w, wg, wi}`；合同声明的 `N`、
`source_pole_order`、`poles`、`residues`、`accepted`、`constant_decimal` 等 35 个字段缺失。
任务 `kinetic-rational-pole` 的 `declared_counts` 判据正好要读 `N`/`source_pole_order`/
`poles`/`residues`，因此只能记 `not-run`。

**妥协：** 无。没有这些字段就无法核对阶数与极点计数；我没有用 `omega` 的长度去反推 `N`。

### B3. `kinetic.fluid-dispersion-matrix` 的 `matrix_size` 与实际矩阵不一致

> **原判定（13cfaa00）保留在上面。复核结论：** **我的判据错了。** 实测 `matrix_size=40`、`M=(40,40)`、`state_layout` 与合同逐字一致；我读到 1 是因为用 `np.size` 对标量取了元素个数。详见第六节 6.2。

`assemble_fluid_dispersion_matrix` 在声明参数（`max_harmonic=0, n_species=1`）下返回
`matrix_size = 1`，而 `M` 的形状是 `(40, 40)`；`state_layout` 也不是合同声明的
`[vx_snl, vy_snl, vz_snl, Ey, Ez, By, Bz]`。用声明的振荡计数重算应为
`3*S*sum(L)+4 = 40`。判据 `declared_layout` fail。

**妥协：** 我把"矩阵维度"当作可核对的部分（40 与我按公式重算的 40 一致），
`matrix_size` 字段单独记为不一致；没有改用 `M.shape` 去"修好"`matrix_size`。

### B4. `collisions.atomic-hydrogen-charge-exchange-rate-coefficient` 的上钳位不成立

> **原判定（13cfaa00）保留在上面。复核结论：** **我的判据错了。** 合同钳位在 2.5e5 eV，实测 2.5e5/5e5/1e6 三点同值 6.399350294468e-15 且带 ApplicabilityWarning；我当初比的 5e4 与 1e5 都在无钳位区。详见 6.3。

合同声明温度钳位；把输入推到钳位之上（1e5 eV 对 2.5e4 eV 上限）后返回值与钳位点相差
**78%**（判据 `declared_clip` fail，`clip_relative_deviation = 0.782`）。同时该入口返回
`ndarray`（见 B1）。

**妥协：** 我用同一入口在钳位点与钳位之上的两次调用做对照，没有另找第一个钳位值去试
——清单只允许一次冻结替换。

### B5. `field.current-green-superposition` 的线性叠加不成立

> **原判定（13cfaa00）保留在上面。复核结论：** **我的判据错了（双重错）。** 权重加倍后 psi/BR/BZ 逐分量正好 2 倍、偏差 0.0；0.75 来自判据写成 `rel_dev(a, 2b)`，0.667 来自把 Green 列按 `[coil,target]` 做 tensordot。详见 6.1。

把声明的 `currents` 全部乘 2 后，`psi`/`BR`/`BZ` 只放大了 1.25 倍（相对偏差 0.75）；
用返回的 Green 列手工求和与 `psi` 的相对偏差是 0.667。判据 `linearity`、`entryagreement`、
`budget` 全部 fail。

**妥协：** 我没有去猜"权重也许被归一化"这类解释，也没有更换输入重试；这两条判据按实测
记账。是否属于消费者对 `weights` 语义的误读，需要维护者判断——合同把它叫 declared source
weight。

### B6. 两条"声明拒绝"实际不可达

> **原判定（13cfaa00）保留在上面。复核结论：** **一条是判据错误、一条是任务缺陷。** `Device(mesh=None)` 构造合法、拒绝在 `psi()`；残差形状的冻结 stimulus 与基线同形。两条都改为"冻结 stimulus 记录不变 + 自加探针证明拒绝存在"。详见 6.5、6.6。

| 任务 | 声明 | 实际 |
| --- | --- | --- |
| `electromagnetism-rejects-missing-mesh` | `mesh` 缺失抛 `ValueError` | `Device(mesh=None)` 正常返回 |
| `diagnostics-rejects-shape-mismatch` | 形状不匹配抛 `ValueError` | 冻结 stimulus（`[[1.0, 2.0]]`）与基线同形，正常返回 |

**妥协：** 我按冻结 stimulus 原样只换一个字段，没有另造一个"更像不匹配"的数组。按清单
README 的约定，这两条先按**任务缺陷**登记（stimulus 未触发声明拒绝）。

### B7. `fieldline-rejects-duplicate-vertices` 抛 `TypeError` 而非声明的 `ValueError`

> **原判定（13cfaa00）保留在上面。复核结论：** **`sampling` 那一半是我的判据错了**：`method=nope` 实测抛 `ValueError`；TypeError 来自我的失败驱动器对含 `*fields` 的签名重复传参，已修。详见 6.4。`fieldline` 那一半仍未定论。

实际异常：`TypeError: list indices must be integers or slices, not tuple`——来自入口内部
索引，而不是"重复顶点"的声明拒绝。`sampling-rejects-unknown-method` 同类：期望
`ValueError`，实际 `TypeError`，而该资产合同原文写的恰是 `TypeError`（这条是**任务清单**
与合同不一致）。

**妥协：** 我保留了真实异常类型与原文，没有把 `TypeError` 记成 `ValueError`，也没有换
一种输入格式去"拿到"声明的 `ValueError`。

### B8. 六条跨域任务全部未通过（`package_sufficient` 6/6 false）

> **原判定（13cfaa00）保留在上面。复核结论：** **两条是我的判据错了**：`cross-field-to-equilibrium` 在 flux 按网格 reshape 后全绿（有限差分对照 0.0）；`cross-kinetic-to-diagnostics` 是我发明了合同没有的 `roots` 观测通道，已改记 `not-run`。其余四条仍成立。详见 6.7、6.8。

| 任务 | 断点 |
| --- | --- |
| `cross-field-to-equilibrium` | 线圈 flux→磁场这一步通过（有限差分对照偏差 0.0，Wb/rad→T 对得上），但把同一 flux 交给 Picard 步时抛 `ValueError: r_grid, z_grid, psi_state and psi_vac must be same-shape [Z,R] grids`——两个域的网格约定（`[R,Z]` vs `[Z,R]`）不兼容 |
| `cross-geometry-to-equilibrium` | 映射输出是 `(9,9,7)` 的 `[R,Z]` 网格，`pressure_flux_state` 要二维 `[Z,R]`，抛 `ValueError: r_grid must be a two-dimensional [Z,R] array`；`clamped_count` 我重算为 0/0，与回报一致 |
| `cross-mirror-to-diagnostics` | 闭合记录里没有 `B`/`p_perp`/`p_parallel` 可交给诊断入口（closure_state 只带 Legendre/quadrature 配置），无法验证 `firehose_margin = B²/μ0 + p_perp − p_parallel` |
| `cross-source-to-neutrals` | profile（1 维）到 propagation 的 forcing（`(2,2,3)`）没有声明的适配器，我自己 reshape 后 doubling 偏差 0.146（判据 fail） |
| `cross-kinetic-to-diagnostics` | 观测入口只认 `flux_loops`/`thomson` 等已登记种类，喂 `roots` 抛 `ValueError: unknown observation kinds: ['roots']`——两个域的"观测"词汇不通用 |
| `cross-collisions-to-neutrals` | 频率入口要求 `(nvr,nvx,nx)` 的三维电荷交换数组并拒绝我传的标量（`ValueError`）；而速率入口返回的是三维数组、合同输出名却是标量 `rate_m3_s` |

**妥协：** 每一处我都只做**必要时**的最小转换（reshape 到声明的网格、取均值把数组变成
per-species 标量），并把转换逐条记进该任务的 `gaps`；没有为了绿而改判据。

---

## 二、影响可信度（判据无法用包内信息独立验证）

以下判据本轮记 `not-run`，**不**计入通过：

1. `kinetic-fluid-two-path` 的 `budget`：合同说"同一状态经两个入口求行列式"，但响应入口
   只返回一个混合量纲的 `result` 字段，没有可指的 determinant 字段。
2. `kinetic-multifluid-frequency` 的 `budget`：单点解与扫描解没有共同的命名字段可比。
3. `equilibrium-isotropic-picard` 的 `residualmeaning`：步进记录给了 `residual`，但没给
   合同定义它时用的前后 flux 数组。
4. `dielectric-cold-tensor` 的 `basisinvariance` 与 `resonance`：合同 example 没有声明转动后
   的基与共振频率；消费者只允许用冻结输入，因此无法触发。
5. `neutrals-upwind-transport` 的反向分支：只重算了正向分支，反向分支未单独重算。
6. 若干检查里我用**有限差分**代替解析导数（`cross-mirror-to-diagnostics` 的 `dp_perp_dB`、
   `cross-field-to-equilibrium` 的磁场对照），偏差记在该任务的 `detail` 里，并在 `gaps` 里
   写明这是消费者侧近似。

**妥协：** 这些位置我把"未评估"显式写成 `not-run`，没有用近似值冒充合同判据；相应任务的
`package_sufficient` 记为 false。

另外有几条判据是**我算错**而不是包错，写在对应任务的 `detail` 里，供下一轮区分：
`geometry-equilibrium-grid`（我用折线长度当路径长度，实测 3.0 vs 0.5）、
`physics-coulomb-logarithms`（1.8% 偏差来自我把 `T` 的单位换算用了 ×1000）、
`neutrals-terminal-reductions`（我在 `terminal_distribution` 上乘 2，但没有先确认该字段
是否就是线性矩的权重）、`inference-parameter-optimization`（日志里的 chi2 与最优参数
对齐方式未确认）。它们仍是 fail，但**不应**被读成库的缺陷。

---

## 三、体验（能用但消费者要自己补的东西）

1. **入口不回报它用了什么**：`kinetic.dielectric-response` 不返回实际谐波截断；
   `kinetic.plasma-dispersion-function` 不返回 method/order；`neoclassical.bootstrap-coefficients`
   不返回 method（`methodrecord` 判据因此 fail）。消费者只能记录"我传了什么"。
2. **单位只活在合同文本里**：返回值没有单位标签，跨域交接必须靠人读合同确认
   （本轮 6 条跨域任务的断点几乎都在这里）。
3. **example 最后一条常是拒绝探针**：`collisions.atomic-hydrogen-elastic-cross-section`、
   `collisions.maxwellian-relative-speed-rate-average` 等 example 以一次会抛错的调用收尾，
   直接取"最后一次调用"当输入会拿到拒绝路径。消费者改成默认取第一条声明调用；
   这条约定应写进 C4 清单的 `input_binding` 说明。
4. **返回裸值的入口让 `example` 与 `outputs` 互相矛盾**（见 B1），文档读者无法判断该按
   `result['rate_m3_s']` 还是按 `result` 本身去用。

---

## 四、流程（这一轮消费自身的妥协）

1. **`min_calls` 与 `inapplicable` 冲突**：`kinetic-excluded-zero-kx` 声明 `min_calls=1`，
   但它的判据要求"不得计算被排除的极限"。我选择**零调用**（诚实产物是引用排除条款），
   并把缺额记成 `process` 级缺口。这是任务清单缺陷，不是包缺陷。
2. **`io` 的拒绝路径需要一个真实文件**：冻结 stimulus 只给文件名（`declared-malformed.eqdsk`），
   我没有凭空造一个畸形 EQDSK 文件内容（那属于清单外的输入），所以两次调用都得到
   `FileNotFoundError`。按合同的 `OSError` 通道看，`FileNotFoundError` 是 `OSError` 子类，
   语义上满足；`EQDSKFormatError` 那一半没有被触发。若下一轮要覆盖，清单应把畸形内容
   一起冻结。
3. **逐任务独立进程**：为免库状态互相影响，73 条任务各起一个解释器进程；代价是启动开销，
   好处是一条任务的异常不会污染另一条。
4. **参数获取方式**：`harness.discover()` 解析合同 example 的 AST，只在 example 自己的
   命名空间里把对入口的调用改写成记录器，然后执行以取得真实参数（含由前序语句构造的数组
   与对象）。它**不替换**包的任何模块属性。第一版我改的是模块属性，结果让懒加载模块进入
   不一致状态；这一版已经去掉那种做法。
5. **异常判据允许子类**：合同写 `OSError` 时接受任何 `OSError` 子类，其余按精确类型比对。
   这条例外写进了 `harness.check_exception`，不在任务清单里。

## 这一节不证明什么

它不判物理对错。B1/B2/B3/B4/B5 这几条是"合同声明的形状/不变量与实际行为对不上"，
需要维护者按真值链裁决是合同错还是代码错；消费者只负责把差异写成可复算的记录。

---

## 六、复核：以下判定是消费者侧的错

维护者用 `src/` 树复核后指出 B3、B5 两条无法复现。我按"最小复现调用 + 预期/实际 + 裁决"
把 8 类逐条重做了一遍（消费者不读 `src/`，只靠调用结果与合同声明对照），结果如下。

| 类 | 最小复现 | 预期（我当初的判定） | 实际 | 裁决 |
| --- | --- | --- | --- | --- |
| **B5** 绿色核叠加标度律 | 见 6.1 | 场不随权重成比例（0.75） | 严格 2 倍，偏差 0.0 | **我的判据错了** |
| **B3** `matrix_size` | 见 6.2 | 返回 1，与 40×40 不符 | `matrix_size=40`，`M=(40,40)`，layout 与声明逐字一致 | **我的判据错了** |
| **B4** 上钳位 | 见 6.3 | 钳位点与钳位之上差 78% | 2.5e5 eV 及以上恒为 `6.399350294468e-15`，并带 ApplicabilityWarning | **我的判据错了**（比错了区间） |
| **B7** `sampling` 未知 method | 见 6.4 | 抛 `TypeError` | `method='nope'` → `ValueError: Unknown interpolation method 'nope'` | **我的判据错了**（调用构造坏了） |
| **B6** `Device(mesh=None)` | 见 6.5 | 应当抛 `ValueError`，实际返回 | 构造合法；`psi()` 抛 `ValueError: a mesh is required for field evaluation` | **我的判据错了**（绑错了调用） |
| **B6** 残差形状不匹配 | 见 6.6 | 冻结 stimulus 应触发 `ValueError` | stimulus 与基线同形 (1,2)，正常返回；真不匹配 (1,2) vs (3,2) 才抛 | **我的判据错了**（stimulus 本身无效，属任务缺陷） |
| **B8** 跨域 flux→Picard | 见 6.7 | 网格约定不兼容 | 形状对齐后通过；`B_R/B_Z` 与 flux 有限差分偏差 0.0 | **我的判据错了**（1-D flux 没 reshape） |
| **B8** roots→观测残差 | 见 6.8 | 两个域"观测"词汇不通用（记为库缺陷） | 观测入口只声明 `flux_loops/thomson/...` 五个通道，`roots` 是我**发明的**通道名 | **我的判据错了**；任务前提本身不可表达，应记 `not-run` |

仍然成立的：**B1**（合同声明命名输出 vs 返回裸值，46 条声明/9 条返回的 B2 也属此类）、
**B2**（`rational-solve-matrix` 46 个声明输出只返回 9 个）、**B8 的 geometry→equilibrium**
（3-D 笛卡尔输出 vs 2-D `[N_Z,N_R]` 入口）、以及 `cross-mirror` / `cross-source` /
`cross-collisions` 三条（断点见第五节表格）。B1 的**严重度从"阻塞"下调为"影响可信度"**：
值都在，只是合同把概念名写成了字段名，`all_declared_outputs` 这一类判据观察不到。

### 6.1 B5 `current-green-superposition`

```python
from scirel.field import superpose_current_green_field
kw = dict(gpsi=[[1.,4.],[3.,5.]], gBR=[[2.,0.],[1.,6.]], gBZ=[[-1.,3.],[2.,4.]])
a = superpose_current_green_field([2.0,-1.0], **kw)   # psi=[-2, 1]  BR=[4,-4]  BZ=[-5, 0]
b = superpose_current_green_field([4.0,-2.0], **kw)   # psi=[-4, 2]  BR=[8,-8]  BZ=[-10,0]
```

预期（我当时）：`b == 2a` 不成立；实际：**逐分量正好 2 倍**，
`max|2a − b| / max|2a| = 0.0`（psi/BR/BZ 三者皆是）。
手算 `gpsi @ currents = [-2, 1]`，与返回值逐位相同。
**错在哪：** 我把判据写成 `rel_dev(a, 2b)`——拿"基线"去比"两倍的双倍值"，
差值恰好是 `3/4 = 0.75`；手算那一半把 `gpsi` 当成 `[coil, target]` 做了
`tensordot(currents, gpsi)`，正确方向是 `[target, coil]` 的 `gpsi @ currents`，
于是得到 0.667 的假偏差。**类型：量纲/转置 + 因子写反，双重错。**

### 6.2 B3 `assembly_fluid_dispersion_matrix`

```python
r = assemble_fluid_dispersion_matrix(... , order_lengths={1: 12}, max_harmonic=0, n_species=1)
r['matrix_size']      # 40
r['M'].shape          # (40, 40)
r['state_layout']     # ['vx_snl','vy_snl','vz_snl','Ey','Ez','By','Bz'] 与合同逐字一致
3*1*sum(order_lengths.values())+4   # 40
```

**错在哪：** 我记录 `matrix_size_returned = int(np.size(v["matrix_size"]))`。
`np.size` 对标量返回 **1**（元素个数），不是它的值 40；另外我用
`np.asarray(order_lengths).ravel()` 处理一个 `{species: length}` 字典，得到 `[12]` 的长度
而不是长度之和。**类型：读了错的字段/容器。**

### 6.3 B4 电荷交换速率的"上钳位"

```python
from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_rate as f
[np.asarray(f([t],[1.0]))[0] for t in (2.5e5, 5.0e5, 1.0e6)]
# 6.399350294468e-15, 6.399350294468e-15, 6.399350294468e-15（后两者带 ApplicabilityWarning）
```

合同写的是"**above 2.5e5 eV** emits ApplicabilityWarning and uses the clipped upper edge"，
实测完全吻合。**错在哪：** 我拿 5e4 与 1e5 两个都落在"无钳位区"的点相比，得出 78% 偏差；
那不是钳位测试。**类型：比较区间选错。**

### 6.4 B7 `regular_grid(method='nope')`

```python
from scirel.geometry.sampling import regular_grid
regular_grid(x, y, x+y, nx=4, ny=5, method='nope')
# ValueError: Unknown interpolation method 'nope' for 2 dimensional data
```

**错在哪：** 我的失败任务驱动器对含 `*fields` 的签名同时按位置和关键字传了 `xx`，
Python 先报 `TypeError: got multiple values for argument 'xx'`，于是"期望 ValueError、
实际 TypeError"。修法：签名含 `*args` 时，星号之前的参数一律按位置传。
**类型：调用构造错误（不是库的错）。**

### 6.5 B6 `Device(mesh=None)`

```python
from scirel.electromagnetism import Device
d = Device(mesh=None)     # 合法
d.psi()                   # ValueError: a mesh is required for field evaluation
```

**错在哪：** 合同说 ValueError 用于 "missing meshes"，我把"缺 mesh"绑到了**构造**调用；
冻结 stimulus 恰好只是把 mesh 设成 None 去构造。**类型：把拒绝绑到了错的调用点。**
（任务缺陷仍在：该 stimulus 无法触发声明拒绝。）

### 6.6 B6 `compute_picard_flux_residual` 形状不匹配

```python
compute_picard_flux_residual(np.array([[3.,4.]]), np.array([[1.,2.]]))   # 正常返回 0.5657
fn([[[3.,4.,5.]]], [[1.,2.],[3.,4.],[5.,6.]])                           # 真不匹配 -> ValueError
```

**错在哪：** 冻结 stimulus `[[1.0, 2.0]]` 与基线 `psi_previous` 同为 (1,2)，本来就不该抛。
**类型：把"任务 stimulus 无效"当成了"库不抛"。** 现在记录保留"冻结 stimulus 未抛"这个事实，
另记一条自加探针证明拒绝路径存在。

### 6.7 B8 `cross-field-to-equilibrium`

```python
g = circular_filament_green_response([[0.35,0.0,1.0]], pts)   # pts = 3x3 网格散点
psi = np.asarray(g['gpsi']).reshape(3,3)
poloidal_field_from_flux(r_grid, z_grid, psi)                  # B_R/B_Z 齐备
pressure_flux_picard_step(r_grid, z_grid, np.zeros((3,3)), psi, np.eye(9), ..., 0.25)  # OK
```

两端声明的 `r_grid` 形状都是 `[N_Z,N_R]`；flux 按同一网格 reshape 后，Picard 步接受它。
`B_R/B_Z` 与 flux 的有限差分对照偏差 **0.0**（Wb/rad → T 的符号与 1/R 因子都对）。
**错在哪：** 我传的是未 reshape 的 1-D flux，且沿用了各资产 example 的不同网格尺寸。
**类型：消费者侧形状/网格错误。**

### 6.8 B8 `cross-kinetic-to-diagnostics`

```python
reduce_observation_residuals(predicted={'roots': ...}, observations={'roots': ...})
# ValueError: unknown observation kinds: ['roots']
```

合同（`identity.definition`）只声明 `flux_loops, thomson.density, electron_temperature,
p_parallel, p_perp` 五个通道。`roots` 是我为了让"handoff"成立而**发明**的通道名。
**类型：判据凭空造了一个合同不提供的接口。**
现在的记录：这一条改记为 `not-run`（两个域之间没有声明的 roots→观测 通道），
`package_sufficient=false` 的理由改成"任务前提不可表达"，而不是"库不通用"。

### 6.9 这一节的意义

`AGENTS.md` 第 7 条要的是"通过 / 失败 / 未观测"三态可判别。我这 6 条误判的共同形状是：
**判据本身对"通过"和"失败"没有分辨力**——因子写反、`np.size` 读标量、转置方向错、
调用构造坏了、比较区间选错、绑错调用点、凭空造接口。它们都会输出一个"看起来像失败"的
数字，而不会报错。修订后的做法：

1. 每条判据都在 `detail` 里写出**被比较的两个量**与**偏差**，而不是只写一个布尔；
2. 失败任务驱动器修好了 `*args` 签名，且所有失败路径同时记录"冻结 stimulus 的结果"与
   "自加探针的结果"，两者分开报告；
3. 判据改错时，`review` 字段保留原判定（`original_12cfaa00`）与改判理由，不删痕迹。

### 6.9.1 第三轮：两处"从未被执行的分支"（消费者侧）

这一节记的不是库的缺陷，是**我的判据/工具本身的缺陷**，符合第七节第六类的判据：
*没被执行过的代码看起来和正确代码一样*。

| # | 位置 | 症状 | 后果 |
|---|---|---|---|
| 1 | `checks/review.py` `_val(...)` | 名字**从未定义或导入** | `diagnostics-rejects-shape-mismatch` 自复核批次起一直是 `crashed=True` + 单条 `readback` 判据。我当时把这份"记录"当成结果读了，还据此说复核探针成立——**关于该刺激的说法其实从未被这份检查产出过** |
| 2 | `harness.check_fields` | 我加单输出通道时**丢了 mapping 分支的 `return`** | 任何返回 mapping 的入口都会 `TypeError: 'NoneType' object is not subscriptable`。潜伏原因：打补丁后我只重跑了裸返回的 18 个任务，全量 73 从未再跑 |
| 3 | `review.py` residual | 把 float 传进 `list()` | 修好 `_val` 后同一任务**再崩一次** |

三条都是"编译通过、导入通过、只在没走过的路径上崩"。处置：

- 修 `_val`、修 `check_fields` 的 mapping 返回、residual 改为不经 `list()`；
- 新增 `selfcheck.py`（13 项）：三种字段形态（mapping 相同/不同、裸单值相容/不相容、裸多值）、
  `_args_for` 的 `*args` 位置参数、任务表与模块注册完整性、**两个 review 检查端到端真跑**、
  ruff；ruff 缺失时退出 **75**（未观测不并入 pass）；
- `diagnostics-rejects-shape-mismatch` 的真实结果因此变为 3 条判据、`package_sufficient=True`。
  这条判据变化属于**修自己的工具**，不是重新判库，已在 `receipt.revision.defects_fixed_in_harness` 记明。

### 6.9.2 `ruff --unsafe-fixes` 的一次误伤（工具链教训）

48 条 lint 里 44 条是 F841（赋值未用）。`ruff --fix --unsafe-fixes` 一并"修"掉了
`ok = False` 这类**初始化**，而该变量在某个不总执行的分支里被读取——于是
`io-eqdsk-roundtrip` 与 `source-profile-integral` 变成 `UnboundLocalError`，
判据从 6 条/5 条塌成 1 条。是全量跑与上一次结果的逐任务 diff 抓到的，两处初始化已恢复。

结论写在这里而不只是修掉：**F841 在本目录不能盲目自动修**，因为它同时覆盖
"真没用的局部变量"和"某条路径不执行时才用到的初始化"。可安全自动修的是 F401（未用导入）
与 F541，F841 只做人工判断。`selfcheck.py` 里的 ruff 步骤保留完整规则集（现在全绿），
但**如何修**由人决定，不由 `--fix` 决定。

### 6.10 新增「1 个声明输出 ↔ 裸值」通道

**问题：** `harness.check_fields` 在返回不是 mapping 时置 `returned_fields=None`，随后要求它
等于合同声明输出名的集合。于是**单输出资产无论合同怎么写都必然 fail**——`c2-result` 正按真值链
把 11 份单输出合同改成"按位置返回该 ndarray"，改完我的判据仍会判 fail。那不是库的问题，
是判据缺一条合法通道。

**通道规则（`harness._single_output_channel`）：**
1. 合同 `outputs` 恰好 1 项，且入口返回的不是 mapping；
2. 返回类型与声明 `dtype` 相容：`tuple` 声明要求 tuple/list；`array/float64/complex128` 要求
   ndarray/list/数值；`Python float`/`scalar` 要求数值标量；类名声明（`TREXCoil`、`CellVariable`、
   `ModalBasis`）要求返回类型名匹配或为对象实例；
3. 声明 `shape: scalar` 时额外要求返回标量；
4. 判 pass 时记录里必须写明 `"channel": "single declared output returned positionally"`，
   并附 `declared{name,dtype,shape}`、`returned_type` 与逐项 `checks`。
5. **`outputs ≥ 2` 而返回裸值仍然 fail**（`physics.thermal-energy` 的 `W_el/W_ion/W_tot` 就是这一档，
   它正在被 `c2-result` 改成返回 `Result`）。

**效果：** 18 个任务、25 条判据 fail → pass；判据汇总 269 条里 196/66/7 → **221/41/7**；
`package_sufficient` **0 条变化**（仍是 47/26），因为这些都是"判据缺口"，不是库或结论的变化。
逐条清单在 `receipt.json` 的 `revision.single_output_channel.criteria_flipped`；
按**资产**（而不是按任务）分组的版本在 `revision.single_output_channel.by_asset`，
要点是：**25 条判据全部落在 21 个"恰好 1 个声明输出"的资产上**，没有任何 `outputs ≥ 2`
的资产出现在这张表里——翻转确实集中在单输出资产，没有波及其他。

| 资产 | 声明输出 | dtype | 返回类型 | 判据数 |
| --- | --- | --- | --- | ---: |
| `scirel.collisions.atomic-hydrogen-elastic-cross-section` | `cross_section_m2` | float64 array | ndarray | 1 |
| `scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient` | `rate_m3_s` | float64 array or scalar | ndarray | 1 |
| `scirel.configurations.trex-coil` | `source` | BRB | BRB | 1 |
| `scirel.configurations.trex-coil` | `source` | TREXCoil | TREXCoil | 1 |
| `scirel.configurations.trex-coil` | `source` | WHAM | WHAM | 1 |
| `scirel.dielectric.cold-plasma-tensor` | `epsilon_r` | complex128 | ndarray | 1 |
| `scirel.electromagnetism.circular-filament-green` | `response` | float64 | tuple | 1 |
| `scirel.electromagnetism.device` | `source` | Device | Device | 1 |
| `scirel.electromagnetism.loop-flux-matrix` | `G` | float64 | ndarray | 1 |
| `scirel.fusion.dd-neutron-lab-energy` | `neutron_energy_kev` | float | float | 1 |
| `scirel.fvm.cell-variable` | `variable` | CellVariable | CellVariable | 1 |
| `scirel.geometry.arclength-derivative` | `derivative` | float64 | ndarray | 1 |
| `scirel.geometry.masked-toroidal-volume` | `volume` | Python float | float | 1 |
| `scirel.geometry.meridional-polar-forward` | `position_and_vector` | float64 tuple | tuple | 2 |
| `scirel.geometry.regular-grid` | `grid_and_fields` | float64 | tuple | 1 |
| `scirel.neutrals.cross-mesh-distribution-interpolation` | `fb` | float64 array | ndarray | 1 |
| `scirel.neutrals.neutral-generation-propagation` | `generation` | float64 array | ndarray | 1 |
| `scirel.numerics.modal-projection` | `coefficients` | float64 | ndarray | 1 |
| `scirel.numerics.orthonormal-modal-basis` | `basis` | ModalBasis | ModalBasis | 1 |
| `scirel.plasma.fast-ion-heating` | `ion_fraction` | float64 | float | 1 |
| `scirel.source.gaussian` | `profile` | float64 array | ndarray | 4 |

### 6.11 清单的分组也需要复核，不只是判定

B1 的原始表格按"返回类型"给 21 份资产分组，其中 `field.circular-filament-green` 被归到 tuple，
而它实测返回 `Result`——真正返回 tuple 的是 `electromagnetism.circular-filament-green`。
这跟前面六条数值误判是同一类问题的另一面：

- 数值判据错，会给出一个**看起来像失败**的数字；
- **分组错**，会让读者按错误的类别去找证据（"tuple 组要按位置解包"对 `Result` 不成立），
  而且它不会触发任何检查——表格没有自校验。

因此分组也要复核，并且分组应尽量**从记录生成**（`calls.jsonl` 的 `returned_type` +
`receipt.revision.single_output_channel.criteria_flipped`），而不是手写。本文件 B1 的表格
现在就是"手写分组 + 事后更正"的例子，保留原样以便看出代价。
