# C4 第二轮 · 分级缺口

本轮结论的数字：73 条任务全部执行（每条的 `calls` 都非空或按合同不产生调用），
`package_sufficient` 43 条为 true、30 条为 false；273 条判据里 191 pass、77 fail、
5 not-run。`not-run` 不计入通过。

下面按"阻塞 / 影响可信度 / 体验 / 流程"分级。每条写清**我做了什么妥协**——妥协不是
"下次注意"，而是这次结论的适用边界。

---

## 一、阻塞（只看包的消费者做不完或有判据无法成立）

### B1. 21 份资产的合同声明了命名输出，入口返回裸值（25 条判据因此 fail）

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

`assemble_fluid_dispersion_matrix` 在声明参数（`max_harmonic=0, n_species=1`）下返回
`matrix_size = 1`，而 `M` 的形状是 `(40, 40)`；`state_layout` 也不是合同声明的
`[vx_snl, vy_snl, vz_snl, Ey, Ez, By, Bz]`。用声明的振荡计数重算应为
`3*S*sum(L)+4 = 40`。判据 `declared_layout` fail。

**妥协：** 我把"矩阵维度"当作可核对的部分（40 与我按公式重算的 40 一致），
`matrix_size` 字段单独记为不一致；没有改用 `M.shape` 去"修好"`matrix_size`。

### B4. `collisions.atomic-hydrogen-charge-exchange-rate-coefficient` 的上钳位不成立

合同声明温度钳位；把输入推到钳位之上（1e5 eV 对 2.5e4 eV 上限）后返回值与钳位点相差
**78%**（判据 `declared_clip` fail，`clip_relative_deviation = 0.782`）。同时该入口返回
`ndarray`（见 B1）。

**妥协：** 我用同一入口在钳位点与钳位之上的两次调用做对照，没有另找第一个钳位值去试
——清单只允许一次冻结替换。

### B5. `field.current-green-superposition` 的线性叠加不成立

把声明的 `currents` 全部乘 2 后，`psi`/`BR`/`BZ` 只放大了 1.25 倍（相对偏差 0.75）；
用返回的 Green 列手工求和与 `psi` 的相对偏差是 0.667。判据 `linearity`、`entryagreement`、
`budget` 全部 fail。

**妥协：** 我没有去猜"权重也许被归一化"这类解释，也没有更换输入重试；这两条判据按实测
记账。是否属于消费者对 `weights` 语义的误读，需要维护者判断——合同把它叫 declared source
weight。

### B6. 两条"声明拒绝"实际不可达

| 任务 | 声明 | 实际 |
| --- | --- | --- |
| `electromagnetism-rejects-missing-mesh` | `mesh` 缺失抛 `ValueError` | `Device(mesh=None)` 正常返回 |
| `diagnostics-rejects-shape-mismatch` | 形状不匹配抛 `ValueError` | 冻结 stimulus（`[[1.0, 2.0]]`）与基线同形，正常返回 |

**妥协：** 我按冻结 stimulus 原样只换一个字段，没有另造一个"更像不匹配"的数组。按清单
README 的约定，这两条先按**任务缺陷**登记（stimulus 未触发声明拒绝）。

### B7. `fieldline-rejects-duplicate-vertices` 抛 `TypeError` 而非声明的 `ValueError`

实际异常：`TypeError: list indices must be integers or slices, not tuple`——来自入口内部
索引，而不是"重复顶点"的声明拒绝。`sampling-rejects-unknown-method` 同类：期望
`ValueError`，实际 `TypeError`，而该资产合同原文写的恰是 `TypeError`（这条是**任务清单**
与合同不一致）。

**妥协：** 我保留了真实异常类型与原文，没有把 `TypeError` 记成 `ValueError`，也没有换
一种输入格式去"拿到"声明的 `ValueError`。

### B8. 六条跨域任务全部未通过（`package_sufficient` 6/6 false）

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
