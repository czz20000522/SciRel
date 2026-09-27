# SciRel FIDASIM FIDA spectral-component family r80

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r79-v3(`f562536`,科学 HEAD `e509afb`,`0.1.0.dev56`,166 资产,快照 `build/verification/review-2026-09-27-r79-neutral-merge-family-v3`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始复核为空(0 项,含隐藏项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout `build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`(读取零写入),只支持 provisional 有界历史开发比较。

## 性质:两项新 operator(N5 谱线分量波长 + N6 FIDA 波长分箱)

本批整合 r79 再次缓付的 "NPA/FIDA 权重生产链" 中有依据的最小切片——FIDA 谱线叶对:

1. `scirel.fusion.doppler-stark-zeeman-wavelengths`(`doppler_stark_zeeman_wavelengths`):保存包 `多普勒StarkZeeman谱线波长` 的单视线分量波长——非相对论 Doppler 位移叠加 Stark--Zeeman 能级差位移(`E' = ||E + v x B||`,速度仅一次 cm/s→m/s 转换,固定 3 分量 Lyman-α / 15 分量 Balmer-α 次序;src/fidasim.f90:69-81,11891-11963)。
2. `scirel.fusion.fida-wavelength-binning`(`bin_fida_los_components`):保存包 `FIDA权重谱线分箱` 的 `store_fw_photons_at_chan` 终端分箱边界——floor 分箱、半开区间 `[lambdamin,lambdamax)`、`1/(4*pi*dlambda)` 归一化因子、越界分量丢弃但保留原始 bin 下标(src/fidasim.f90:12297-12347)。

## 公共资产裁定(评审发现)

保存包把两叶封装在 `FIDA_LOS权重生产图`(physical_state → phase_weights,节点为 `FIDA视线物理状态聚合` 与 `FIDA LOS相位权重生产`)内。该图不移植:其节点绑定本批有意不整合的重型 CX/colrad/相位生产者,尚无组合边界可声明;两叶以普通 operator 进入,图级组合待相位生产者或第二个消费者出现再议。两叶按保存包打包保留为两个独立身份(域不同:分量波长表 vs 波长分箱轴)。

## 与现有基线的关系(对照结果)

- 基线无任何 Doppler/Stark/Zeeman 分量波长或 FIDA 波长分箱资产(`rg` 检索 src/tests/catalog 无命中);diagnostics 域的 JH Balmer-alpha 发射/反演关系涉及能级布居与发射系数,不涉及谱分量位置;colrad 资产推进状态、不产生波长。两项均记为 `add`。
- 组合证据:19 项直接测试中的两个 N5→N6 证人把 `doppler_stark_zeeman_wavelengths` 输出喂入 `bin_fida_los_components`(15 分量 Balmer-α 全窗内守恒;3 分量 Lyman-α 半开窗外部分量被丢弃且不影响其他 bin)。保存包 `FIDA_LOS权重生产图` 在相位生产者内部声明同一 N5→N6 交接。

## 源 quirk 逐字保留(回归钉定,非修复)

- 速度仅一次 cm/s→m/s 转换;视线内部归一化(缩放输入给出相同输出)。
- `E' = ||E + v x B||` 沿用保存臂的 y 分量符号约定;`q0/q1` 四周组合回旋与 Stark 项;位移相对 `lambda0`(非 `lambda_D`)求值。
- 零场零速时全部分量退化为同一 Doppler 中心(`q0=q1=0`);15 分量表只在有场时分离。
- 分箱为半开区间 floor 分箱;`lambdamax` 处分量映射到被丢弃的 bin `nlambda`(等价源 `bin > nlambda` 分支);越界分量保留原始计算下标(窗下为负)。

## 登记加固(各带判别回归)

1. 波长算子对全部向量/标量输入做有限值校验(保存臂在其文档宣称 fail closed 的同时静默传播 NaN/inf)。
2. 参考波长必须为正(保存臂接受零与负值)。
3. 标量模长拒绝布尔(保存臂把 `magnetic_magnitude_t=True` 数值化为 1.0 T)。
4. `component_count` 必须 genuine integer、接受 `np.integer`(保存臂 `not in (3,15)` 接受整值浮点如 `3.0`);拒绝布尔。
5. 分箱算子拒绝波长/强度数组中的布尔条目——bool dtype 与混合 object 形式(如 `np.asarray([True, 1.0], dtype=object)`)一并拒绝(保存臂 `np.asarray(..., dtype=float)` 把 `True` 静默数值化为 1.0,即 r79 合并家族闭合的同一缺口),并拒绝布尔窗口边界;保存臂自身的 `nlambda` genuine-integer 合同保留并以回归钉定。

## 组合证据

- 19 项直接测试(`tests/operator_contracts/test_fida_spectral_family.py`):两资产保存 probes、源 quirk 钉定、全部加固回归、以及两个 N5→N6 组合证人。
- 无独立复放文件:两叶均为包级 equation-oracle(`多普勒StarkZeeman谱线波长` 记录 `source_unavailable`,分箱记录 `independent bin oracle; no Fortran runtime parity claimed`),保存实现内容摘要逐资产记录于 exact documents 与 `build/test-evidence-r80.md`(参考记录,无自动漂移检测)。

## 相对 r79-v3 的增量

- r79-v3: 中性库合并家族,166 资产 dev56
- r80: FIDA 谱线分量族(2 operator),168 资产 dev57;版本 `0.1.0.dev56` → `0.1.0.dev57`
- 既有 166 份文档机械版本提升;`src/scirel/fusion/__init__.py` 追加两个纯公共导出

## 验证(全部为最终 pwsh 7+ 门禁实测回执,真实退出码已核;详见 `build/test-evidence-r80.md`)

- 源码态全仓(复放根激活):**1676 passed, 43 skipped, 0 failed**,exit code 0(r79-v3 全树 1657,+19)
- 文档校验源码态:**168/168**,`runtime_origin: source`,`examples_executed: true`,exit code 0
- 安装态(干净 venv build/venv-r75-clean,wheel `--no-index --no-deps` 安装):文档 **168/168**(`runtime_origin: installed`);全树 **1675 passed, 44 skipped, 0 failed**,exit code 0,junit 确认 0 errors;`scirel.__file__` 位于 venv 内
- catalog `build/catalog/r80`:`complete`,declared_total 168,root digest 见 test evidence
- 内部 wheel `scirel-0.1.0.dev57-py3-none-any.whl`,SHA-256 见 test evidence

## 审核范围:首次审核集合为全部 168 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r79-v3 的快照比较只作开发增量导航辅助。实测回执在冻结后记录于 post-freeze addendum(如有)。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:`fida_weights_los` 相位生产者(CX→colrad→Doppler/Stark/Zeeman→bin)、NPA 阶段 B 权重生产者(`NPA权重物理生产`)、三项 MPI 权重归约(NPA 五数组、主动 FIDA 双数组、中子三数组)、真实 HDF5 表驱动、MC marker 生产、并行(MPI 秩)reservoir 合并图、中性库生命周期
- 开放专家问题:(1) 波长算子沿用调用方参考波长与源的非相对论/四周组合近似,不宣称独立原子物理验证——该证据上限对未来可信版本是否可接受由专家裁定。(2) 保存臂的 equation-oracle 证据类别(两叶均无 Fortran runtime parity)原样继承。(3) 许可证状态均为 `pending-human-decision`
