# SciRel FIDASIM NPA store_npa leaf r81

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r80-v3(`2999ac5`,修复/tree 提交 `935c17f`,`0.1.0.dev57`,168 资产,快照 `build/verification/review-2026-09-27-r80-fida-spectral-family-v3`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始复核为空(0 项,含隐藏项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout `build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`(读取零写入),只支持 provisional 有界历史开发比较;本轮按 `input-manifest.json` 的 `l1/FIDASIM` scope(1253 文件)逐文件重核活字节与尺寸,并复现 ordinal recipe scope digest `sha256:cd0010b8...`(`source_byte_verified: true` 是该快照属性,不是合格 L1 声明)。

## 性质:一项新 operator(N8 store_npa 无状态标量切片)

本批整合 r80 缓付的 NPA 检测链中最小叶:

1. `scirel.fusion.npa-energy-bin-increment`(`select_npa_energy_bin_increment`):保存包 `NPA能量通道通量增量` 的无状态 record 映射——`energy = beam_mass * v2_to_E_per_amu * dot(v, v)`、Fortran `minloc` 同距最先通道、`min(orbit_class, nclass)` 类别截断、非累积 `flux/dE`(首相邻中心定 dE 的源约定;src/fidasim.f90:10600-10724)。

## 证据上限:ledger 声称 vs 本次可核证据

保存包 `extraction_ledger.md`(2026-08-16)以外部原生 source microprobe(`../FIDASIM_evidence/source_probe/npa_store_flux_audit/`,三条真实 `store_npa` 复放,`max_abs = 0`,冻结源 `9019e945...`)把该关系升级为 `source_behavior_verified`。该目录不在冻结保存输入旁,包内测试头自标 `source_unavailable`;本轮无法从冻结输入独立复查该回执。r81 将 ledger 声明记为 provenance,审查上限保持在包级 equation/boundary oracle——**不凭文字把本次上限抬到已核 Fortran runtime parity**;若后续定位到外置回执并绑定摘要,可在 successor 中提高证据级别。

## 公共资产裁定(评审发现)

保存包把该叶组合在 `NPA轨迹探测器响应图`/`NPA命中到探测器响应图`(命中轨迹 → typed store_npa record → 非累积 increment)内;这些图不移植——其节点绑定本批不整合的 N3/N8 命中与衰减生产者。叶以普通 operator 进入,图级组合待第二个消费者出现再议。

## 与现有基线的关系(对照结果)

- 基线无 NPA 能量分箱或 flux/dE 关系(rg 检索仅命中不相关子串);r80 的 FIDA 波长分箱按光子波长分箱,无共同代码路径。记为 `add`。
- 组合证据:调用方把三条返回 record 累积进自有 `(energy, detector, class)` 存储,复现含类别截断的逐 (bin, class) 部分和——即保存图声明的 N8 用法,叶本身不触碰存储。

## 源 quirk 逐字保留(回归钉定,非修复)

- `dE = grid(2) - grid(1)` 取首相邻中心对,非均匀网格与远离前两中心的命中同此约定。
- 精确同距选最先通道(Fortran `minloc` 语义)。
- detector 下标原样透传;类别按 `min(orbit_class, nclass)` 截断。

## 登记加固(各带判别回归)

1. 三个下标合同必须 genuine integer、接受 `np.integer`(保存臂 `isinstance(value, int)` 接受 `True` 但拒绝整值浮点与 `np.int64`;拒绝浮点是延续保存臂行为,接受 np.integer 与拒绝布尔才是本轮加固)。
2. 速度向量与能量中心的布尔条目(容器/bool dtype/object 三形式)拒绝;三个标量拒绝布尔与非有限值。
3. 计算能量必须有限(溢出速度/质量 fail closed,不经 inf 分箱)。
4. r81 冻结前复核发现:首间距 `dE` 必须正有限、返回 `flux/dE` 必须有限——保存臂对 `dE = 5e-324` 返回 inf、对 `(-1e308, 1e308)` 间距溢出返回静默 0.0,均违背包文档 "有限非负" 承诺。

## 同批多线圈澄清(不改默认行为)

出库实测发现 `scirel.field.multi-coil-vacuum-field` 的 `current_a` 易误读:exact document 原文只称 "source-set drive current" 且 2x2 示例省略 `weights`,而实现与旧测试默认每丝权重 1(有效每丝驱动 `current_a * weights[i]` 叠加)。若 `current_a` 是线圈截面总电流,调用方须显式分配总和 1 的权重(等分才为 1/(nr*nz));若每丝是独立载流匝,默认 1 正确。r81 仅在新开发版 exact document 中给出两种条件化说明(含 "port 无法检测调用方意图;选错会改变有效安匝数与源权重,场幅值与空间分布均可变化,2x2 等分默认权重读总电流会 4x 过驱" 的措辞)与一项辨别性数值测试(`[0.5]*4` 恰为默认场一半;`[0.25]*4` 复现 250 A 全匝运行);默认权重=1、算法与已冻 r80 摘要字节不变,不设 `sum(weights)=1` 无条件门禁(用法 (a) 合法地全 1)。

## 组合证据

- 14 项直接测试(`tests/operator_contracts/test_npa_store_family.py`):保存 probes、源 quirk 钉定、全部加固回归、N8 调用方累积证人。
- 多线圈辨别性测试位于 `tests/graph_contracts/multi_coil_vacuum_field/test_graph_multi_coil_vacuum_field.py`(+1,共 5)。
- 证据类别:包级 equation/boundary oracle + 历史 ledger microprobe 声明(外置不可复查);无自动漂移检测。

## 相对 r80-v3 的增量

- r80-v3: FIDA 谱线分量族(2 operator),168 资产 dev57
- r81: NPA store_npa 叶(1 operator),169 资产 dev58;版本 `0.1.0.dev57` → `0.1.0.dev58`
- 既有 168 份文档机械版本提升;`src/scirel/fusion/__init__.py` 追加一个纯公共导出;非机械内容变更有两处,均随本批一并审核:`multi-coil-vacuum-field` exact document 增补 `current_a` 条件化说明(科学代码/默认行为零改动),以及 `doppler-stark-zeeman-wavelengths` 源码/测试/exact doc 加入非正波长 fail-closed 修复(r80-v3 复核发现的合同缺口,按 brief 在下一开发版处理——见下节)

## 验证(全部为最终 pwsh 7+ 门禁实测回执,真实退出码已核;详见 `build/test-evidence-r81.md`)

- 源码态全仓(复放根激活):门禁回执见 `build/test-evidence-r81.md`
- 文档校验源码态:**169/169**,`runtime_origin: source`,`examples_executed: true`,exit code 0
- 安装态(干净 venv,wheel `--no-index --no-deps` 安装):文档 169/169(`runtime_origin: installed`);全树回执见 test evidence
- catalog/wheel/摘要见 test evidence

## 审核范围:首次审核集合为全部 169 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r80-v3 的快照比较只作开发增量导航辅助(变更面 = 新文档 + 168 份机械版本提升 + 多线圈文档条件化说明)。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:`fida_weights_los` 相位生产者、NPA 阶段 B 权重生产者、三项 MPI 权重归约、真实 HDF5 表驱动、MC marker 生产、并行(MPI 秩)reservoir 合并图、中性库生命周期
- 开放专家问题:(1) 历史 microprobe 回执若定位并绑定摘要,是否允许 successor 抬升本叶证据级别;(2) 多线圈 `current_a` 语义是否最终需要显式调用方声明标志而非文档约定;(3) 许可证状态均为 `pending-human-decision`

## r81 预冻结复核更正(dossier 记录)

1. 保存臂下标检查语义更正:isinstance(value, int) 对 2.0 返回 False——保存臂**拒绝**整值浮点、接受布尔、拒绝 
p.int64。因此"拒绝浮点"不是本轮新加固,只是延续保存臂行为;本轮加固是接受 
p.integer 与拒绝布尔。模块错误消息、exact document verification.scope、candidate review 已同步更正。
2. 本批实质科学增量不止 NPA 新叶:doppler-stark-zeeman-wavelengths 按 r80-v3 独立复核发现的合同缺口在本开发版加入非正波长 fail-closed(源码/测试/exact doc 更新,判别回归 `test_nonpositive_component_wavelengths_fail_closed`;输入如 E=1e11 V/m 于 121.57 nm 曾返回负分量 -218.4 nm)。它明确列入本批审核与反向依赖范围,不藏在机械升版里。