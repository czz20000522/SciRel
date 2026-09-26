# SciRel KN1DPy collision-matrix assembly family r67

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r66(`6240995`,`0.1.0.dev40`,128 资产,快照 `build/verification/review-2026-09-27-r66-alpha-contraction-v3`)的 successor;既有快照(v1/v2/v3)原样保留。合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均复核为空,未消费任何合格 L1 输入。

## 性质:两项新 operator(碰撞矩阵装配族)

来源为保存 KN1DPy 包(`D1待重审历史产物/KN1DPy-631d0bf1`,严格 D1 资格已撤回,provisional),实现文件按 SHA-256 钉定:

1. `scirel.kinetic.atomic-collision-matrix-assembly`(`assemble_atomic_hydrogen_collision_matrices`):从显式速度载子(`vr, vx, Vr2pidVr, dVx`)与热归一化(`Tnorm, mu`)出发,经双速度空间前驱几何、嵌入式 theta 五点求积与 Fortran-order reshape,装配四个 `(N,N)` 原子 SIG 矩阵(`SIG_CX`、`SIG_H_H`、`SIG_H_H2`、`SIG_H_P`),并返回保存臂声明的取证状态字段(`v_v2`、`v_v`、`vr2_vx2`、`vx_vx`、`Vr2pidVrdVx`、`Vth2`)。
2. `scirel.kinetic.molecular-collision-matrix-assembly`(`assemble_molecular_hydrogen_collision_matrices`):分子 H2 四族同构装配(`SIG_CX`、`SIG_H2_H`、`SIG_H2_P`、`SIG_H2_H2`);分子 `SIG_CX` 能量因子 `H_MASS*Vth2/Q`(无 0.5、无 `mu`,kinetic_h2.py:1045)逐字保留,判别测试防止被对齐到原子侧约定。

本批闭合 r66 收缩算子声明的直接上游边(N4-1 / N3-1):截面叶(r49/r51/r53)→ 权重/热速度 → SIG 装配 → Alpha 收缩。

## 复用判断与登记的分歧(本批核心预审事项)

- **截面拟合复用公共叶,不内嵌第二份公式**:保存包逐字内嵌 KN1DPy `sigma/` 拟合;本移植经已集成的 `scirel.collisions` 叶求值(系数与 clip 逐项相同)。20 万点能量探针(覆盖全部 clip 端点、H-P 10 eV 分支边界、E=0)显示两臂各三个弹性族与内嵌拟合**逐位一致**;各臂 CX 族最大相对差 2.22e-15(原子)/2.21e-15(分子),根因为标准化 `np.exp` vs 源 `np.e **`(100 万点对数网格根因探针:按 `np.spacing` 度量最大 17 个双精度 ulp)。以上为**采样证据,非连续全域上界**;CX 族复放容差定为 rtol=1e-14。回退条件:若专家要求 CX 族逐位复放,需重新内嵌带标注的源公式副本。
- **形状约定归一**:集成叶存在两种已声明的输出形状约定(部分带前导单元素轴);移植端口归一到载子形状,其他形状 fail closed。该归一包装是新增声明代码,不是源代码。
- **Tnorm/mu 标量收紧(端口新增 fail-closed)**:保存臂接受 size-1 数组并会产出 `(1,1)` Vth2;本端口拒绝任何非 0-d 输入。登记为对保存臂拒绝行为的有意分歧。
- **单位声明**:`Tnorm` 以 eV 声明(与 thermal-speed-scale 关系同约定);`vr` 声明为正(校验只拒绝非正,无单调门禁)、`vx` 严格递增且含正负两侧(无精确对称门禁)——文字与实际执行的门禁一致。

## 科学边界

- `SIG_CX` 在声明域非负;两臂各三个弹性族的有界负元由带符号 `vr2_vx2`/`vx_vx` 因子内在产生,如实复现、不 clamp;物理可接受性留待专家。
- 无状态确定性映射:不读 `KH.Internal`/`KH2.Internal` 缓存、不依赖 `Do_SIG_*` 门控或 `New_Grid` 生命周期(源缓存两态取证逐位一致)、不写回调用方状态。
- **登记的源文档冲突**:保存分子臂 operator.md 称 canonical 2x2 负元计数 2/2/4,但用保存包测试自身 canonical fixture 可复现的计算为 4/4/8(原子臂 8/4/4 相符)。保存文档原样保留,候选测试断言实际复算结果,原因留待专家审查。

## 组合证据

- 17 项测试(14 直接 + 3 环境 gating 复放):独立 broadcasting-geometry oracle(基于源自身内嵌公式,rtol=1e-12 为保存包预算)、前驱状态、`SIG_CX` 非负、弹性负元有界及 canonical 确定性计数、fail-closed 载子合同(含标量收紧)、输入只读、以及装配→r66 收缩端到端组合。
- 复放:SHA-256 钉定保存臂——弹性族与前驱状态逐位一致,CX 族 rtol=1e-14,拒绝行为一致。

## 相对 r66 的增量

- r66: collision frequency contraction family(2 项),128 资产 dev40
- r67: collision-matrix assembly family(2 项),130 资产 dev41
- 版本 `0.1.0.dev40` → `0.1.0.dev41`
- 每臂声明 4 项 `scirel.collisions` 集成依赖(保存包内嵌同源拟合);其他资产合同不变(仅机械版本号 bump)

## 验证(全部记录于 `build/test-evidence-r67.md`)

- 源码态全仓(复放激活):**1462 passed, 43 skipped, 0 failed**(r66-v3 全树 1445,+17)
- 130/130 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1313 passed, 192 skipped, 0 failed**(r66: 1290/189)
- catalog `build/catalog/r67`:`complete: 130/130`,root digest `sha256:6c0f4ea2ea227ff70a60756be401114f730527f0bcc0e0cc956c0b444d89f3e5`
- 内部 wheel `scirel-0.1.0.dev41-py3-none-any.whl`,SHA-256 `494e67e2df060a3c5071b23cb298b6a915a3e4975ecd6943ccc8c1cd0e13f2e6`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:分子 sigv 反应速率表(需 10 叶速率算子的图编排)、N4-3/N3-4 Omega 下游聚合、`SIG_D2_*` 其他碰撞族、外部原子物理参考(`validation_oracle_gap`)
- 分子 operator.md 负元计数冲突、CX 逐位复放回退条件、分子装配是否需独立物理 oracle、原子/分子 `SIG_CX` 能量因子差异是否需跨路径对账,均为开放专家问题
- 许可证状态均为 `pending-human-decision`
