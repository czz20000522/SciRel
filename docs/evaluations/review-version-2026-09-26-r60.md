# SciRel KN1DPy neutral-moment diagnostics family r60

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r59(`39416f569cd8f2a36db2b29f0b3e9c1d590b52ae`,快照 `build/verification/review-2026-09-25-r59-jh-radiation`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:十一项新 operator(中性矩诊断族)

`scirel.kinetic` 新增十一个 operator,覆盖保存 KN1DPy 源的中性矩归约与输运频率组装层:

1. `scirel.kinetic.thermal-speed-scale`(`compute_thermal_speed_m_s`)
2. `scirel.kinetic.generation-density-reduction`(`reduce_generation_density`)
3. `scirel.kinetic.axisymmetric-neutral-moments`(`reduce_axisymmetric_neutral_moments`)
4. `scirel.kinetic.elastic-frequency-channels`(`sum_elastic_frequency_channels`)
5. `scirel.kinetic.incoming-boundary-flux-normalization`(`normalize_incoming_neutral_boundary`)
6. `scirel.kinetic.spatial-source-shape-normalization`(`normalize_spatial_source_shape`)
7. `scirel.kinetic.neutral-total-collision-frequency`(`assemble_neutral_total_collision_frequency`)
8. `scirel.kinetic.atomic-scattered-sources-reduction`(`reduce_atomic_scattered_sources`)
9. `scirel.kinetic.molecular-scattered-sources-reduction`(`reduce_molecular_scattered_sources`)
10. `scirel.kinetic.elastic-regeneration-aggregation`(`aggregate_elastic_regeneration_source`)
11. `scirel.kinetic.simple-charge-exchange-source`(`assemble_simple_charge_exchange_source`)

全部逐位复现保存 formal 实现;无修复。四项声明的 fail-closed 收窄见下。

## 预审收窄(三轮只读预审,全部 fail-closed,保存臂行为留证)

1. NaN 速度轴:保存臂传播 NaN 到流速/温度;本实现 fail-closed。
2. 通道求和溢出:保存臂对 3×1e308 返回 inf;本实现 fail-closed。
3. NaN 归一化温度/质量/体积(含 `source_default` 下):保存臂传播 NaN;本实现 fail-closed。
4. 全部 11 资产输出有限性门控:任何非有限结果改为 ValueError。

逐模块审计(同一极端输入,保存臂 vs 本实现)确认每份 exact document 的
`runtime_failure` 声明真实成立;差异均记录于 `identity.assumptions` 并有回归钉死。

## 保留的保存行为(开放专家问题)

- `sigma_zz = sigma_yy` 柱对称认定(返回独立副本)。
- `empty_slice_policy="source_default"` 零密度切片语义(流速 0、温度 1 eV)。
- 零管径处壁面损失为零(保存算术,非无限管极限)。

## 变更清单

- 新增 11 个 `src/scirel/kinetic/*.py` 模块与导出(kinetic `__init__` + 根 `__init__`)。
- 新增 11 份 exact document(kind=operator)+ 其余 99 份机械 `implementation_version` 提升;`0.1.0.dev31` → `0.1.0.dev32`。
- 新增 5 个测试文件(39 直接 + 13 复放/回归;总计 51)。
- 新增候选三件套 `review_candidates/2026-09-26-neutral-moments/`、本记录与
  `docs/evaluations/intake-2026-09-26-neutral-moments.md`、index 新增 batch r60(28 条)。
- `tests/test_asset_documentation.py`、`tests/test_affected_test_selection.py`、
  `tests/test_thin_mcp_adapter.py` 计数 99→110。
- `provenance/admitted-assets.json`、`src/scirel/_validation.py`、
  `src/scirel/_composition.py`:字节零变化。

## 科学证据

- 每模块对保存实现的双臂复放(SHA-256 逐文件绑定)在声明域内逐位一致;
  拒绝行为双臂一致(声明的 fail-closed 收窄处除外,差异逐条留证)。
- 独立 oracle:冻结常数重算、圆柱体积积分重算、平移 Maxwellian 流速/温度
  恢复见证、独立梯形积分、零管径壁面损失见证、负值/取消见证。
- 逐文件测试计数(`pytest --collect-only`):11+6+14+8+12 = 51;合计运行
  **52 passed**(复放根已配置;无根时 11 条复放跳过)。
- 全模块极端输入审计(保存臂与实现逐一对照)确认输出有限性门控完备。

## 验证(全部 pwsh 7.6.6)

- 源码态全仓(`python -B -m pytest -q -p no:cacheprovider tests/`,
  `PYTHONPATH=src;tests`,复放根已配置):**1353 passed, 43 skipped,
  0 failed**(r59 1301,+51,skip 计数不变;日志行 `1353 passed, 43 skipped,
  6 warnings in 184.14s`)。
- 110/110 文档源码态与安装态(`--installed-runtime`)校验通过,含示例执行。
- 干净 venv `build/venv-r60-clean`:r45 子集 **955 passed, 159 skipped,
  0 failed**;安装态全树(`SCIREL_INSTALLED_RUNTIME=1`,`python -I -B -m
  pytest -q -o pythonpath= -p no:cacheprovider tests/`)**1234 passed,
  162 skipped, 0 failed**(日志行 `1234 passed, 162 skipped, 6 warnings in
  163.49s`;跳过数为无 `SCIREL_KN1DPY_REVIEW_ROOT` 时环境门控复放跳过)。
- catalog `build/catalog/r60`:`complete: 110/110`,root digest
  `sha256:1c982a546a392b2e60a4c9e026344f82502918c25609e96c905836ee9a53c8dd`。
- 内部 wheel `scirel-0.1.0.dev32-py3-none-any.whl`,SHA-256
  `e89eccc362ad030473721395e66497a545bbe5c0499f3473038153669967680e`。
- 候选审核材料索引:batch r60 唯一段 28 条,逐条按 Directory 解析且摘要
  与候选文件一致(脚本核验)。

## 边界与待决

- 不宣称:合格 L1 消费、对外部物理参考的正确性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(壁面源序列图、自适应网格、跨网格插值、BoltzmannRHS、SIG 矩阵、
  分子 sigv 表组装、平移 Maxwellian 矩补偿等)继续缓付。
- 许可证状态均为 `pending-human-decision`。
