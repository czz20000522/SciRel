# KN1DPy 分子氢电荷交换对开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-h2-collision-data/review.md)及其
[比较清单](../../review_candidates/2026-09-25-h2-collision-data/README.md)。

## 关系族选择

本批次继续兑现 r46/r49 缓付的"分子 H2 全族"中最有直接证据的两叶。对照 r50 基线
(`8b8dd15`,74 资产 dev24)与未发布候选池:无任何分子氢碰撞资产,两个保存叶均为
**新增能力**;按科学语义(输入、模型、输出)判重,不按名称。保留的区分:两 H2 叶
是同一过程的姊妹拟合(截面 vs 双变量速率系数),后者不是前者的 Maxwellian 平均
——平均关系仍是 r41 的 `maxwellian-relative-speed-rate-average`(组合测试验证
分子截面叶可直接作为其 `cross_section_m2` 端口);分子拟合与 r49 原子拟合是不同
物理系统,两个方向的数值分歧在测试中断言(共享能量网格上分子/原子截面、分子/
原子速率系数均不 allclose)。来源树只读:全部导入 `python -B` 且显式
`PYTHONDONTWRITEBYTECODE=1`,本轮对保存树零写入。

## 两项资产与有据修复

1. **`scirel.collisions.molecular-hydrogen-charge-exchange-cross-section`**
   (`evaluate_molecular_hydrogen_charge_exchange_cross_section`,源锚
   `KN1DPy/sigma/sigma_cx_hh.py:5-23`、`KN1DPy/sigma/poly.py:3-10`,caller 证据
   `kinetic_h2.py:1036-1049`,实现 SHA-256
   `2be195e5393454e78a728eee8de53a12974865ad3fef470b8566b61ff3806a5f`):Janev
   九系数对数多项式,源裁剪 [0.1, 2.01e4] eV 逐位保留。一处修复(其文档声明
   而实现未执行):负能量拒绝(保存实现静默裁剪入域)。
2. **`scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient`**
   (`evaluate_hydrogen2_charge_exchange_rate`,源锚
   `KN1DPy/sigma/sigmav_cx_hh.py:5-95`,ledger N15 `EQ-N15-H2-CX-RATE`,caller
   证据 `kinetic_h2.py:1196-1206`、`kinetic_mesh.py:137`,实现 SHA-256
   `8ca54201138f6d1d19803e2bfb042b80980b2a9367bad36d53eafccdfc6bfd22`):9×9
   双变量对数多项式,源求和顺序逐位保留。两处修复:非正温度与负能量拒绝。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 失败回归先行以显式序列证明:移除两个新模块后 4 个新测试文件收集期
  **4 errors ImportError**,恢复后 **22 passed**。
- 独立 oracle:闭式重算(截面)、`polyval2d`(速率),rtol 1e-15/1e-12;裁剪端点
  逐位相等;双极端角由 SHA 绑定复放逐位钉死(原子族 r49 记录的求和序抵消同样
  适用于速率拟合,oracle 测试避开该角)。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,两个实现文件分别
  SHA-256 绑定):一维/二维网格全部 `assert_array_equal` **逐位复现**;三份修复
  差分见证(保存实现接受负能量/非正温度并裁剪入域,后继拒绝)。7 passed。
- 组合链:分子截面叶直接作为 `average_cross_section_over_maxwellian` 的
  `cross_section_m2` 端口(m=2 靶),产有限正速率。
- 原子/分子区分断言:共享网格上两个截面拟合、两个速率拟合互不 allclose。
- 保存包自身证据(ledger `ACCEPT_OPERATOR` ×2、N15 source-only dataset 注记)
  作为有界历史对照引用。

## 开发验证(r51 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1081 passed,
  43 skipped**;计数断言 74→76、包级 `__all__` 更新,无既有数值断言弱化。
  (过程更正:计数曾误写 77,由 `complete coverage requires every declared
  asset` 门禁当场拦截后更正为 76。)
- 76/76 exact documents 源码态校验通过。
- 内部 wheel `scirel-0.1.0.dev25-py3-none-any.whl`(SHA-256
  `a3b72aee1d01021e8cbee6005a3ed5c620ded553ac318b1f54fc4d74ef782ee1`);开发
  catalog `complete: 76/76`,root digest
  `sha256:9b87786685adea5d120a4616c74d44a607f9bc1d8c4e5fe3a0edf8d98a26953e`。
- 干净离线 venv(fresh `build/venv-r51-clean`,`--no-index` wheelhouse 与 r31
  记录逐哈希一致,`--no-index --no-deps --force-reinstall` 安装 wheel,
  `python -I` 隔离探针确认 `scirel` 解析到 venv site-packages):
  r45 文档化 source-free 子集 **799 passed, 43 skipped, 0 failed**;全 tests 树
  **1078 passed, 46 skipped, 0 failed**(46 = 43 环境门控 + 2 setuptools 命名
  阻塞 skip + 1 源码守卫 skip,r50 修复沿用);安装态文档校验 **76/76** 通过
  (`runtime_origin: installed`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、两个拟合对外部原子物理参考(AMJUEL/HYDHEL 等)的
  正确性、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(分子弹性动量转移截面、解离速率族、壁面/源序列、自适应
  网格、跨网格插值、BoltzmannRHS 组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的四项问题见候选文档;冻结待审说明见
  [r51 评审说明](review-version-2026-09-25-r51.md)。
