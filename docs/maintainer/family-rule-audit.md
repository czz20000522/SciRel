# 族规则审计：总纲 §6 的 `method=` 规则执行到什么程度

状态：**第 1~2 节是一次性审计（`main` @ `7f1eef8c`，2026-11-17）；第 3 节的判据与第 6 节的处置原则是持久的。**
本文件**不改代码、不改合同、不改测试**，供维护者裁决。

## 0 结论先写

审计对象是 249 份合同。这是它给三份产出里最关键的一份，因为它回答一个具体问题：
**总纲 §6 的"同族合成一个函数 + `method=`"规则，是没被执行，还是那些合同本就不是同族？**

答案是**两条同时成立**，而且它们的比例可量化：

| 判定 | 合同数 | 含义 |
| --- | --- | --- |
| **该合族** | **15**（6 组） | 只改一个选择参数、其余不动就得到同一物理量，却拆成了多个函数 |
| **该分开** | **67** | 物理输入不同、或本就是不同物理量/流水线不同阶段 |
| **证据不足** | **31** | §6.3 的判据在现有签名上**无法执行** |
| 无同族候选 | 136 | 唯一能力，不存在"该不该合"的问题 |
| 合计 | 249 | |

带 `method` 的合同：**9 份**（`kinetic` 6、`inference` 1、`neoclassical` 1、`geometry`/`sampling` 1）。
规则执行率 = 9/249 ≈ 3.6%，但它不是唯一的失败模式——**31 份"判不了"才是更严重的那一类**。

## 1 候选判据（可复核）

族候选不能靠名字像不像。本审计用三条机械判据生成候选，再逐条给判定：

**判据 A（机械配对）**：同域 + 输出名集合的 Jaccard ≥ 0.5 + 输入名集合的 Jaccard ≥ 0.5。
对本库 249 份合同给出 **49 对**候选（脚本见 §5）。

**判据 B（选择参数）**：签名里已出现 `method` / `model` / `family` / `selector` / `jcase` 的，逐一核对
它选的是不是"同一物理量的不同算法"。

**判据 C（逐份扫）**：对 `neutrals` 全部 33 份（0 份带 `method`）逐份看名字与签名，不靠聚类。

三选一的判据来自总纲 §6.3：

> 调用的人只改 `method`、别的参数一个都不动，拿到的是不是同一个物理量？
> 是 → 合族；不是 → 分开。

判为"该合族"必须满足：签名差异**只在算法/模型选择上**；判为"该分开"必须给出**物理输入不同**的证据；
两者都给不出时判"证据不足"——**不得按名字相似度猜**。

## 2 判定明细

### 2.1 现有 9 份带 `method` 的合同

| 域 | 签名 | 选择参数 | 判定 |
| --- | --- | --- | --- |
| kinetic | `evaluate_plasma_dispersion(z, *, method='scipy', order=None)` | `method ∈ {scipy, rational, weideman, jpole}` | **样式样板**：四种 Z 算法一个入口 |
| kinetic | `evaluate_dielectric_response(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, method='harmonic', harmonics=None)` | `method ∈ {harmonic, harmonic_weideman, ronnmark}` | **样式样板**；非法 method 会列合法值 |
| neoclassical | `compute_bootstrap_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star, *, method='redl')` | `redl` / `sauter` | 符合总纲 §6.2 的示范例 |
| kinetic | `evaluate_fluid_dispersion(kx, state, method='fDR')` | 字符串 | 符合 |
| kinetic | `evaluate_fluid_special(method, x, parameter=None)` | 位置参数 | 符合，但 method 做成位置参数，与其它函数的 `*` 风格不一致 |
| kinetic | `evaluate_spectral_dispersion(species=None, *, …, method=2, …, oldmethod=2, …)` | `method` **和** `oldmethod` | **两个选择参数并存**：`oldmethod` 是历史遗留的第二选择器，属实现细节泄漏到公开面 |
| kinetic | `solve_temporal_spectrum(M, A, *, vectors=False, oldmethod=2, …)` | `oldmethod` | 同上，只有 `oldmethod` |
| kinetic | `evaluate_dielectric_response` 的姊妹：`evaluate_dielectric_diagnostics(*, …, harmonics=15)` | 无 `method`，固定 harmonic | **该合族**，见 2.2 |
| inference | `optimize_anisotropic_parameters(*, …, method, …)` | 优化器名 | **不是物理模型族**：选的是数值优化器，属 L1 数值层，不是"同一物理量的不同模型" |
| geometry/sampling | `regular_grid(xx, yy, *fields, nx=200, ny=200, xi=None, yi=None, method='linear')` | 插值方法 | 同上：数值插值选择，对应 scipy 的 `kind=`，不归 §6 管 |

**归纳**：9 份里真正属于 §6 意义下"物理模型族"的只有 5 份（kinetic 4 + neoclassical 1）；
2 份是数值层选择（`method` 在这里是 scipy 的 `kind=` 语义）；2 份暴露了 `oldmethod` 这种实现遗留选择器。
所以"9/249"这个数字本身也要打折：**真正体现 §6 规则的样板是 5 份**。

### 2.2 该合族（6 组，15 份）

每一组都必须能指到签名，且签名差异只在算法选择上。

| # | 域 | 签名 | 为什么该合族 |
| --- | --- | --- | --- |
| 1 | kinetic | `evaluate_dielectric_diagnostics(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, harmonics=15)`<br>`evaluate_dielectric_response(*, B0, qs, ms, ns0, Ts0, omega, kz, kx, method='harmonic', harmonics=None)` | 9 个关键字参数逐一相同；输出同为 `K` / `D` / `determinant`。且 `dielectric_diagnostics.py` **直接 import 了** `dielectric_response` 的 `_CONVENTION`、`_harmonics` 并调用同一条 harmonic 路径。→ `diagnostics = response(method='harmonic', harmonics=15)`，诊断字段可以并进同一返回 |
| 2 | numerics | `ClampedCubicSpline(x_data, y_data, yp=(0,0))`<br>`FirstClampedCubicSpline(x_data, y_data, yp=0, m=0)`<br>`SecondClampedCubicSpline(x_data, y_data, m=1)`<br>`NaturalCubicSpline(x_data, y_data)` | 四份合同 `definition` **逐字相同**："Piecewise cubic Hermite interpolation with a boundary-specific linear slope system"，只在 `boundary` 字段里分别写"两端给一阶导""两端二阶导为零"。→ 对应 scipy 的 `CubicSpline(bc_type=...)`，同一族一个类 |
| 3 | geometry/sampling | `locs_to_vals(X, Y, Q, coord_list)`<br>`locs_to_vals1D(X, Y, Q, coord_list)`<br>`locs_to_vals_griddata(X, Y, Q, coord_list)` | 四个位置参数逐字相同，只差插值后端。→ `method='default'|'griddata'`（`1D` 分支是否保留取决于是否真是不同物理输入，见 §4 的保留意见） |
| 4 | kinetic | `evaluate_generalized_dispersion(z, selector=0, *, expression='exp(-v.^2)/sqrt(pi)', integration_mesh=None)`<br>`evaluate_generalized_hilbert(z, expression, *, integration_mesh, continuation=True)` | 同一 `relation`：`Z=∫f(v)/(v-z)dv`，同输出 `Z` / `Zp`，**同一个实现模块** `scirel.kinetic.generalized_dispersion`。只差分布函数 f 的选法：整数 `selector` vs AST `expression`——`selector` 本身就是算法选择参数 |
| 5 | neutrals | `evaluate_outer_convergence(previous_density_m3, current_density_m3, truncate)`<br>`evaluate_neutral_outer_seed_convergence(previous_density_m3, current_density_m3, truncate)` | 签名**逐字相同**，返回同为"相对变化比 + bool + 理由字符串"；唯一差别是判定阈值为 `truncate` vs `10*truncate`。按 §6.4，截断阶数属于"某方法专有的容差"，**不构成分开的理由** → 应为 `pass_='outer'|'seed'`。**维护者已裁决：保持分开，另开 scope 工单记录语义冲突（T-2026-1200）** |
| 6 | kinetic | `pole_coefficients(J=8)`<br>`get_z_pole_coefficients(*, j_order)` | 同一 `relation`："integer pole count J → residues and complex pole positions"；输出同为 `bzj` / `czj`，只在返回包装上有差别 |

### 2.3 该分开（67 份）

**分成两类标注，读者必须能分辨哪条是权威、哪条是审计者判断。**

#### (a) 总纲 §6.3 有**明文依据**的（28 份）

| 域 | 组 | 数量 | 总纲原文依据 |
| --- | --- | --- | --- |
| physics | `calculate_log_lambda_ee(T_e, n_e)` / `calculate_log_lambda_ei(T_e, n_e)` / `calculate_log_lambda_ii(T_e, n_e)` | 3 | §6.3 表格："电子–电子和电子–离子的库仑对数 → **分开**（是不同的碰撞对，不是同一个量的不同算法）" |
| io | `read_eqdsk(filename, *, strict=True)` / `read_geqdsk(filename, *, strict=True)` | 2 | §6.3 表格："读 EQDSK 和读 G-EQDSK → **分开**（读文件是数据格式问题，不是在选物理模型）" |
| collisions | 5 份弹性截面（`evaluate_atomic_hydrogen_elastic_cross_section(energy_ev, viscosity=False)`、`evaluate_hydrogen_h2_elastic_cross_section(energy_ev)`、`evaluate_hydrogen2_proton_elastic_cross_section(energy_ev)`、`evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy_ev, viscosity=False)`、`evaluate_hydrogen_proton_elastic_cross_section(energy_ev)`） | 5 | 同上"不同碰撞对"一条的推广：输入名 Jaccard = 1.00，但碰撞对不同 |
| collisions | 电荷交换截面 2、电荷交换速率 2、碰撞矩阵 2、omega 频率 2 | 8 | 同上 |
| collisions | `average_cross_section_over_maxwellian` 与各截面函数 | 2 | §6.3："动量转移截面和粘性截面 → 分开（两个不同物理量）"的同型：截面 vs 速率是不同物理量 |
| 其他 | `assemble_atomic_hydrogen_collision_matrices` 与 … | 8 | 同上 |

（`physics` 与 `io` 两组共 5 份是**逐字**引用；`collisions` 的 23 份是**按同一条依据推广**——
总纲只点了"电子–电子/电子–离子"这一对，推广到所有碰撞对是审计者的判断，不是原文列举。）

#### (b) 审计者按 §6.3 判据**推断**的（39 份）

| 域 | 组 | 数量 | 推断依据 |
| --- | --- | --- | --- |
| neutrals | `contract_atomic_hydrogen_alpha_frequencies` / `contract_molecular_hydrogen_alpha_frequencies`；`reduce_atomic_scattered_sources` / `reduce_molecular_scattered_sources` | 4 | 不同物种 |
| neutrals | `interpolate_scalar_across_mesh(fa, xa, xb, do_warn=0)` / `interp_distribution_across_mesh(fa, vr_a, vx_a, x_a, Tnorm_a, …, correct=1, …)` | 2 | 标量 vs 分布，物理输入不同 |
| neutrals | 其余 25 份：`assemble_*` / `build_*` / `reduce_terminal_*` / `normalize_*` / `propagate_*` / `sum_*` / `update_*` | 25 | 逐份看名字与签名和返回量：全部是**同一条中性粒子输运流水线的不同阶段**，输出分别是分布、频率、源、通量、守恒诊断等不同物理量；**没有一对是"同量异算法"** |
| geometry | `RChord(rpts, z0=0.0)` / `ZChord(zpts, r0=0.0)` | 2 | 变化的是几何方向这一物理输入 |
| geometry | `contour_points(contourset)` / `helper_contour_points(contourset)` | 2 | 签名相同，但**文档化的产出类型不同**（`FieldLine` vs `HelperFieldLine`），两者构造参数与 `get_kappa_n` 返回形状都不同；命名债另开 T-2026-1201 |
| source | `exponential_profile(ρ_norm, vpr, drho_norm, *, decay_start, width, total)` / `gaussian_profile(…, *, center, width, total)` | 2 | 形状参数集结构性不同（`center` 对指数分布无意义），属 §6.4"硬塞变成大杂烩"的风险 |
| fvm | `make_convection_terms(v_face, d_face, var, dirichlet_mode='ghost', neumann_mode='ghost')` / `make_diffusion_terms(d_face, var)` | 2 | 两个不同的离散算子 |
| neoclassical | `calculate_bootstrap_current` / `compute_bootstrap_coefficients(…, method='redl')` | 2 | 不同物理量（电流 vs 系数）；后者是 `method=` 正例 |

### 2.4 证据不足（31 份）

| 域 | 合同 | 为什么判不了 |
| --- | --- | --- |
| equilibrium / mirror | **6 份签名是 `(inputs=None, **kwargs)`**：`solve_free_boundary_anisotropic_picard`、`solve_reduced_hall_anisotropic_picard`、`solve_kinetic_mirror_hall_equilibrium`、`solve_frank_egedal_pressure_closure`、`solve_grid_mirror_kinetic_closure`、`solve_mirror_quasineutral_closure` | §6.3 的判据要读参数表，而参数表不透明。**这是本审计最重要的发现**：族规则在它最需要的地方（多个平衡/闭合求解器）不可审计 |
| kinetic | fluid 簇 15 份：`assemble_fluid_dispersion_matrix`、`assemble_fluid_em`、`derive_fluid_case`、`evaluate_fluid_dispersion`、`evaluate_fluid_special`、`fluid_deck`、`fluid_equilibrium_relative_rates`、`fluid_equilibrium_si`、`fluid_frequency_pencil`、`fluid_solve_state`、`scan_fluid_corrected`、`scan_fluid_wavevectors`、`solve_fluid_bonk`、`solve_fluid_em`、`solve_fluid_wavevector_eigenproblem` | 需要逐个读物理才能分族。**最强候选**：`solve_fluid_bonk(jcase=1, omegas=None)` 与 `solve_fluid_em(jcase=2, j_order=8, max_harmonic=6, omegas=None)` 共用选择参数 `jcase`；`fluid_frequency_pencil → assemble_fluid_dispersion_matrix → fluid_solve_state` 更像流水线阶段而非同族 |
| kinetic | `evaluate_plasma_dispersion(z, *, method='scipy', order=None)` / `evaluate_cauchy_transform(z, density, *, bounds=None, …)` / `jpole_evaluate(bzj, czj, z)` | 输出都含 Z，但输入面不同（Maxwellian 捷径 / 表格密度 / 预计算系数）。**`evaluate_plasma_dispersion` 是族规则样板，不应被合并掉** |
| kinetic | `jpole_coefficients(J=12, I=16, *, precision=80)` / `pole_table(model='es1d', J=8, *, opt=None)` / `get_gamma_lpole_coefficients(*, max_harmonic)` | 前者返回高层 Result，第二个只返回 `state/receipt`，第三个是 **Gamma（Bessel）展开**系数——不是同一个展开对象 |
| diagnostics | `compute_firehose_mirror_margins(p_parallel, p_perp, magnetic_field, …)` / `compute_pointwise_firehose_margin(p_parallel, p_perp, magnetic_field, mu0=…)` | 同量但一个含镜像稳定性、一个点态；是否同族取决于物理口径 |
| geometry | `ThetaChord(tpts, r0=1.0)` / `SphericalRChord(rpts, theta0=0.0)` | 合同定义分别为 `R=r0 sinθ, Z=r0 cosθ` 与 `R=r sinθ, Z=r cosθ`——像是同一映射的标量/数组半径两版，但命名意图不同 |
| fieldline | `FieldLine(psi, verts, **kwargs)` / `HelperFieldLine(psi, verts)` | 文档化了构造参数与 `get_kappa_n` 返回形状的差异（同一物理量、不同接口）。属"接口不一致"而非"不同物理量"，交 T-2026-1201 一并裁决 |

### 2.5 特别检查：`neutrals` 33 份（0 份带 `method`）

逐份看名字与签名的结果：**33 份里只有 2 份构成族候选，其余 31 份不是同族。**

| 判定 | 份数 | 合同 |
| --- | --- | --- |
| 该合族 | 2 | `evaluate_outer_convergence` / `evaluate_neutral_outer_seed_convergence`（签名逐字相同，只差 10× 阈值） |
| 该分开 | 6 | 原子/分子两组（4）+ 标量/分布插值（2） |
| 该分开（流水线阶段） | 25 | 见 2.3(b)：`assemble_neutral_boltzmann_rhs`、`build_shifted_maxwellian_seed`、`compensate_velocity_slice`、`make_cylindrical_velocity_quadrature`、`reduce_axisymmetric_neutral_moments`、`reduce_terminal_molecular_*`（5 份）、`update_neutral_generation_accumulation` 等 |

**判断**：`neutrals` 的 0/33 不是"规则没执行"，而是**这个域本来就没有模型族**——
它是一个求解器的流水线被拆成了一份合同一个阶段。
`neutrals` 真正的问题不是缺 `method=`，而是**它的 33 份合同缺少一个"子主题"层**：
`assemble_*`（装配）、`build_*`（构造分布）、`reduce_*`（归约出物理量）、`interpolate/interp_*`（跨网格）
四组各自内部没有族关系，但组之间也没有任何结构告诉检索者"这是四个阶段"。
这与 [参照项目](reference-projects.md) §1.5 的索引结构问题是同一件事。

## 3 判据本身的一个缺口（持久）

§6.3 说"只改 `method`、别的参数一个都不动"。这句话在三种情况下给不出答案：

1. **签名不可读**（`**kwargs`，6 份）→ 判不了；
2. **选择参数不是 `method`**（`selector`、`jcase`、`oldmethod`、`model`）→ 判据的字面意思会漏掉它们，
   而它们恰恰在选择算法；
3. **返回值形状变了**（`FieldLine.get_kappa_n` 返回 `(npts,2)`，`HelperFieldLine` 返回两个 `(npts,)`）
   → "拿到的是同一个物理量"成立，但"拿到的东西能互换"不成立。

建议补一条判据回总纲（持久）：

> 族判据除了"同一物理量"，还要加一句**返回值必须可直接互换**：
> 换一个选择参数之后，调用方不需要改任何后续代码。
> 否则那不是"同一个量的不同算法"，是"同一个量的两个不同接口"——后者要么统一接口，要么分开并说明。

这条一旦成立，`FieldLine` / `HelperFieldLine` 和 `evaluate_dielectric_diagnostics` /
`evaluate_dielectric_response` 都会被同一条规则覆盖，不需要逐案讨论。

## 4 保留意见（审计者未判的部分）

以下不是"判定"，是"没有判"：

- **`locs_to_vals` / `locs_to_vals1D` 的 `1D` 分支**：三个函数签名相同，但 `1D` 是否服务不同的物理输入
  （一维路径 vs 二维场）需要读实现，本次未读。若它真是不同维度，则该组从"该合族 3"缩为"该合族 2 + 分开 1"。
- **fluid 簇 15 份**：只在 §2.4 里给出最强候选，未逐份判。这一簇是 `kinetic` 62 份里最大的候选池，
  值得单独一轮审计。
- **`fieldline` / `sampling` 两个域的 21 份合同**：它们属于 `geometry` 下的模块（ID 域段与模块域不一致，C2 在还债），
  本审计按 ID 域段分类。若按模块域重算，这些判定会并入 `geometry`。

## 5 复算方法

```python
import json, glob, collections, itertools

rows = []
for path in sorted(glob.glob('catalog/examples/*.json')):
    doc = json.load(open(path))
    api = doc['public_api']['python']
    rows.append(dict(
        dom=doc['asset_id'].split('.')[1],
        sym=api['symbol'], sig=api['signature'],
        ins={i['name'] for i in doc.get('inputs', [])},
        outs={o.get('name') for o in doc.get('outputs', [])},
    ))

print('带 method 的合同:', sum(1 for r in rows if 'method' in r['sig']))

def jac(a, b):
    return len(a & b) / len(a | b) if (a or b) else 1.0

pairs = 0
for dom in {r['dom'] for r in rows}:
    for a, b in itertools.combinations([r for r in rows if r['dom'] == dom], 2):
        if not a['ins'] or not b['ins']:
            continue
        if jac(a['outs'], b['outs']) >= 0.5 and jac(a['ins'], b['ins']) >= 0.5:
            pairs += 1
            print(f"[{dom}] {a['sym']} <> {b['sym']}")
print('判据 A 候选对:', pairs)   # 49
```

## 6 处置原则（持久）

**本审计不合并、不改代码、不改合同。** 理由两条，都来自仓库自己的规则：

1. **改族就是改公开签名**，按 §6.5 可能改变默认方法，属"改物理"，必须附新旧对比并走分级评审
   （[`AGENTS.md`](../../AGENTS.md) 第 2 条）。
2. **候选不宜合族或不宜删除的，必须给出证据，不能强并强删。** 判不了的一律留在原地，
   写明卡点（本文件 §2.4、§4），不是按名字相似度并掉。

后续动作只有三项，且都不是本文件做的：

| 动作 | 归属 |
| --- | --- |
| 补"公开函数不得用 `**kwargs` 吞掉物理参数"的检查器，再逐项收口 14 份 | C2 后续批次（见 [持久规范与状态](durable-vs-status.md) §3.1） |
| `outer_convergence` 语义冲突裁决 | 工单 T-2026-1200 |
| `helper_*` / `Helper*` 命名债 | 工单 T-2026-1201 |
| 把"族判据 + 返回值可互换"写进总纲与 api-spec | 维护者 |
