# SciRel FIDASIM beam-neutral multi-segment deposition family r78

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r77-v3(`de6b410`,`0.1.0.dev54`,158 资产,快照 `build/verification/review-2026-09-27-r77-dcx-colrad-family-v3`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空(0 项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout(读取零写入),只支持 provisional 有界历史开发比较。最终科学 HEAD `a8ca079`。

## 性质:三项新 operator + 一项组合 task_graph(N3 neutral_population_transport;沉积算子位于 N3/N4 seam)

本批整合 r77 缓付的 "束中性逐段碰撞辐射沉积闭环":

1. `scirel.fusion.beam-grid-ray-segment-tracking`(`trace_beam_grid_ray_segments`):确定性 DDA 逐段遍历,逐字保留源的 50 次固定细分定位等离子体穿越、自适应子段计数/上限、一基索引与终止策略(零速度空遍历、越界、 crossing-limit pop quirk)。
2. `scirel.fusion.n3-n4-segment-deposition`(`assemble_n3_n4_segment_deposition`):逐段 N4 handoff 校验(中点对齐、零基下标、精确 prior state、dt 一致、非空 provenance)与源 marker 归一化(`dens/nlaunch`、`photons/nlaunch`、population-loss flux、累计沉积)。
3. `scirel.fusion.ndmc-deposition-producer`(`run_ndmc_deposition_producer`):源忠实 `nneutrals`(e0 = 1.60217733e-19,src/fidasim.f90:69)与逐分量初态门,`store_neutrals` 全/半/三分之一群体累积与 `flux_tot`(逐段 `flux*dv` 相加不重排)。
4. `scirel.fusion.beam-neutral-segment-deposition-loop`(`deposit_beam_neutral_segments`,kind task_graph):保存包 `束中性逐段碰撞辐射沉积图` 的源顺序组合(deposition_initialization → beam_grid_track → local_state_sequence → n4_cell_update_handoff → deposition),节点顺序不可交换;组合两个已集成叶 + graph-internal 校验节点,carried state 与累计沉积为显式反馈。

## 公共资产裁定(评审发现)

保存包将 `N3逐段沉积初态规范化` 与 `N3局域等离子体原子快照规范化` 声明为独立 operator。两者均为 data-edge 校验门——逐字返回调用方数据,无科学关系——而现有集成公共资产中没有纯 pass-through 校验器(最薄的 `dcx-thermal-species-selection` 也输出被下游消费的量)。裁定:两者作为 deposition 图的 graph-internal 校验节点执行(逐字复现保存合同,registered deviation from saved packaging);待出现第二个独立消费者(如真实 HDF5 表驱动)再提升为公共资产。

## 量纲调解(评审发现,非专家认可;未决问题保留专家裁定)

1. **N3/N4 链携带 rate-density 状态(cm^-3 s^-1)**:源以 `states(1) = nneutrals*fraction/dv` 播种(nneutrals 单位 particles/s,src/fidasim.f90:13016-13057);已集成 `nbi-component-initial-state` 资产已标注 `initial_state_rate_per_volume_cm_inv3_s_inv`(cm^-3 s^-1,"源的隐式 1 s 约定未证明")。因此 `(sum(previous)-sum(next))/nlaunch` 为 cm^-3 s^-1、`flux*dv` 为 particles/s,`deposited_particles_per_s` 标注正确;保存臂 `*_cm_inv3` 状态字段名误标该单位,新公共名采用精确 `*_cm_inv3_s_inv` 形式(无预发布兼容负担)。
2. **colrad 单位标注重审**:colrad 推进为单位无关线性代数;rate-density 输入下其积分密度为 cm^-3(与 `store_neutrals` 的 `pop%dens += dens/nlaunch` 一致)、光子输出为 cm^-3 s^-1(与 handoff 的 `photons_per_cm3_s` 一致)。冻结 r77 `collisional-radiative-state-advance` 文档标注(states cm^-3、integrated cm^-3 s、photons s^-1)与其自身家族初态输出(cm^-3 s^-1)不一致,已在本 successor 中作为开发合同修复更正(算术不变;r77-v3 冻结字节原样保留);不声明直接组合:N4 记录保持显式外部调用方能力(保存图自身声明 "caller separately composes N4")。
3. **有符号段通量**:源 `flux = (iflux - sum(states))/nlaunch` 有符号;当 rate matrix 的 inflow(population)项超过 loss 项时 colrad 产生净群体增益(全列和 ≤0 的 loss-only 矩阵不能产生增益)。证人使用已集成 `collisional-radiative-state-advance` 与此类矩阵端到端贯通 N3→NDMC。NDMC producer 因此只要求有限性(源忠实有符号累积);保存臂文档的非负声明及实现对负记录的拒绝记录为 bounded incompatibility,交专家裁定。
4. **e0 分叉(既有跨资产分歧)**:`nbi-injected-neutrals-normalization` 用 CODATA 2018(1.602176634e-19),`nbi-component-initial-state` 与本 producer 门用源值 1.60217733e-19(冻结 trace rel 0.0 vs ~4.34e-7)。源忠实门有意拒绝 CODATA-e0 归一化;冻结源应统一哪个常数由专家裁定。
5. **nlaunch 归一化语义**:源在 `store_neutrals` 前执行 `dens/nlaunch`,消费记录携带 per-marker 归一化密度;调用方不得重复归一化。声明方式由专家裁定。

## 登记的分歧与加固

- **登记加固**(带判别见证):genuine-integer 轨道限制、sample 下标与 grid shape(bool、`np.bool_`、整值浮点拒绝——保存臂 `isinstance(int)`/`astype(int)` 接受 bool、截断浮点);`nlaunch`/体积/时长/prior 沉积的 genuine finite scalar 门(含 graph-internal 初始化与快照助手);非数值 N4 记录字段抛 ValueError 而非裸 TypeError;负 `dens_cm_inv3` 或 `photons_per_cm3_s` fail closed(保存臂自身合同声明非负但实现只拒绝负 next states);快照助手跃迁表 knot 数为 genuine integer(保存臂 `int()` 静默截断);NDMC 累积群体必须保持有限。
- **源 quirk 逐字保留**:零速度空遍历、50 步穿越二分、crossing-limit pop、自适应计数/上限公式、沉积图源节点顺序(不可交换)、真空段零温接受、in-grid `store_neutrals` 累积顺序。

## 组合证据

- 28 项直接测试(`tests/operator_contracts/test_beam_deposition_family.py`):四资产保存 probes、端到端 colrad 群体增益证人、signed-flux 与负期望总量、record-count 与快照合同拒绝、上述全部加固。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要逐资产记录于 exact documents 与 `build/test-evidence-r78.md`(参考记录,无自动漂移检测)。

## 相对 r77-v3 的增量

- r77-v3: DCX/HALO colrad 家族 + 弹道分支矩阵校验修复,158 资产 dev54
- r78: 束中性逐段沉积家族(3 operator + 1 组合图),162 资产 dev55;版本 `0.1.0.dev54` → `0.1.0.dev55`
- 既有 158 份文档机械版本提升;`scirel.fusion.collisional-radiative-state-advance` 额外携带单位标注修复(仅文档文本);`src/scirel/fusion/__init__.py` 追加五个纯公共导出与一个常数

## 验证(全部为实测回执,子进程 returncode 已核;详见 `build/test-evidence-r78.md`)

- 源码态全仓(复放根激活):**1634 passed, 43 skipped, 0 failed**,returncode 0(r77-v3 全树 1606,+28)
- 文档校验源码态:**162/162**,`runtime_origin: source`,`examples_executed: true`
- 安装态(干净 venv,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1 + setuptools 84.0.0,wheel `--no-index --no-deps`,`-I`):文档 **162/162**(`runtime_origin: installed`,示例执行通过);全树 **1633 passed, 44 skipped, 0 failed**,returncode 0
- catalog `build/catalog/r78`:`complete: 162/162`,root digest `sha256:f16f84e0a46e9552b64f0e2e9804bcc3b6ee9135dc390d5d0179b9420d6fbfbf`
- 内部 wheel `scirel-0.1.0.dev55-py3-none-any.whl`,SHA-256 `591a42918a7f15ca12d59ccfd580d1056b6c09ef8b51555906540bec9eedd73b`

## 审核范围:首次审核集合为全部 162 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r77-v3 的快照比较只作开发增量导航辅助。实测回执在冻结后记录于 post-freeze addendum(如有)。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:真实 HDF5 表驱动、NBI 权重生产链(NPA/FIDA 谱)、多 cell 种群合并(中性库合并家族)与 MC marker 生产
- 开放专家问题:rate-density 状态单位与源隐式 1 s 约定、colrad 文档单位标注修复是否需同步其它 colrad 家族声明、有符号段通量的 bounded incompatibility、e0 分叉的统一选择、nlaunch 归一化语义的声明方式
- 许可证状态均为 `pending-human-decision`
