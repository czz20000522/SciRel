# 平面波矢投影开发整合记录（本仓批次）

状态：**隔离开发批次，非可信版、非公开发行**。本记录对照保存的 PDRF/PDRK L1 内容；
两项目尚未取得绑定 source、skill、bundle、严格 `full_freeze` 与独立审查的完整
whole-source D1 交接回执，因此本批次不得记为已核验冻结 L1 的正式接纳，
PDRF/PDRK 当前也**不是合格的 whole-source D1 来源**。

## 科学关系与来源更正

科学比较与拟议处置见[波矢专家候选](../../review_candidates/2026-09-24-pdr-wavevector/review.md)
（PDRF `plasma_k_projection` package `sha256:4bbb3dcd7ced270e1f41405cae7b9c727a4e253c994dfda6021dea2781fd691a`，
PDRK `wavevector_projection` package `sha256:71b1b7790849f2839b9792d0a401f5ea3fb5ed621097c873f7e037b9a39dfc70`；
两者为有条件重叠，不是完整算子重复）。本批次新增
`scirel.geometry.planar-wavevector-projection`，唯一精确科学合同为
[exact document](../../catalog/examples/scirel.geometry.planar-wavevector-projection.json)，
实现与直接测试分别在 `src/scirel/geometry/planar_wavevector.py` 与
`tests/operator_contracts/test_planar_wavevector.py`。不接任何来源 TaskGraph；
PDRF 反向图 `fluid_dispersion_branch_sweep`、PDRK 反向图
`kinetic_dispersion_scan`/`pdrk_main_pipeline` 未重绑。

相对 2026-09-25 intake 提交（SciRel-intake-20260925 @ 36d50f0）的**来源更正**一项：
intake 实现的 `_finite_real_vector` 只在 `np.asarray` 之后检查 `dtype.kind`，
而 NumPy 把混合容器 `[1, True]` 强制转换为整型数组、把 `[np.bool_(True), 1.0]`
转换为 float64，因此合同声明的"拒绝布尔伪数"被静默违反。本批次先写失败回归
（先确认缺实现时收集失败；再放 intake 原样实现，确认 3 个混合布尔参数化用例
与显式回归测试共 4 项失败、其余 13 项通过），随后在转换**之前**对输入对象做
布尔伪数扫描修复。纯布尔容器与布尔标量原本就被 dtype-kind 检查拒绝，行为不变。

## 与 intake 提交的整合边界

只逐项整合批次相关文件：实现、领域导出、直接合同测试（含混合布尔回归）、
exact document 与 15/63 catalog/selector 测试计数。intake 提交中的无关改动
（docs 批量措辞、`scripts/check.ps1`、`tests/test_release_environment.py`）和
依赖保存来源源码的 `test_planar_wavevector_l1.py` 均**未**引入：后者在
intake 当前 HEAD（647d5db）经 `SCIREL_HISTORICAL_PDRF_ROOT` /
`SCIREL_HISTORICAL_PDRK_ROOT` 指向保存的 PDRF/PDRK 源码根目录才能执行，
违反源码无关测试边界。intake
记录的 PDRF/PDRK 数值对照（极坐标正模长相合、直角分量相合、零模长角度/负模长/
`par` 状态/大分量溢出/负 `cwp` 方向不同）作为一次性 provisional 证据保留在本记录，
不在本仓重跑，也不扩大为严格 D1 冻结证据。

## 验证（实际执行）

- `PYTHONPATH=src python -m pytest tests/operator_contracts/test_planar_wavevector.py`：
  修复后 **17 passed**（含 3 个混合布尔参数化用例与显式回归测试）。
- `PYTHONPATH=src python scripts/validate_asset_documents.py catalog/examples
  --check-runtime --execute-examples`：`asset_count: 15`，runtime 与示例校验通过，
  `implementation_version` 与本基线 `pyproject.toml` 的 `0.1.0.dev5` 一致
  （未复用 r81 dev58 原字节）。
- 相关 catalog/selector/surface 测试
  （test_planar_wavevector、test_asset_documentation、test_affected_test_selection、
  test_thin_mcp_adapter、test_public_surface）：**84 passed**。
- `pwsh ./scripts/check.ps1 -Mode affected`（按工作区实际变更）：选择器经 exact
  document 可归属全部变更路径，**未 fail closed 到全套**；选择 6 个测试文件，
  **87 passed**。选择报告为工程证据，不是新的治理事实。

## 待决与风险

- 专家需决定科学身份、SI 输入约定、`hypot` 与来源平方求和在大分量的数值差异，
  以及 PDRF 归一化输入卡到 `1/m` 的映射。
- PDRF/PDRK 的 whole-source D1 冻结交接仍缺；未来若重绑来源 TaskGraph，
  须另证端口、状态与图测试。
- 混合布尔修复只扫描容器顶层元素；已是 NumPy 数组的输入（布尔信息在调用方
  转换时已丢失）不在本合同拒绝范围内，exact document 的 constraints 已按
  "boolean pseudo-numbers … NumPy would coerce" 表述。
- 开发 catalog 为 `partial: 15/63`；构建、测试与 catalog 均不产生专家批准或公开发布。
