# SciRel FIDASIM DCX/HALO colrad 家族 r77

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r76-v1(`0cca44c`,`0.1.0.dev51`,153 资产,快照 `build/verification/review-2026-09-27-r76-halo-iteration-feedback-v1`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空(0 项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout(读取零写入),只支持 provisional 有界历史开发比较。最终科学 HEAD `8aa1da1`。

## 性质:四项新 operator + 一项组合 task_graph(N3 neutral_population_transport;推进算子位于 N3/N4 seam)

本批整合 r75/r76 缓付的 "DCX 谱线状态" 项所依赖的 colrad 核心。全部表格由调用方显式提供——不发明任何原子数据事实:

1. `scirel.fusion.dcx-thermal-species-selection`(`select_dcx_thermal_species_mass`):源物种循环的质量选择。
2. `scirel.fusion.dcx-halo-colrad-initial-state`(`prepare_dcx_colrad_initial_state`):单标记初态加权;快离子密度仅在束质量与被选热离子质量严格相等的同位素分支计入;光子快离子修正为热份额;全零初态返回 eligible=false 而非报错。
3. `scirel.fusion.collisional-radiative-rate-matrix`(`assemble_collisional_radiative_rate_matrix`):由三张调用方跃迁表(H-H、H-e、杂质)与局域等离子体态组装实速率矩阵;逐字保留 `log10(E_b/A_b)` 与温度表坐标、双线性插值、minlog 低率阈值、上表缘零率策略、同质量快离子加和与 Einstein 列和对角重写。
4. `scirel.fusion.collisional-radiative-state-advance`(`advance_collisional_radiative_states`):本征分解推进一个时间步(`src/fidasim.f90:11776-11837`),时间积分密度投影与 Einstein 光子率;等离子体外走弹道分支(状态不变、`state*dt`、零光子、不消费矩阵);实本征态合同(虚部 ≤1e-12)是源语义门。
5. `scirel.fusion.dcx-halo-marker-initialization`(`initialize_dcx_halo_marker`,kind task_graph):保存包 `DCXHalo标记初态图` 的源顺序组合(位置采样 → plasma 能力 → 物种选择 → halo 速度 → CX-rate 能力 → 初态加权),节点顺序不可交换;组合四个已集成叶 + 两个调用方能力(可调用对象作为显式输入端口)。

## 判重结论

- 对基线:无 colrad 矩阵组装、本征推进、DCX 初态加权或标记初始化组合资产。KN1DPy 的 `atomic/molecular-collision-matrix-assembly` 是中性输运的弹性碰撞矩阵(不同公式、不同能级结构、不同表合同),不合并。
- 对未发布候选池:无重叠。
- 依赖闭包完整:全部表格、速率与等离子体态均为调用方显式合同;无隐藏原子数据。

## 登记的分歧与加固

- **零特征值边界(钉定而非修复)**:保存臂 `(exp(0)-1)/1` 规则使零模式积分密度为 0,而 Fortran 源对零特征值先 `+1` 再 exp(数值避零怪癖,值不同)。保存包自身的 ledger 已登记该分歧,并证明在 823 次有界复放事件(240 合成 + 583 真实 HDF5 表)中均未触发(全部非零特征值)。本移植逐字复现保存臂并以判别回归钉定;提请专家裁定,不做静默修复。
- **特征求解器条件底噪**:本移植使用 numpy/LAPACK 求解器,非源的 balance+QR eigensystem;保存 ledger 记录 583 真实表事件中对捕获通量 ~5e-6 的条件底噪(独立参考间 ~1e-13)。作为证据上限记录,不声称逐位一致。
- **登记加固**(带判别见证):states/dt/矩阵/表格/Einstein 率/初态乘积的有限与类型门(保存臂静默传播 NaN/Inf,表格字段缺失抛裸 KeyError);严格整数 emitting/species 下标(bool 拒绝);表格间距必须为正;exp 溢出 fail closed;provider 合同违规抛 ValueError(含缺失字段名)而非裸 TypeError/KeyError。
- **源 quirk 逐字保留**:上表缘零率策略、minlog 阈值置零、严格相等同位素分支、Einstein 列和对角重写、实本征态 1e-12 合同、弹道分支不消费矩阵、标记切片源节点顺序。

## 组合证据

- 17 项直接测试:保存 probe 复现(同位素份额、常量表矩阵 oracle、上表缘策略、对角本征推进与光子投影、弹道规则、含 graph_order 诊断的标记流)、逐叶直调等价、provider 调用顺序强制、provider 合同拒绝、上列加固与两个钉定回归。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要逐资产记录于 exact documents 与 `build/test-evidence-r77.md`(参考记录,无自动漂移检测)。

## 相对 r76-v1 的增量

- r76-v1: DCX/HALO 迭代反馈家族(1 operator + 1 有界序列图),153 资产 dev51
- r77: DCX/HALO colrad 家族(4 operator + 1 组合图),158 资产 dev52;版本 `0.1.0.dev51` → `0.1.0.dev52`
- 全部 153 份既有文档仅机械版本提升;`src/scirel/fusion/__init__.py` 五项纯公共导出追加

## 验证(全部为实测回执,子进程 returncode 已核;详见 `build/test-evidence-r77.md`)

- 源码态全仓(复放根激活):**1604 passed, 43 skipped, 0 failed**,returncode 0(r76 全树 1587,+17)
- 文档校验源码态:**158/158**,`runtime_origin: source`,`examples_executed: true`
- 安装态(干净 venv,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1 + setuptools 84.0.0,wheel `--no-index --no-deps`,`-I`):文档 **158/158**(`runtime_origin: installed`,示例执行通过);全树回执见 evidence 文件
- catalog `build/catalog/r77`:`complete: 158/158`,root digest `sha256:4a70c6ad5a1033b08a5681836833695398ae9424395ca4af8def6e34b6356454`
- 内部 wheel `scirel-0.1.0.dev52-py3-none-any.whl`,SHA-256 `89e4e7e89113f872c3d375ad68ea12e253edaab4517fb96ae6af800faa17f7bc`

## 审核范围:首次审核集合为全部 158 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r76-v1 的快照比较只作开发增量导航辅助。实测回执在冻结后记录于 post-freeze addendum。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:真实 HDF5 表驱动与多段沉积闭环(束中性逐段碰撞辐射沉积图)、NBI 权重生产链(NPA/FIDA 谱)、多 cell 种群合并与 MC marker 生产
- 开放专家问题:零特征值 +1 避零怪癖的物理含义与本移植应否同步、eigensolver 条件底噪对 colrad 谱全族的物理充分性、同位素严格相等判据在浮点质量下的适用性
- 许可证状态均为 `pending-human-decision`
