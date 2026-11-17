# C4 收口轮 · 分级缺口

判定口径沿用上一轮：**只拿分发包的消费者**能否按合同正确使用。每条缺口写清
"卡在哪一句/哪一个运行时事实上"，`package_sufficient=false` 的任务一律不并进 pass；
`not-run` / `not-observed` 单列且永不计为通过。

本轮共 73 条任务、272 条判据（225 pass / 40 fail / 7 not-run），另有 7 条审计判据
（A1–A3、B1–B2、C1–C2：5 pass、2 fail，其中 C2 汇总了 3 条 `not-observed` 的子句）。

---

## 一、本轮缺口

### B1. "21 份单输出合同声明按位置返回"这个数字在包里对不上（阻塞记账，不影响使用）

任务书说 21 份单输出合同被声明为按位置返回。包内实际把该句写进
`outputs[0].description` 的是 **13 份**：

- `8f52863b` 批 1 的 11 份：`collisions.atomic-hydrogen-charge-exchange-rate-coefficient`、
  `collisions.atomic-hydrogen-elastic-cross-section`、
  `collisions.molecular-hydrogen-charge-exchange-rate-coefficient`、
  `dielectric.cold-plasma-tensor`、`electromagnetism.loop-flux-matrix`、
  `geometry.arclength-derivative`、`neutrals.cross-mesh-scalar-interpolation`、
  `neutrals.neutral-generation-propagation`、`numerics.modal-projection`、
  `source.exponential`、`source.gaussian`
- 批 2 的 2 份：`geometry.meridional-polar-forward`、`geometry.meridional-polar-inverse`
- 另有 `numerics.faddeeva` 用既有写法 "returned directly as an array"（本轮计入"已声明"）

13 + 1 = **14 份**已声明；`21` 是那次逐份裁决的**范围**（其中 `physics.thermal-energy`
改成 `Result`、`field.circular-filament-green` 判无需改动、其余 5 份在批 1 里）。
按 21 去找会少 8 份。这不是库的缺陷，是**回执口径与包不一致**——记在这里，免得下一轮
又按 21 对账。

**能不能只用包确认这一点**：能，`contract-audit.json → channels.declared_channel_counts`
给出 `{positional: 14, result-field: 5, undeclared: 119}`，`declared_positional: 14`
且 `runtime_consistent: 14`。

### B2. 三份单输出合同"返回 mapping，但合同没把键列全"（阻塞：读不到值）

138 份单输出合同里，119 份**没有**任何返回通道声明。其中 84 份直接返回裸值（常识解读成立），
8 份声明名正好是键，19 份键名在 `constraints`/`dtype`/`shape` 里逐个列全，2 份的键是调用方给的
轮廓层级（合同给了取键规则）。剩下 **3 份**是硬缺口：

| 合同 | 运行时事实 | 合同卡在哪 |
| --- | --- | --- |
| `kinetic.fluid-case-state` | 返回 31 个键（`B0,S,T00,Ts0,Ts_unit,c,c2,epsilon0,jcase,kB,kn,kz,me,mp,ms,mu0,n00,ns0,ns_unit,qe,qs,rhocn,rhocs,vts,wcn,wcs,wcs2,wn,wp2,wps,wps2`） | `description` 只有 "Complete species scales and source material metadata; EM sets kz=0.1kn."，31 个键里只出现 `kz` |
| `kinetic.multifluid-frequency-solve` | 返回 12 个键 | `constraints`+`shape` 只覆盖 `M,A,w1,w2,X1,X2`；`componentwise_backward_errors`、`refinement`、`state_scales`、`zero_structure`、`wcs`、`wps` 没在合同任何字段出现 |
| `io.eqdsk-class` | 构造出的 `EQDSK()` 是**空** mapping（`keys: []`） | 本合同的散文没列键集；键集只在**另一份**合同 `io.read-geqdsk` 的 description 里 |

**卡在哪一句**：这三份都把"返回的是什么"写成了散文或别处，而 `outputs[0].name` 不是可用键。
缺的是"结构的键集写在结构化字段里"这一条约定，不是某个数值。

复现（三份里的第一份）：

```sh
SCIREL_PACKAGE_ROOT=$PWD/.runtime/c4close/scirel-delivery-close \
  .runtime/c4close/venv-consumer/bin/python -I -c "
import sys; sys.path.insert(0,'examples/c4-usage-acceptance/closeout')
import harness as H
a='scirel.kinetic.fluid-case-state'
r=H.Ctx({'id':'x'}).call(a, H.Ctx({'id':'x'}).named(a))
print(len(r['returned_fields']), r['returned_fields']); print(H.contract(a)['outputs'][0])"
```

### B3. 119 份单输出合同完全没写返回通道（体验级）

能拿到值，但"要不要取键"只能靠试。其中 8 份的声明名正好是键、19 份键名散在
`constraints`/`dtype`/`shape` 里——都可以读到，但都需要逐份读散文。

这一条**不**判成阻塞：84/119 的运行时行为与"单输出按位置"一致，试一次就对。
判成体验级缺口，理由是同一个包对同一件事（"这个值从哪拿"）有四种写法：
明确的句子（14 份）、明确的 `Field of the returned … Result mapping`（5 份）、
只写在 `constraints` 里（19 份）、什么都没写（119 份）。

### B4. 五份新证据子句里，三条不能只靠包验证（影响可信度）

17 条可判定子句：14 pass、0 与公共行为矛盾、3 `not-observed`：

| 合同 | 子句 | 为什么包内验不了 |
| --- | --- | --- |
| `field.poloidal-field-from-flux` | "independent 80/120-digit Biot-Savart integration gives positive direct BR" | 包内没有该积分可调用体，子句也没印出积分式；无法复算 |
| `field.poloidal-field-from-flux` | "closes to 6.0 eps of the term scale" | 没印 stencil 与 "term scale" 的定义。我用二阶单边差分得到 1.7e-15 ≈ **7.6 eps**（差 1.27 倍）——既不确认也不否认 |
| `numerics.truncated-svd-inverse` | "The hand-SVD construction covers permutation-times-diagonal spectra only" | 讲的是维护者测试怎么构造的，包里没有该产物 |

其余 14 条都验过且一致，包括：二次通量闭式解 `B_R=-R(e+2bZ)`、`B_Z=2(a+eZ+bZ²)`；
单幂族 `R^aZ^b` 与有理数闭式在 2.8 eps 内；散度恒等式在返回数组上收在 1.7e-15；
常数参考量不改变 `B_R/B_Z`；3-4-5 折线精确、四分一转角逐位不变、√2 长度在 4 eps 内；
clamped 样条在端点斜率一致时精确复现三次多项式、`yp=(0,0)` 时**不**精确；natural 样条对线性函数精确、对三次多项式不精确；SVD cutoff 恰好命中时保留、下一个丢弃、宽矩阵返回转置形状。

### B5. `round2/README.md` 的覆盖表与它自己的 `round2/results.json` 有 15 行不一致（流程）

按同一套 `coverage.py` 口径逐格比对 22 行：

- 15 行的 `criteria(pass/fail)` 不一致，例如 `source` README 写 `9/3`、results.json 是 `12/0`；
  `configurations` README 写 `5/3`、results.json 是 `8/0`。
- `cross` 一行连 `sufficient` 都不一致：README 写 **0**，`results.json` 是 **1**。

解释只有一个：那张表是**装置修补之前**（`6.9.1` 那次 `_val` 修复之前）抄下来的，
之后没随最终数字重算。本轮的表由 `coverage.py` 现算并原样贴出，避免同类漂移。
这条不改动 round2 的任何产物——那是历史回执，只在此标注它**不能作为逐格对账依据**。

### B6. `round2` 没有把 `thermal-energy` 的数值存下来，历史基线因此缺失（流程）

`round2/tasks/physics-coulomb-logarithms.json` 第 3 次调用记的是
`returned_type: "tuple"`、`returned_fields: null`，`calls.jsonl` 同样不存返回值。
所以"改成 `Result` 后数值没变"**不能引 round2 作证**。

本轮的替代做法：把 oracle 写在消费者侧——按合同 `identity.definition` 的
`1.5*sum(p*vpr*drho_norm)` 用 `fractions.Fraction` 从合同 example 的字面参数精确复算，
得 `7.8 / 11.7 / 19.5`，与按名读到的值相对偏差 **0.0**；另加两条 example 无关的关系
（`p_tot=p_el+p_ion` 时 `W_tot=W_el+W_ion`、`vpr` 加倍则三通道加倍），偏差均 **0.0**。

### B7. 本轮自己判据的两处缺陷（已修，记录以防重犯）

1. **散度恒等式用了一阶单边差分**：`np.gradient` 默认 `edge_order=1`，在边界对二次函数
   不是精确的，第一次跑出 `max_abs_divergence_over_term_scale = 0.506`——几乎就是 0.5，
   典型的"判据自己坏了"的形状。改成 `edge_order=2` 后为 `1.7e-15`。
   **若当时直接报"库的散度恒等式不成立"，就是一次误判。**
2. **通道审计只扫 `description`**：第一版把 7 份判成"读不到值"，其中 5 份的键名其实写在
   `constraints`/`shape` 里（例：`thermal-speed-scale` 的 constraints 写着
   "Carries exactly one field thermal_speed_m_s"）。改成扫 `description`/`constraints`/
   `dtype`/`shape` 四个字段并记录命中位置后，硬缺口从 7 降到 **3**（见 B2）。
   两处都写进了 `selfcheck.py` 的敏感度检查：`exact_energy` 去掉 3/2 必须变、
   权重加倍必须变；`channel_of` 三种写法必须各自落位。

### B8. 7 条 `not-run` 判据（沿用，未改善，不并进 pass）

| 任务 | 判据 | 为什么没评估 |
| --- | --- | --- |
| `cross-kinetic-to-diagnostics` | `cardinality`、`zeroresidual` | 观测入口只接受 `['flux_loops','thomson.density','electron_temperature','p_parallel','p_perp']`，传 `roots` 抛 `ValueError: unknown observation kinds`，没有声明的通道能承载根 |
| `dielectric-cold-tensor` | `resonance` | 精确回旋共振要求一个 example 未声明的频率 |
| `equilibrium-isotropic-picard` | `residualmeaning` | 步前后通量差的范数没有与步记录一起返回，残差无法用存下的数组重算 |
| `kinetic-fluid-two-path` | `budget` | 两条发布入口返回的载荷没有共同的命名字段承载 determinant |
| `kinetic-multifluid-frequency` | `budget` | 两条入口的记录不共享同一量的命名字段 |
| `kinetic-rational-pole` | `declared_counts` | 合同声明 46 个输出、运行时只有 9 个字段（round2 的 B2 仍在） |

### B9. 25 条任务 `package_sufficient=false`（与 round2 逐条相同）

按 kind：nominal 25/43 通过、failure 21/23、inapplicable 1/1、cross **1/6**。

- **failure 组只有 2 条不通过**，都是"库抛的不是合同声明的那个异常"：
  `fieldline-rejects-duplicate-vertices`（判据 `raise` fail）、
  `io-rejects-bad-and-missing-input`（判据 `malformed`、`missing` 两条 fail）。
  其余 21 条 failure 任务的异常判据全部 pass。
- **cross 组只有 `cross-field-to-equilibrium` 一条能做完**（按网格 reshape 后 Picard 步接受，
  有限差分对照偏差 0.0）。`cross-kinetic-to-diagnostics` 的判据没有 fail，但两条
  `not-run` 使它在最严格口径下也不成立；其余 4 条的 fail 判据分别是
  `cross-collisions-to-neutrals`（`fields_frequency`、`handoff`）、
  `cross-geometry-to-equilibrium`（`fields_state`、`sameshape`、`clamped_count`）、
  `cross-mirror-to-diagnostics`（`formula`、`no_verdict`）、
  `cross-source-to-neutrals`（`linearity`、`budget`）。
- **nominal 组 18 条不通过**，断点分三类：合同没声明可用的量传递路径（cross/两入口）；
  合同声明的字段运行时没有（`kinetic-rational-pole`）；判据需要的输入不在 example 里
  （`dielectric-cold-tensor` 的回旋共振频率）。

---

## 二、与 round2 的对比

| 项 | round2 | 本轮 | 判据 |
| --- | --- | --- | --- |
| 包源 revision | `4b5b4aaa` | `d429359d` | — |
| wheel sha256 | `4fc9757a…` | `f1501a3e…` | 重打包，非同一 wheel |
| 任务 executed | 73/73 | 73/73 | — |
| `package_sufficient` | 48 | 48 | 逐条相同 |
| 判据 | 224/41/7 | **225/40/7** | 仅 1 条变化 |
| 判据变化 | — | `physics-coulomb-logarithms.fields` fail→pass | 因为 `thermal-energy` 现在返回 `Result`，字段名与声明的三个输出一致 |
| 反向变差（pass→fail） | — | **0** | `closeout/checks/` 与 `harness.py` 与 round2 逐字节相同，装置唯一 |
| 数值变化 | — | **0** | 73 条更任务的 answer 逐值比对，只有 2 处对象 repr/临时路径差异，已单列 |
| B1（21 份声明命名输出返裸值） | 阻塞 | **单输出部分关闭**：14 份已声明且运行时一致；多输出部分转为 B3 | 见上 |
| B2（`rational-solve-matrix` 46 声明 vs 9 字段） | 阻塞 | **未变**（`kinetic-rational-pole::declared_counts` 仍 `not-run`） | 判据同 round2 |
| B3–B8（分散在 kinetic/collisions/cross 的 8 条） | — | **未变** | 同上：判据与装置都没变，唯一变化的判据在 physics |

---

## 三、仍未关闭（承接 round2）

1. **B2 类**：`kinetic.rational-solve-matrix` 声明 46 个输出、只返回 9 个字段。消费者无法
   按合同取到另外 37 个；本轮仍是 `not-run`，不是 pass。
2. **cross 5/6 断点**：两条合同之间只有裸数组的交界，没有声明的量传递路径。
3. **2 条任务、3 条判据的异常类型不一致**：`fieldline-rejects-duplicate-vertices`（`raise`）
   与 `io-rejects-bad-and-missing-input`（`malformed`、`missing`）——库抛的不是合同声明的那个异常。
   round2 README 里写的"4 条不一致"与它自己的 `results.json` 不符（failure 组同样只有这 2 条不通过），
   口径与 B5 同一类问题。
4. **`io` 域 2/2 任务 `package_sufficient=false`**：写读往返能跑，但"合同声明的失败行为"
   与实测不符（`io-rejects-bad-and-missing-input`）。
5. **单输出通道的三份硬缺口**（本轮 B2）与 119 份无声明（B3）。
6. **3 条不可包验的证据子句**（本轮 B4）。
7. **族级覆盖无法核对**：`family` 字段只有 3 份合同有。

## 四、本轮自身的妥协

- 包与 venv 不进仓库（wheel 929589 B、包约 6.8 MB），回执只写 sha256 与复跑命令；重打一遍可逐字节比对。
- `audits.py` 的 oracle（精确有理数热量、闭式解、cutoff 判定）都由消费者写，不看 `src/`；
  代价是这些 oracle 只能覆盖合同已经写明的关系，合同没写的形式（如 v7 的 Biot–Savart 对比）无法自造。
- 119 份无声明通道的合同，只对每份做了**一次**默认 example 调用；用别的输入时键集是否不同
  （例如 `contour-points` 的键就是输入层级）没有逐份穷举。
- `harness.py::_single_output_channel` 有一处松判据：当 `dtype` 是类名时，
  `returned not in ("NoneType","")` 即算相容。本轮 73 条任务里走这条单输出通道的判据共 **25 条**，
  走这个松分支的是 **0 条**（`tasks/*.json` 里 `detail.checks` 含 `object_instance` 的为 0），
  所以本轮结果不依赖它；但它仍是下一轮该收紧的地方。

## 五、这一节不证明什么

- 不证明物理正确性（归 C1）。B4 只判"子句与公共行为是否一致"，不判证据是否成立。
- 不证明全库覆盖（73 条是代表任务）。
- `not-observed` / `not-run` 一律不计为通过；上述 3 份硬缺口、7 条 not-run、3 条不可验子句，
  都是缺口本身，不是"通过但有注释"。
