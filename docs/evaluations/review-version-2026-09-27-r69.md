# SciRel GSEQ filament-coil Green family r69

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r68(`ad0331e`,`0.1.0.dev42`,132 资产,快照 `build/verification/review-2026-09-27-r68-omega-aggregation-v1`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空,未消费任何合格 L1 输入。**本批是首个非 KN1DPy 来源**:GSEQ 保存包只支持 provisional 有界历史开发比较;包实际位于兄弟主仓库 checkout `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/gseq`(读取只,零写入),不在本 intake 工作树内。

## 性质:三项新 operator(GSEQ 环形线圈 Green 链)

1. `scirel.field.coil-green-geometry`(`compute_axisymmetric_coil_modulus`):源轴偏移正则化(`r0 + 1e-8`,显式契约)后的观测半径、逐线圈椭圆模数平方与 Green 距离分母。
2. `scirel.field.complete-elliptic-integrals-approx`(`evaluate_complete_elliptic_integrals`):GSEQ apx==1 多项式-对数 K(m)、E(m) 近似,全数组 `m==1` 哨兵(`K=1e300,E=1`)与混合数组 Inf/NaN 路径逐字保留。
3. `scirel.field.filament-coil-green-field`(`evaluate_filament_coil_green_field`):GSEQ imethod==1 闭式线圈响应叠加(ψ=R A_phi、B_r、B_z)。

## 判重结论:关系变体,不是新 Green 能力

响应算子与基线 `scirel.field.circular-filament-green` 是**同一圆丝 Green 物理**,登记为声明变体(variant-of)。变体边界与公共身份分立理由:(i) K/E 由调用方逐线圈供给(GSEQ 溯源对齐)而非内部 scipy 求值;(ii) 标量观测点 + 源正则化在上游恰好一次;(iii) 组合 `2e-7*N*I` 电流因子;(iv) 奇点 fail-closed 拒绝 vs 基线的非有限置零。K/E 近似算子是独立数值关系(采样实测对 scipy 最大相对差 K ≤1e-8、E ≤2e-8,20 万点 [1e-6,0.999999] 扫描——采样证据非连续全域上界),基线没有公开 K/E 关系,不存在重复。合并进基线会破坏 GSEQ 溯源对齐链并混用两种奇点合同;变体边界记入 exact document,未来统一留专家。

## 组合回归与登记的 fail-closed 加固(全部对保存臂静默行为有意分歧)

- **预审记录的真实失败链已修**:正则化半径恰落在丝环上 → 几何算子 m=1 → K/E 算子有限哨兵(源合同保留)→ 源响应静默返回 (2e293, NaN, NaN)。响应算子现在拒绝 `separation==0 / modulus==1`(组合回归钉定该链)。
- 原始观测半径在 `(-1e-8, 0)` 被几何算子拒绝(仅靠 offset 就会静默变正,保存臂接受)。
- 溢出加固:有限极值输入(`r0=rl=1e308` 平方溢出;`current=turns=1e308` 因子溢出)在几何与响应算子显式 ValueError,不再向下游递送 NaN/Inf。
- 无修复声明:接受输入上的源算术逐字移植,只有输入/输出边界加固。

## 组合证据

- 12 项直接测试:几何/闭式/K-E 的独立复算(精确相等或 rtol=1e-15)、电流线性、镜像对中平面 B_r 抵消、同 K/E 下与基线 scipy 资产 rtol 1e-12 一致、源近似下 ≤1e-5 相对差(采样)、奇点链组合回归、负半径与溢出拒绝。fixture 每次调用重新播种。无独立复放文件:gseq 保存包以包级 oracle 为验证目标,跨实现对基线 scipy 资产提供第二臂;测试套件不对保存字节做自动漂移检测。三项保存实现的内容摘要(SHA-256,仅为证据参考记录,见 `build/test-evidence-r69.md`):轴对称线圈几何模数 `d46667c5…`、完全椭圆积分近似 `1fb09545…`、环形线圈Green场响应 `c29e18d9…`。
- 新增领域草稿 `docs/domains/neutral-particle-transport.md`(KN1DPy 中性输运链导航,以 exact documents 为唯一合同引用,provenance 上限与专家待决如实声明),已链接进 `docs/domains/README.md`。

## 相对 r68 的增量

- r68: Omega aggregation family(2 项),132 资产 dev42
- r69: GSEQ filament-coil Green family(3 项),135 资产 dev43
- 版本 `0.1.0.dev42` → `0.1.0.dev43`

## 验证(全部记录于 `build/test-evidence-r69.md`,所有子进程 returncode 已核)

- 源码态全仓(复放激活):**1498 passed, 43 skipped, 0 failed**,returncode 0(r68 全树 1486,+12)
- 135/135 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r69-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1344 passed, 197 skipped, 0 failed**,returncode 0(r68: 1332/197)
- catalog `build/catalog/r69`:`complete: 135/135`,root digest `sha256:fb1cf5257689d19ce67f4b10289d7e3298092f133539d202c555da3b00b4b116`
- 内部 wheel `scirel-0.1.0.dev43-py3-none-any.whl`,SHA-256 `4c5c21316ad7a9aa3adca6b28e72522c474bd32841717d9a453c3ba7483ffb0c`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 开放专家问题:变体的未来统一条件;K/E 近似是否保留公开身份;源 `sign`/钳制值等前批遗留待决
- 许可证状态均为 `pending-human-decision`
