# 首次待审资产的来源覆盖

本索引用于专家定位当前 68 个开发资产的来源证据，不是来源项目完整拆解证明、科学批准或许可证结论。基准为 SciRel `418d984f386f24074e80870f4243713ce2fcc4c5` 的 68 份 `scirel.asset-document.v1`；当时合格 L1 交付根为空。此前保存的来源候选可支持有界开发比较，但不能按旧 `full_freeze` 标签重新认定为合格输入。

## 旧迁移账本：52 项

[`provenance/admitted-assets.json`](../../provenance/admitted-assets.json) 的 SHA-256 为 `549f6e55eba497f1b8b6727e35cf5fe6091b3881a053ac9848bd1b6edd20e1f1`。按 `public_callable` 与当前 exact documents 的 `public_api.python.module + symbol` 对照，账本中 52 个互异 callable 全部一一命中当前文档：41 个 Operator、11 个 TaskGraph，没有未解析项。账本逐项给出保存的实现路径、文件摘要、旧版本树及依赖绑定；现行身份与科学合同以对应 exact document 为准，不能从账本中的旧 `admission`、`decision_ref` 或当时的 `review_rationale` 推导当前专家认可。当前 SciRel 实现也不宣称与保存实现字节相同。

## 账本外：16 项

以下资产不在上述 52 项迁移账本内。每组的确切科学关系、有限测试、来源限制和已知反例仍以各自的 exact document 及已有整合记录为准；同组不表示可合并为一个资产。

| 保存来源或观察范围 | 当前 SciRel 资产 ID | 证据边界 |
| --- | --- | --- |
| CQL3D 保存候选 | `scirel.collisions.normalized-momentum`, `scirel.collisions.thermal-electron-momentum`, `scirel.collisions.relativistic-maxwellian-bessel-closure` | 文档保留 dispatcher 拆分、数值修正及适用域差异；不是当前合格 L1。 |
| FIDASIM 保存候选 | `scirel.fusion.dd-neutron-lab-energy` | 文档明确本次规范化没有独立重读 Fortran，源码行号来自保存候选。 |
| ASCOT5 / TokaGrad 保存候选 | `scirel.fusion.bosch-hale-reactivity` | 两项目是有界重叠而非系数完全相同；严格 D1 资格已撤回，详见 [整合比较](intake-2026-09-25-bosch-hale-reactivity.md)。 |
| PDRF / PDRK 保存候选 | `scirel.geometry.planar-wavevector-projection` | 条件性重叠，不吸收 PDRK 的扫描状态；两项目旧严格 D1 资格已撤回，详见 [整合比较](intake-2026-09-25-planar-wavevector.md)。 |
| PDRK / fluidBW 保存候选 | `scirel.kinetic.plasma-dispersion-function` | 解析关系共享，数值近似阶数不同；两项目当前均非合格 L1，详见 [整合比较](intake-2026-09-25-plasma-dispersion.md)。 |
| fluidBW 保存候选 | `scirel.kinetic.species-equilibrium-scales`, `scirel.kinetic.bessel-gamma`, `scirel.kinetic.kinetic-dispersion-sum` | 只覆盖已声明的尺度、函数与有限谐波点值；旧 D1 资格已撤回，详见 [整合比较](intake-2026-09-25-fluidbw-kinetic.md)。 |
| 保存的吸收、冷等离子体及全波/几何观察记录；当前 exact documents 未统一声明同一个来源项目 | `scirel.diagnostics.species-absorption-fraction`, `scirel.dielectric.cold-plasma-tensor`, `scirel.geometry.axisymmetric-equilibrium-grid-mapping`, `scirel.geometry.axisymmetric-equilibrium-grid-support`, `scirel.geometry.complex-rectilinear-interpolation`, `scirel.geometry.material-support-classification` | 分别查看六份文档中的来源描述、拆分/合并判断与失败域；不要凭领域相邻关系补造单一项目溯源。 |

结构核对：当前文档共 68 个互异 callable，其中账本内 52 项、账本外 16 项；账本外为 15 个 Operator 和 1 个 TaskGraph。68 份文档的 `license_status` 均为 `pending-human-decision`。这些数量只描述当前开发库的可追索范围，不证明原项目物理功能覆盖，也不授权可信晋级或公开发行。新的合格 L1 到达后，必须重新对照确切来源快照和现有 68 项，而非继承此处的历史资格判断。
