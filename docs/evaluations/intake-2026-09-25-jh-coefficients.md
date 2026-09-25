# KN1DPy Johnson-Hinnov 系数 B 样条族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始时
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-jh-coefficients/review.md)及其
[比较清单](../../review_candidates/2026-09-25-jh-coefficients/README.md)。

## 关系族选择

本批次整合保存包 `原子氢JH-r系数B样条评价` 中的三个系数评价叶(r53-r56 各批
次缓存付清单之外的同包剩余叶)。对照 r56 基线(`93bb7cc`,93 资产 dev28)与
未发布候选池:基线与池中均无"调用者提供 B 样条载荷的系数评价"类资产(最近
邻为 Maxwellian 相对速度平均、Bosch-Hale 解析反应率、r56 闭式布居叶,均不同
关系),三个保存叶均为**新增能力**;按科学语义判重,不按名称。三叶保持兄弟
身份不合并:r 取显式 (n,2,5) 张量的 (ion, level) 切片并在 no_null=1 分支用源
1e32 哨兵覆盖密度;s 消费调用者密度(分支分裂见证在两臂上断言);alpha 用自
己的系数向量、覆盖密度且保证输入不可变。包内 Saha 关系已在 r56 整合为
`scirel.kinetic.hydrogen-saha-equilibrium-population`,不重复添加;包内 Saha
副本(仅正有限)与已整合资产(正有限且 <1e32)的域边界差异已为辐射后续批
次记录。辐射诊断(Lyman/Balmer/逆诊断)与载荷生产器**缓付**:前者组合已整
合 Saha 资产与本批系数,适合作为组合批次单独评审;后者物化打包系数数据,准
入系数数据资产是独立的专家决定。来源树只读:全部导入 `python -B` 且显式
`PYTHONDONTWRITEBYTECODE=1`,本轮对保存树零写入。

源锚(`jhr_coef.py:12-66`、`jhs_coef.py:24-60`、`jhalpha_coef.py:10-64`、
`common/JH_Coef.py:5-29`)取自保存包自身抽取记录,未重读原始源码树;保存实
现文件 SHA-256 `253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344`。

## 三项资产(全部无修复)

1. **`scirel.collisions.hydrogen-jh-r-coefficient`**
   (`evaluate_h_jh_r_coefficient`):显式载荷三次 B 样条,端点裁剪逐位保留;
   no_null=1 密度哨兵覆盖行为逐位保留并作为见证断言,**开放专家问题**记录。
2. **`scirel.collisions.hydrogen-jh-s-coefficient`**
   (`evaluate_h_jh_s_coefficient`):载荷校验(精确字段集、order 4、77 系数
   节点几何)+ 消费调用者密度的评价,逐位复现。
3. **`scirel.collisions.hydrogen-jh-alpha-coefficient`**
   (`evaluate_h_jh_alpha_coefficient`):同上载荷校验 + 密度哨兵覆盖 + 输入
   不可变保证,逐位复现,**开放专家问题**记录。

与 r56 速率叶不同,本批**无修复**:三个保存 formal 实现均已完整执行其声明
合同(错误消息逐字保留)。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 失败回归先行以显式序列证明:移除三个新模块后 6 个新测试文件收集期
  **6 errors ImportError**,恢复后 **30 passed**。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 7+5+6=18,复放
  4+4+4=12,合计 30。
- 独立 oracle:同一样条的独立 FITPACK 路径重算(`RectBivariateSpline.ev`,
  非 `bisplev`),rtol 1e-12;端点裁剪落到端点值逐位相等;r 的 ion/level 通
  道选择、s 的密度依赖、r/alpha 的密度无关与输入不可变见证均独立断言。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,保存实现文件
  SHA-256 绑定):打包系数载荷上 r 全部 (ion, level) 通道、s/alpha 一维与
  12 点 profile 全部 `assert_array_equal` **逐位复现**;拒绝行为(no_null、
  能级域、物种/形状/载荷缺陷)双臂一致见证;s 消费密度 / alpha 不消费的
  分支分裂见证直接从保存实现读出并复现。
- 过程自纠三处,均发生在门禁运行前:合成载荷轴点数最初不满足 77 系数几何
  (改 11×7 轴);oracle 中 `RectBivariateSpline.ev` 在本 scipy 版本返回形状
  (1,) 数组(改显式取标量);alpha oracle 漏加构造偏移 0.25(补上,注释说
  明 B 样条对系数线性)。另修正复放测试自身两处:保存臂仅接受一维(去掉二
  维 reshape),小量级 witness 改 `array_equal`。

## 开发验证(r57 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1271 passed,
  43 skipped**;计数断言 93→96、包级 `__all__` 断言更新,无既有数值断言弱化。
- 96/96 exact documents 源码态校验通过(`--check-runtime --execute-examples`,
  `runtime_origin: source`,`examples_executed: true`)。
- 内部 wheel `scirel-0.1.0.dev29-py3-none-any.whl`(SHA-256
  `b6339384f0615923a9f4c8615bc9f86128245c4d8dbb4a6f314dc9cddf7dabc6`);开发
  catalog `complete: 96/96`,root digest
  `sha256:39d13056f040ab462467d775601ea3a6916a2f83afece78343fc91ca5ff9f716`。
- 干净离线 venv(fresh `build/venv-r57-clean`,`--no-index --no-deps
  --force-reinstall` 安装 wheel,`python -I` 隔离探针确认 `scirel` 解析到
  venv site-packages):r45 文档化 source-free 子集 **989 passed, 43 skipped,
  0 failed**;全 tests 树 **1268 passed, 46 skipped, 0 failed**;安装态文档校
  验 **96/96** 通过(`runtime_origin: installed`,`examples_executed: true`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、任何系数表对外部原子物理参考的正确性
  (`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、
  可信晋级或公开发行。
- r/alpha 叶的 no_null=1 密度哨兵覆盖是否为预期发布合同(或应由后继修复为
  消费密度)为开放专家评审问题(候选文档第 1 项)。
- 两种载荷形式(显式张量 vs 整载荷 mapping)并存、系数数据资产准入、包内
  Saha 域边界差异的调和,均为候选文档待决项。
- KN1DPy 其余叶节点(辐射诊断组合批、壁面/源序列、自适应网格、跨网格插值、
  BoltzmannRHS 组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审说明见
  [r57 评审说明](review-version-2026-09-25-r57.md)。
