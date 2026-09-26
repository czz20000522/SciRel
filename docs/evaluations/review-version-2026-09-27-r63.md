# SciRel KN1DPy transport-step family r63

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r62(`965028c`,快照 `build/verification/review-2026-09-27-r62-dist-interp-v3`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:三项新 operator(中性输运步家族)

1. `scirel.kinetic.neutral-upwind-transport-coefficients`
   (`assemble_neutral_upwind_transport_coefficients`;源锚
   `KN1DPy/kinetic_h.py:1170-1249`;保存 SHA-256
   `b7b2979415f82d64fb9f963d1c6e531a9ff6353b8d93e209d3370b34db721bf2`):
   正向/反向梯形推进系数 Ak/Bk/Fk/Ck/Dk/Gk 的组装。该算子涉及 x 与 vx
   两轴(不含 vr);vx 必须有限且含正/负分支,x 必须严格递增且有限。
2. `scirel.kinetic.neutral-generation-propagation`
   (`propagate_neutral_generation`;源锚
   `KN1DPy/kinetic_h.py:1260-1275; kinetic_h2.py:1385-1415`;保存 SHA-256
   `9d24a06959b37deaa142857bf75bb545c1bedcdbd9ec54f721c62387698c1a13`):
   first_flight 与 scattered 两种代际的双向传播。
   Bk 为 scattered 分支的正向源系数(非 first-flight);first_flight 使用
   Fk;scattered 使用 Bk/Dk。incoming_boundary 仅应用于正 vx 分支;
   负 vx 分支右边界固定零。vx 必须有限(NaN/inf 节点被保存臂静默通过,
   本实现 fail-closed)。
3. `scirel.kinetic.neutral-boltzmann-rhs`
   (`assemble_neutral_boltzmann_rhs`;源锚
   `KN1DPy/kinetic_h.py:1636-1646; kinetic_h2.py:1794-1803`;保存 SHA-256
   `fc47ee0a4c5ad0668844cc0ca30bf6ba4b3fc3530e8ca393e60642d8cf9e95fa`):
   Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall) 的显式 RHS 组装。
   保存臂的 NaN 热速度在双臂上均被 ValueError 拒绝(见
   `test_the_saved_rejection_behavior_agrees_exactly`)。

保存实现逐位复现;无修复。

## 声明的域收紧(r63 预审)

- **upwind**: x 有限性(保存臂 NaN x 通过单调性谓词);vx 有限性(inf 通过)。
- **propagation**: vx 有限性(保存臂 NaN vx 静默通过);incoming_boundary
  仅应用于正 vx 分支;Bk 为 scattered 源系数(非 first-flight)。
- **BoltzmannRHS**: 热速度有限性(保存臂 NaN 热速度被 ValueError 拒绝,
  与本实现一致,无分歧)。

## 变更清单

- 新增 3 个模块 + 导出;新增 3 份 exact document + 其余 113 份机械提升;`dev36` → `dev37`。
- 新增 2 个测试文件(`test_transport_step.py` 10 direct + `test_transport_step_l1.py` 4 replay)。
- 新增候选文档 `review_candidates/2026-09-27-mesh-seam/review.md`;index batch r62(11 条)。
- 账本与 _validation/_composition 字节零变化。

## 科学证据

- 双臂复放(SHA-256 绑定):两种 generation_kind、重复调用,逐位一致。
- 独立 oracle: 正向步闭环公式 Ak=(2*vx-dx*alpha_k)/(2*vx+dx*alpha_{k+1});
  BoltzmannRHS 独立符号和重算。
- 逐文件计数:direct 10 + replay 4 = 14。

## 验证(全部 pwsh 7.6.6)

- 源码态全仓:**1395 passed, 43 skipped, 0 failed**(log `1395 passed, 43 skipped, 7 warnings in 217.95s`)。
- 116/116 文档源码态与安装态校验通过,含示例执行。
- 安装态全树:**1266 passed, 172 skipped, 0 failed**(log `1266 passed, 172 skipped, 7 warnings in 188.48s`)。
- catalog `build/catalog/r63`:`complete: 116/116`,root digest `sha256:9bb68e645c60564a431d71029245f5aa2eb559ba81e8e8fbd0e2571699d9133e`。
- 内部 wheel `scirel-0.1.0.dev37-py3-none-any.whl`,SHA-256 见 manifest。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行。
- 继续缓付:SIG 矩阵、分子 sigv 表、Franck-Condon 源、平移 Maxwellian 矩补偿、壁面源序列等。
- 许可证状态均为 `pending-human-decision`。
