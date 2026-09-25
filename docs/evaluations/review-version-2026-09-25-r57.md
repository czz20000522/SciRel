# SciRel Johnson-Hinnov 系数 B 样条族整合 r57

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始时复核为空,未消费任何合格 L1 输入。本版是 r56(`93bb7cc`,快照 `build/verification/review-2026-09-25-r56-population-family`)的 successor;既有快照原样保留。

## 科学增量(三项新增资产,KN1DPy Johnson-Hinnov 系数 B 样条族)

对照 r56 基线与未发布候选池,保存包 `原子氢JH-r系数B样条评价` 的三个系数评价叶均为新增能力;三叶保持兄弟身份不合并(r 取显式 (n,2,5) 张量的 (ion, level) 切片、s 消费调用者密度、alpha 覆盖密度且输入不可变)。包内 Saha 关系已在 r56 整合,不重复添加。

1. **`scirel.collisions.hydrogen-jh-r-coefficient`**(`evaluate_h_jh_r_coefficient`):源锚 `jhr_coef.py:12-66` + `common/JH_Coef.py:5-29`(保存实现 SHA-256 `253cda22…b6344`,锚点取自保存包自身抽取记录)。显式载荷三次 B 样条,端点裁剪逐位保留。**无修复**;no_null=1 密度哨兵覆盖逐位保留为见证断言,开放专家问题。
2. **`scirel.collisions.hydrogen-jh-s-coefficient`**(`evaluate_h_jh_s_coefficient`):源锚 `jhs_coef.py:24-60`。载荷校验(精确字段集、order 4、77 系数节点几何)+ 消费密度的评价。**无修复**,逐位复现。
3. **`scirel.collisions.hydrogen-jh-alpha-coefficient`**(`evaluate_h_jh_alpha_coefficient`):源锚 `jhalpha_coef.py:10-64`。同上载荷校验 + 密度哨兵覆盖 + 输入不可变保证。**无修复**,逐位复现,开放专家问题。

## 科学证据

- 失败回归先行以显式序列证明:移除三个新模块 → 6 errors ImportError;恢复 → 30 passed。
- 逐文件测试计数以 `pytest --collect-only` 记录:18 direct + 12 replay = 30。
- 独立 oracle:同一样条的独立 FITPACK 路径重算(`RectBivariateSpline.ev`),rtol 1e-12;端点裁剪逐位相等;通道选择、密度依赖/无关、输入不可变见证独立断言。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,保存实现文件 SHA-256 绑定):打包载荷 r 全通道、s/alpha 一维与 12 点 profile `assert_array_equal` 逐位复现,拒绝行为双臂一致,s/alpha 密度语义分支分裂从保存实现读出并复现。
- 过程自纠:合成载荷 77 系数几何、oracle `ev` 标量提取、alpha 构造偏移、复放测试一维约束与小量级 witness,均记录于测试证据。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1271 passed, 43 skipped**;计数断言 93→96、包级 `__all__` 断言更新,无既有数值断言弱化。
- 96/96 文档源码态与干净离线 venv 安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过,均执行示例。
- 干净离线 venv(fresh `build/venv-r57-clean`):r45 文档化 source-free 子集 **989 passed, 43 skipped, 0 failed**;全 tests 树 **1268 passed, 46 skipped, 0 failed**。
- 内部 wheel `scirel-0.1.0.dev29-py3-none-any.whl`,SHA-256 `b6339384f0615923a9f4c8615bc9f86128245c4d8dbb4a6f314dc9cddf7dabc6`;开发 catalog `complete: 96/96`,root digest `sha256:39d13056f040ab462467d775601ea3a6916a2f83afece78343fc91ca5ff9f716`。

## 边界与待决

- 不宣称:合格 L1 消费、任何系数表对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- r/alpha 叶 no_null=1 密度哨兵覆盖为开放专家评审问题;两种载荷形式并存、系数数据资产准入、包内 Saha 域边界差异为候选文档待决项。
- KN1DPy 其余叶节点(辐射诊断组合批、壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 96 项资产。
