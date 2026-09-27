# SciRel FIDASIM cross-node leaf family r72

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r71(`f1f07e6`,`0.1.0.dev45`,142 资产,快照 `build/verification/review-2026-09-27-r71-nbi-birth-leaves-v2`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空,未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout,只支持 provisional 有界历史开发比较。

## 性质:五项新 operator(跨 N2/N7/N9 节点的独立确定性叶)

按保存 `program_framework_map.md` 节点归属:

1. `scirel.fusion.dd-rate-table-interpolation`(`dd_reaction_rate_per_s`,N9):双线性 log10 速率表插值 + 密度缩放,branch_index 零基。
2. `scirel.fusion.fast-ion-relative-energy`(`calculate_fast_ion_relative_energy`,N9):`E_rel = v2_to_E_per_amu * A * |v_i - v_rot|^2`。
3. `scirel.fusion.mc-marker-weight-allocation`(`allocate_mc_markers_by_weight`,N7):get_nlaunch 标记分配,caller-owned CDF 变itate,F-order 逆 CDF 采样。
4. `scirel.fusion.nbi-injected-neutrals-normalization`(`normalize_nbi_injected_neutrals`,N2):ndmc 功率到中性态归一化,使用 CODATA 2018 e=1.602176634e-19 C。
5. `scirel.fusion.nbi-cell-directed-ray`(`nbi_cell_directed_ray`,N2):mc_nbi_cell 确定性射线几何 + 孔径接受 + 高斯发散权重。

## 判重结论

- 与 r71 初态叶的 e0 差异是**登记的合同差异**,不是缺陷:N2 的两条归一化路径(六能级初态物化用源 e=1.60217733e-19;本批 ndmc 归一化用 CODATA 2018 e=1.602176634e-19)在保存 program map 中就是不同节点产物,保存 map 记录 e0 差异为开放专家裁决,不合并。
- 与 Bosch-Hale:解析 Maxwellian 拟合 vs 调用方提供的冻结表插值——不同关系,无重叠。
- 五叶彼此独立(表插值、运动学能量、标记计数、归一化、射线几何),跨 N2/N7/N9 无组合 TaskGraph,组合缺口如实声明。

## 登记的分歧

- **DD 速率指数溢出门**:有限极值表内容使 `10^log_rate` 溢出;保存臂静默 Inf。
- **相对能量溢出门**:max-finite 速度点积溢出;保存臂静默 Inf。
- **标记守恒门**:分配总数必须等于 requested_markers;保存臂无此检查。
- **严格 branch_index**:bool 与 float 通过源 isinstance 检查;本移植拒绝。
- **源 quirk 逐字保留**:theta_z-uses-focy(保存包自身 probe 钉定)、Float32 分量除数、超出末区间的零返回。

## 组合证据

- 16 项直接测试:双线性独立复算(rtol 1e-15)、相对能量零静止恒等、F-order CDF 复算与计数守恒、NBI 归一化源公式、保存包自身 ray probe、Float32 除数恒等,以及上列加固见证。fixture 每次调用重新播种。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标,闭式复算与摘要同行记录提供溯源链接。

## 相对 r71 的增量

- r71: NBI birth/geometry leaf family(5 项),142 资产 dev45
- r72: cross-node leaf family(5 项),147 资产 dev46
- 版本 `0.1.0.dev45` → `0.1.0.dev46`

## 验证(全部记录于 `build/test-evidence-r72.md`,所有子进程 returncode 已核)

- 源码态全仓(复放激活):**1540 passed, 43 skipped, 0 failed**,returncode 0(r71 全树 1524,+16)
- 147/147 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r72-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1386 passed, 197 skipped, 0 failed**,returncode 0(r71: 1370/197)
- catalog `build/catalog/r72`:`complete: 147/147`,root digest `sha256:08827967326d798de0f39980e874c39adcffb1f478e823db43682d372c237b2a`
- 内部 wheel `scirel-0.1.0.dev46-py3-none-any.whl`,SHA-256 `85742b791bbb7e068f62c9693edbd0530f274055cae994bbda2baaa7f7931c58`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:NBI 权重生产链、DCX 谱线状态、外层 NBI 源几何、外层框架 TaskGraph
- 开放专家问题:e0 差异(CODATA vs 源)的裁决、DD 表的物理精度、theta_z quirk 的物理含义
- 许可证状态均为 `pending-human-decision`
