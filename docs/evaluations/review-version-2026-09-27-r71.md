# SciRel FIDASIM NBI birth/geometry leaf family r71

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r70(`644b223`,`0.1.0.dev44`,137 资产,快照 `build/verification/review-2026-09-27-r70-fast-ion-kinematics-v3`)的 successor;既有快照(v1/v2/v3)原样保留。合格 L1 交付根在本轮开始与结束均复核为空,未消费任何合格 L1 输入。FIDASIM 保存包实际位于兄弟主仓库 checkout `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`(读取只,零写入),只支持 provisional 有界历史开发比较。

## 性质:五项新 operator(跨 N2/N3/N7 节点的独立确定性叶)

按保存包 `program_framework_map.md` 的节点归属:N2 neutral_beam_source_sampling(能量分量速度缩放、六能级初态物化、束网格 cell 采样)、N3 neutral_population_transport(热 halo 速度采样)、N7 fast_ion_fida_response(俯仰/回旋角方向映射——保存 operator.md 明确这是快离子局域磁场标架方向,不是 NBI 中性束出生关系)。五叶是跨节点独立叶;框架图未发射组合它们的 TaskGraph(N7 标架是局域磁场标架,不是 NBI 出生射线),故不含跨节点组合测试,该组合证据缺口如实声明。

1. `scirel.fusion.nbi-energy-component-velocity`(`scale_nbi_velocity_for_energy_component`):full/half/third 能量分量速度缩放,`sqrt(Float32(efrac))` 除数逐字保留。
2. `scirel.fusion.nbi-component-initial-state`(`materialize_nbi_component_initial_state`):六能级初态物化,`states(1) = nneutrals*fraction/dv`,仅能级 1 有布居。
3. `scirel.fusion.thermal-halo-velocity-sampling`(`sample_halo_velocity`):热 Maxwellian halo 出生速度,随机性由调用方持有的标准正态变itate 承载。
4. `scirel.fusion.beam-grid-cell-sampling`(`sample_beam_grid_cell`):笛卡尔束网格 cell 出生位置,零均值仿射映射。
5. `scirel.fusion.pitch-gyro-velocity-direction`(`pitch_gyro_to_velocity_direction`):俯仰/回旋角到单位速度方向,`sqrt(1-pitch^2)*cos*a + pitch*b + sqrt(1-pitch^2)*sin*c`(早期草稿的 `sin(gyro)*cos(angle)` 为转写错误,已更正)。

本批五叶与 r70 的权重/修正消费者无关系重叠,且彼此跨 N2/N3/N7 独立。

## 判重结论

- 对 r70:无重叠——r70 是中子权重与位置修正;本批是出生态(密度/能级)、出生位置(网格 cell)与出生方向(俯仰/回旋框架)。
- 对基线 `shifted-maxwellian-seed`(KN1DPy):该资产构造柱面速度网格上的归一化分布;halo 叶把单个粒子的调用方正态变itate映射为速度——域、输出与单位记账均不同,不合并。
- 五叶彼此是独立关系(能量缩放、能级物化、热采样、位置采样、方向映射),各有独立保存包,互不重复。
- 排除(证据不足):MPI 归约/门包(NBI 三谱、NPA 权重)是运行时门而非科学关系;DCX 系列依赖尚未提取的谱线状态。

## 登记的分歧与直接见证

- **权重因子溢出门**:三个有限 max-float 份额使权重和溢出为 Inf(保存臂返回 rate 0 + Inf factor);本移植在除法前 fail-closed。
- **密度溢出门**:有限 rate 乘极小 volume 溢出逐格密度(rate 门查不到的路径由密度门兜住);保存臂静默 Inf。
- **halo 分母下溢归一**:分母积下溢到 0.0 时保存臂抛裸 `ZeroDivisionError`;本移植转为统一的 `ValueError`,接受域不变(仅异常类型分歧)。
- **速度缩放溢出见证**:模数通过 1e-12 isclose 窗但大于 1.0 的有限 ray(如 `1+1e-12`)乘 max 有限速度溢出并被拒绝。
- **输入收紧**:有限正标量速度(NaN 通过源的 `vinj<=0` 检查)、严格 int 分量 1/2/3(bool 与 float 1.0 通过源的 tuple 成员相等)、`nlevels` 恰为 6。
- **俯仰恒等式为容差限定**:`dot(direction, b_unit) == pitch` 在精确正交框架下精确,在接受的 1e-12 容差框架内该恒等式带同阶容差;直接测试只在 canonical 框架断言精确恒等,并在随机 QR 框架断言容差限定恒等。
- **caller-owned 随机性**:halo 与束网格叶以显式变itate为输入,不绑定 RNG,相同变itate 逐位重放。
- **零功率是合法输入**(全零态、有限零 rate);exact doc 写实际符号合同而非"正功率"。

## 组合证据

- 9 项直接测试:五叶全部对独立闭式复算精确相等(Float32 除数、level-1-only、热速度公式、零均值仿射、俯仰分解),结构恒等式(单位范数、中点/零宽塌缩、相同变itate确定性、零温塌缩),以及上列登记加固与见证。fixture 每次调用重新播种,单 affected 用例与整文件运行的载子逐位一致。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标,闭式复算与保存实现摘要(同行记录于 `build/test-evidence-r71.md`)提供溯源链接;无自动漂移检测。

## 相对 r70 的增量

- r70: fast-ion kinematics family(2 项),137 资产 dev44
- r71: NBI birth/geometry leaf family(5 项),142 资产 dev45
- 版本 `0.1.0.dev44` → `0.1.0.dev45`

## 验证(全部记录于 `build/test-evidence-r71.md`,所有子进程 returncode 已核)

- 源码态全仓(复放激活):**1524 passed, 43 skipped, 0 failed**,returncode 0。真实 r70-v3 基线(commit `644b223`,在临时 worktree 直接实测 **1515 passed/43 skipped**,rc=0)+9 项 NBI 测试;r70 旧证据的 1508 是 v1 树(在 review-scope 修复 `acef9c5` 新增 7 项 collected 之前)的数,跨版本对账以 r70-v3 的 1515 为准
- 142/142 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r71-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1370 passed, 197 skipped, 0 failed**,returncode 0。r70-v1 证据的 1354/197 是 v1 树的数(在 `acef9c5` +7 collected 之前),与 r71 的 1370 不可直接对账;r70-v3 的安装态基线未直接重跑,不在此推算任何派生数字;本安装态回执由审查者独立复跑通过
- catalog `build/catalog/r71`:`complete: 142/142`,root digest `sha256:854cc403400d1b37443f14cf8807f46c84f5d458fe4dc34b8a26196c4ef1b4eb`
- 内部 wheel `scirel-0.1.0.dev45-py3-none-any.whl`,SHA-256 `5fc36403906b3357bcf1e6971d46aefa2f0be6d64cc8446d4998810d691ae82e`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:NBI 权重生产链(NPA/FIDA 谱)、DCX/Halo 谱线状态、中子谱归约(MPI 门包)、外层 NBI 源几何(源面射线与孔径)
- 开放专家问题:Float32 除数的物理精度、六能级模型的适用性、halo 采样与源 MC 分布的一致性
- 许可证状态均为 `pending-human-decision`
