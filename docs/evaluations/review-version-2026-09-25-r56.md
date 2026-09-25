# SciRel 原子氢布居数据族整合 r56

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空,未消费任何合格 L1 输入。本版是 r55(`7222f2b584e368c7399182f6227117930005f9d8`,快照 `build/verification/review-2026-09-25-r55-index-paths`)的 successor;既有快照原样保留。

## 科学增量(三项新增资产,KN1DPy 原子氢布居数据族)

r46/r49 缓付的布居数据三叶按证据兑现。对照 r55 基线与未发布候选池,三个保存叶均为新增能力;三叶保持兄弟身份不合并(Janev 双物种枚举闭式调度、复合叶固定基态、Saha 叶为平衡布居非速率系数故归 `kinetic` 域)。

1. **`scirel.collisions.janev-electron-impact-ionization-rate-coefficient`**(`evaluate_janev_electron_impact_ionization_rate`):源锚 `sigmav_ion_h0.py:1-22` + `sigmav_ion_hh.py:1-27`(实现 SHA-256 `ff9b5f5c…`)。双物种 polyval 拟合,源裁剪逐位保留。修复:非正温度拒绝(保存实现折叠为一条通用错误并静默裁剪);物种枚举 {"H","H2"} 保留为声明合同。
2. **`scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient`**(`evaluate_atomic_hydrogen_1s_radiative_recombination_rate`):源锚 `sigmav_rec_h1s.py:3-25`(实现 SHA-256 `ad71a46c…`)。Storey 型解析式,冻结常数逐位保留。修复:非正温度拒绝。
3. **`scirel.kinetic.hydrogen-saha-equilibrium-population`**(`evaluate_h_saha_equilibrium_population`):源锚 `nh_saha.py:25-46`(实现 SHA-256 `38fa28ac…`)。Saha 闭式,科学分支独占、1-D 配对样本、能级整数 ≥1。**无修复**——保存实现已完整执行其声明合同;其文档样板("标量或 profile 数组")与实现一维合同的矛盾作为专家评审问题。

## 科学证据

- 失败回归先行以显式序列证明:移除三个新模块 → 6 errors ImportError;恢复 → 32 passed。
- 逐文件测试计数以 `pytest --collect-only` 记录:21 direct + 11 replay = 32。
- 独立 oracle:polyval 同表重算、闭式同常数重算,rtol 1e-12/1e-15;裁剪端点逐位相等;物种分歧与能级标度对照闭式断言。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,三个实现文件分别 SHA-256 绑定):`assert_array_equal` 逐位复现,含两份非正温度修复差分见证与 Saha 拒绝行为一致见证。
- 过程自纠:草拟的 Saha 单调性断言与实测相反(冷输入下指数因子压制能级 2),改为断言 oracle 等式;记录于候选文档。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1241 passed, 43 skipped**;计数断言 90→93、包级 `__all__` 更新,无既有数值断言弱化。
- 93/93 文档源码态与干净离线 venv 安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净离线 venv(fresh `build/venv-r56-clean`,wheelhouse 与 r31 记录逐哈希一致):r45 文档化 source-free 子集 **959 passed, 43 skipped, 0 failed**;全 tests 树 **1238 passed, 46 skipped, 0 failed**。
- 内部 wheel `scirel-0.1.0.dev28-py3-none-any.whl`,SHA-256 `a27256b7320dc99f34fac7b919360241469cbb29be1b418817db28f2dd842704`;开发 catalog `complete: 93/93`,root digest `sha256:44a7b60ef848bce205e31394deddb93bdfef394cf8882a97d11646a86f4e26cf`。

## 边界与待决

- 不宣称:合格 L1 消费、三个关系对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- Saha 叶一维合同与文档样板句的矛盾为开放专家评审问题。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 93 项资产。
