# SciRel 分子氢电荷交换对整合 r51

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空,未消费任何合格 L1 输入。本版是 r50(`8b8dd150fe5778da8bd88fdf9c66b05c37f2c954`,快照 `build/verification/review-2026-09-25-r50-installed-runtime`)的 successor;既有快照原样保留。

## 科学增量(两项新增资产,KN1DPy 分子氢电荷交换对)

r46/r49 缓付的"分子 H2 全族"中最有直接证据的两叶按证据兑现。对照 r50 基线与未发布候选池,两个保存叶均为新增能力;两叶保持姊妹关系不合并(速率系数拟合不是截面的 Maxwellian 平均,平均关系仍由 r41 资产承担,组合测试覆盖分子截面叶作为其 `cross_section_m2` 端口);分子拟合与 r49 原子拟合是不同物理系统,两个方向的数值分歧在测试中断言。

1. **`scirel.collisions.molecular-hydrogen-charge-exchange-cross-section`**(`evaluate_molecular_hydrogen_charge_exchange_cross_section`):源锚 `KN1DPy/sigma/sigma_cx_hh.py:5-23`(实现 SHA-256 `2be195e5393454e78a728eee8de53a12974865ad3fef470b8566b61ff3806a5f`)。Janev 九系数对数多项式,源裁剪逐位保留。修复:负能量拒绝(保存文档声明而实现未执行)。
2. **`scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient`**(`evaluate_hydrogen2_charge_exchange_rate`):源锚 `KN1DPy/sigma/sigmav_cx_hh.py:5-95`(实现 SHA-256 `8ca54201138f6d1d19803e2bfb042b80980b2a9367bad36d53eafccdfc6bfd22`,ledger N15)。9×9 双变量对数多项式,源求和顺序逐位保留。修复:非正温度与负能量拒绝。

## 科学证据

- 失败回归先行以显式序列证明:移除两个新模块 → 4 个新测试文件 4 errors ImportError;恢复 → 22 passed。
- 独立 oracle:闭式重算(截面)、`polyval2d`(速率),rtol 1e-15/1e-12;裁剪端点逐位相等;双极端角由 SHA 绑定复放逐位钉死。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,两个实现文件分别 SHA-256 绑定):一维/二维网格全部 `assert_array_equal` 逐位复现,含三份修复差分见证;7 passed。
- 组合链与原子/分子区分断言(共享网格互不 allclose)均覆盖。
- 保存包 ledger `ACCEPT_OPERATOR` ×2 作为有界历史对照。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1081 passed, 43 skipped**;计数断言 74→76、包级 `__all__` 更新,无既有数值断言弱化。过程更正:计数曾误写 77,由 `complete coverage requires every declared asset` 门禁当场拦截后更正。
- 76/76 文档源码态与干净离线 venv 安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净离线 venv(fresh `build/venv-r51-clean`,wheelhouse 与 r31 记录逐哈希一致):r45 文档化 source-free 子集 **799 passed, 43 skipped, 0 failed**;全 tests 树 **1078 passed, 46 skipped, 0 failed**(46 = 43 环境门控 + 2 setuptools 命名阻塞 skip + 1 源码守卫 skip,r50 修复沿用)。
- 内部 wheel `scirel-0.1.0.dev25-py3-none-any.whl`,SHA-256 `a3b72aee1d01021e8cbee6005a3ed5c620ded553ac318b1f54fc4d74ef782ee1`;开发 catalog `complete: 76/76`,root digest `sha256:9b87786685adea5d120a4616c74d44a607f9bc1d8c4e5fe3a0edf8d98a26953e`。

## 边界与待决

- 不宣称:合格 L1 消费、两个拟合对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(分子弹性动量转移截面、解离速率族、壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 76 项资产。
