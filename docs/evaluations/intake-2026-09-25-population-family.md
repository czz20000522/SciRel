# KN1DPy 原子氢布居数据族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-population-family/review.md)及其
[比较清单](../../review_candidates/2026-09-25-population-family/README.md)。

## 关系族选择

本批次继续兑现 r46/r49 缓付清单中的原子氢布居数据三叶。对照 r55 基线
(`7222f2b`,90 资产 dev27)与未发布候选池:无任何 temperature-only 电离率、辐射
复合率或平衡布居资产(r49 的 COLLRAD 是密度依赖的 H0 电离表,不同关系),三个
保存叶均为**新增能力**;按科学语义判重,不按名称。保留的区分:Janev 叶是闭式
双物种枚举调度(H/H2 两物理系统,数值分歧已断言);复合叶固定基态 n=1 与自身
冻结常数;Saha 叶是平衡布居(m^-3)而非速率系数,按科学领域归入 `kinetic` 域。
来源树只读:全部导入 `python -B` 且显式 `PYTHONDONTWRITEBYTECODE=1`,本轮对
保存树零写入。

## 三项资产与有据修复

1. **`scirel.collisions.janev-electron-impact-ionization-rate-coefficient`**
   (`evaluate_janev_electron_impact_ionization_rate`,源锚
   `sigmav_ion_h0.py:1-22` + `sigmav_ion_hh.py:1-27`,实现 SHA-256
   `ff9b5f5c…e3d1`):双物种九系数 polyval 拟合,源裁剪 [0.1, 2.01e4] eV 逐位
   保留。修复:非正温度拒绝(保存实现把温度与物种检查折叠为一条通用错误并
   静默裁剪入域);物种枚举 {"H","H2"} 作为声明合同保留。
2. **`scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient`**
   (`evaluate_atomic_hydrogen_1s_radiative_recombination_rate`,源锚
   `sigmav_rec_h1s.py:3-25`,caller `kinetic_h.py:862,867-881`,实现 SHA-256
   `ad71a46c…2528`):Storey 型解析式,冻结常数(Ry=13.58 eV、A_nl=3.92、
   x_nl=0.35、n=1)逐位保留。修复:非正温度拒绝。
3. **`scirel.kinetic.hydrogen-saha-equilibrium-population`**
   (`evaluate_h_saha_equilibrium_population`,源锚 `nh_saha.py:25-46`,实现
   SHA-256 `38fa28ac…e89c`):Saha 闭式(冻结常数 3.310e-28、13.6057 eV),
   1-D 配对样本、科学分支独占(源 1e32 哨兵值按合同不可达)、标量整数能级
   ≥1。**无修复**——保存实现已完整执行其声明合同,位逐位复现;其文档样板
   ("标量或 profile 数组")宽于实现的一维合同,矛盾作为专家评审问题记录。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 失败回归先行以显式序列证明:移除三个新模块后 6 个新测试文件收集期
  **6 errors ImportError**,恢复后 **32 passed**。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 8+6+7=21,复放 4+3+4=11,
  合计 32。
- 独立 oracle:polyval 同表重算(电离)、闭式同常数重算(复合与 Saha),
  rtol 1e-12/1e-15;裁剪端点逐位相等;物种分歧、能级标度均对照闭式断言。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,三个实现文件分别
  SHA-256 绑定):一维/二维网格全部 `assert_array_equal` **逐位复现**;两份
  非正温度修复差分见证 + Saha 拒绝行为精确一致见证。11 passed。
- 过程自纠一处:草拟的 Saha 断言猜测冷输入下能级 2 布居高于能级 1,实测
  相反(指数因子压制),直接测试与 exact document 示例均改写为断言 oracle
  等式而非错误单调性猜测。

## 开发验证(r56 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1241 passed,
  43 skipped**;计数断言 90→93、包级 `__all__` 更新,无既有数值断言弱化。
- 93/93 exact documents 源码态校验通过。
- 内部 wheel `scirel-0.1.0.dev28-py3-none-any.whl`(SHA-256
  `a27256b7320dc99f34fac7b919360241469cbb29be1b418817db28f2dd842704`);开发
  catalog `complete: 93/93`,root digest
  `sha256:44a7b60ef848bce205e31394deddb93bdfef394cf8882a97d11646a86f4e26cf`。
- 干净离线 venv(fresh `build/venv-r56-clean`,wheelhouse 与 r31 记录逐哈希
  一致,`--no-index --no-deps --force-reinstall` 安装 wheel,`python -I` 隔离
  探针确认 `scirel` 解析到 venv site-packages):r45 文档化 source-free 子集
  **959 passed, 43 skipped, 0 failed**;全 tests 树 **1238 passed, 46 skipped,
  0 failed**;安装态文档校验 **93/93** 通过(`runtime_origin: installed`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、三个关系对外部原子物理参考(AMJUEL/HYDHEL、
  Janev-Smith、Storey 原始表等)的正确性(`validation_oracle_gap` 残余原样
  保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- Saha 叶的一维合同与保存文档样板句的矛盾为开放专家评审问题(候选文档第 3 项)。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS
  组装、SIG 矩阵组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审说明见
  [r56 评审说明](review-version-2026-09-25-r56.md)。
