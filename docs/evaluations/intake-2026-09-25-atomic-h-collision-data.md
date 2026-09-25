# KN1DPy 原子氢碰撞数据族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始、
来源纠正与结束均复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史
开发比较,不构成 SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-atomic-h-collision-data/review.md)
及其[比较清单](../../review_candidates/2026-09-25-atomic-h-collision-data/README.md)。

## 关系族选择

本轮是 r46 明确缓付的"电荷交换速率系数等叶节点"批次的兑现。按科学语义(输入、
模型、输出)对照当前 71 资产基线(`dbb4385`,r48)、52 个 Pleiades 单元及两个
附加快照的未发布候选池:无任何氢碰撞截面、速率系数或电离率资产,三个保存叶
均为**新增能力**;不按名称凑数。保留的区分:两 CX 叶是同一过程的姊妹拟合
(截面 vs 双变量速率系数),后者不是前者的 Maxwellian 平均——平均关系仍是
r41-r48 的 `maxwellian-relative-speed-rate-average`(组合测试验证截面叶可直接
作为其 `cross_section_m2` 端口);COLLRAD 叶是电子撞击过程与独立数据表。

来源树只读遵守:复放 import 一律 `python -B` 且显式 `PYTHONDONTWRITEBYTECODE=1`。
一轮早期探针曾在 COLLRAD 保存目录写入一个 `__pycache__` 字节码缓存(2026-09-26
01:00:59 +08:00),已按可恢复方式隔离至工作树
`build/quarantine/2026-09-26-collrad-saved-operator-pyc/`(含 record.md,记录
pyc SHA-256 `c1b099d36acc5a65f1cbf0796cee6b148d9bb0ab8cdbb8f71bf95407671cdbd5`);
移动前后保存 `scientific_operator.py` 的 SHA-256 均为
`2cd665e788e1444d60a4d7ca4b0e95fd76fd651b8a12653f7969aba8b9939bf1`,证明源文件
逐位未变;其余三个早期 pyc 未触碰,冻结来源无任何改写。

## 三项资产与有据修复

1. **`scirel.collisions.atomic-hydrogen-charge-exchange-cross-section`**
   (`evaluate_atomic_hydrogen_charge_exchange_cross_section`,源锚
   `KN1DPy/sigma/sigma_cx_h0.py:7-32`、`poly.py:3-10`,实现 SHA-256
   `af55e393c0e7510a0c1734eabc2a635374c1dfe2ec8dcc3ae87386772a80b099`):Janev
   九系数对数多项式 + Freeman–Jones 解析分支,双分支源裁剪逐位保留。两处修复
   (其文档均声明但实现未执行):负能量拒绝(保存实现静默裁剪入域)、分支选择器
   必须为标量(保存实现用 `np.any` 归约数组,其示例甚至传入数组)。
2. **`scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient`**
   (`evaluate_atomic_hydrogen_charge_exchange_rate`,源锚
   `KN1DPy/sigma/sigmav_cx_h0.py:8-95`,caller 证据
   `kinetic_h.py:1031-1044`、`kinetic_mesh.py:134`,实现 SHA-256
   `9a0037c238cc9fc99eabfa17984368d954c56ef9aa651e47967b5b1c273a1bfa`):9×9
   双变量对数多项式,源求和顺序(能量幂外层/温度幂内层)逐位保留。两处修复:
   非正温度与负能量拒绝(保存实现静默裁剪入域)。
3. **`scirel.collisions.collrad-h0-ionization-rate`**
   (`evaluate_collrad_h0_ionization_rate`,源锚
   `KN1DPy/collrad_sigmav_ion_h0.py:16-217`,门控 `kinetic_h.py:841-855`,
   实现 SHA-256 `2cd665e7…`):冻结 15×60 log(n)/log(T) 表的 log(rate) 双线性
   插值,端点裁剪与非降序配对坐标合同逐位保留。一处修复(其文档声明输出形状
   等于广播输入形状):要求两输入同形状、输出保持输入形状(保存实现一律展平为
   一维且只比展平尺寸,同尺寸异形数组被静默接受)。

COLLRAD 表转录质量:手工转录后经逐位数组比较发现 9 处差异(1 处为错行取值),
随即改为从保存文件机械抽取表行替换,复比 `np.array_equal` **逐位一致**;
源文件只读未动。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 双分支截面、速率系数与 COLLRAD 插值各有独立 oracle(`polyval2d`、几何均值
  中点、闭式重算),直接断言 rtol 1e-12/1e-15 与裁剪端点逐位相等。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,三个实现文件分别
  SHA-256 绑定):Janev/Freeman 分支、速率系数一维/二维网格、COLLRAD 一维扫掠
  与裁剪边缘全部 `assert_array_equal` **逐位复现**;四份修复差分见证(保存实现
  接受负能量/非正温度/数组选择器/异形同尺寸输入并展平,后继拒绝或保形)。
  16 passed。
- 组合链:截面叶直接作为 `average_cross_section_over_maxwellian` 的
  `cross_section_m2` 端口,产有限正速率。
- 保存包自身证据(ledger `ACCEPT_OPERATOR`、COLLRAD source-runtime 数据集验证
  9 分区 max_rel 1.45e-14、包级 oracle)作为有界历史对照引用。

## 开发验证(r49 当前状态)

- 失败回归先行:三份直接合同测试先 ImportError 失败(3 errors),实现后通过。
- 直接 + 复放 **37 passed**。
- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1059 passed,
  43 skipped**(较 r48 的 1013+52 新增 37 项测试,9 项门控复放真实运行);
  计数断言 71→74、`collisions.__all__` 断言更新,无既有数值断言弱化。
- 74/74 exact documents 源码态(`--check-runtime --execute-examples`)与
  干净离线安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净离线 venv(`include-system-site-packages=false`,`--no-index
  --find-links build/dependency-wheelhouse` 安装 numpy/scipy/pytest 后
  `--no-index --no-deps` 安装 wheel,`python -I` 执行):隔离探针确认 `scirel`
  解析到 venv site-packages;全套 tests 树 **1054 passed, 43 skipped,
  5 failed**——5 项失败均为环境绑定(`test_admitted_distribution_builder` 两项
  需嵌套 wheel 构建的旧准入构建器、`test_release_environment` 两项探测专用
  release python、`test_affected_test_selection` 的 git-unicode 分类依赖开发机
  git 编码),该 5 项在源码态全量门禁中全部通过,且与本轮三项资产无关;与
  r46/r48 的干净安装只跑 source-free 子集的做法一致。
- 内部 wheel `scirel-0.1.0.dev24-py3-none-any.whl`(SHA-256
  `a0c665a7d2920650fce832c448c49d4c866260daec0cba0102dd60e3e56c95a0`);开发
  catalog `complete: 74/74`,root digest
  `sha256:030f8a3704c5388e8d08d005ff8067129cb3f998926c37f7a9e0c5ce64974b90`。

## 边界与待决

- 本轮不宣称:合格 L1 消费、三个拟合或 COLLRAD 表对外部原子物理参考
  (AMJUEL/HYDHEL 等)的正确性、裁剪/非降序合同以外的适用域、调用方输入的
  物理有效性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(自适应网格、跨网格插值、分子 H2 全族、壁面/源序列、
  BoltzmannRHS 组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审说明见
  [r49 评审说明](review-version-2026-09-25-r49.md)。
