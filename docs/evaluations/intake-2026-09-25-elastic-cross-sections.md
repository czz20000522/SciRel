# KN1DPy 弹性动量转移截面族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-elastic-cross-sections/review.md)及其
[比较清单](../../review_candidates/2026-09-25-elastic-cross-sections/README.md)。

## 关系族选择

本批次继续兑现 r46/r49 缓付清单中的弹性动量转移截面族:五个不同氢粒子对
(H–H、H⁺–H、H–H₂、H₂–H₂、H₂–H⁺)的独立截面拟合。对照 r52 基线
(`380cdb1`,76 资产 dev25)与未发布候选池:无任何弹性截面资产,五个保存叶均为
**新增能力**;按科学语义(输入、模型、输出)判重,不按名称。保留的区分:五个资产
保持五元组兄弟身份不合并;H–H 叶的粘性分支是源的不同量(独立系数集),不是动量
转移拟合的参数化;H₂–H₂ 叶的 `viscosity` 选择器是源文档化的同拟合回退,非第二
拟合。五个截面均可直接作为 r41 Maxwellian 速率平均的 `cross_section_m2` 端口
(组合测试覆盖 H–H 叶)。来源树只读:全部导入 `python -B` 且显式
`PYTHONDONTWRITEBYTECODE=1`,本轮对保存树零写入。

## 五项资产与有据修复

1. **`scirel.collisions.atomic-hydrogen-elastic-cross-section`**
   (`evaluate_atomic_hydrogen_elastic_cross_section`,源锚
   `sigma_el_h_h.py:19-38`,caller `kinetic_h.py:957`,实现 SHA-256
   `129bc8e2…`):动量转移/粘性双分支拟合,源裁剪 [0.03, 1.01e4] eV 逐位保留。
   修复:负能量拒绝;选择器须为 0-d 标量(保存实现依赖 `bool()` 强转,静默接受
   0-d/单元素数组、多元素数组抛 NumPy 通用 ambiguous 错误——该前提经实证探针
   修正,初始"np.any 归约"假设错误)。
2. **`scirel.collisions.proton-atomic-hydrogen-elastic-cross-section`**
   (`evaluate_hydrogen_proton_elastic_cross_section`,源锚
   `sigma_el_p_h.py:1-42`,caller `kinetic_h.py:996-1016`,实现 SHA-256
   `b92dbb2a…`):10 eV 断点分段拟合,源裁剪 [0.001, 1.01e5] eV。修复:负能量
   拒绝。断点严格取零与 `np.array([E])` 前导单元素轴作为声明的源行为逐位保留,
   其与保存文档样板输出形状句的矛盾作为专家评审问题记录。
3. **`scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section`**
   (`evaluate_hydrogen_h2_elastic_cross_section`,源锚
   `sigma_el_h_hh.py:1-31`,caller `kinetic_h.py:970-984`,实现 SHA-256
   `4377ae23…`):单拟合 + 前导轴包装。修复:负能量拒绝;包装矛盾同上。
4. **`scirel.collisions.molecular-hydrogen-elastic-cross-section`**
   (`evaluate_hydrogen2_hydrogen2_elastic_cross_section`,源锚
   `sigma_el_hh_hh.py:1-31`,caller `kinetic_h2.py:1099-1125`,实现 SHA-256
   `0c10fbb9…`):单拟合;保存实现自身的标量布尔/整数选择器验证与同拟合回退
   作为声明合同保留。修复:负能量拒绝。
5. **`scirel.collisions.proton-molecular-hydrogen-elastic-cross-section`**
   (`evaluate_hydrogen2_proton_elastic_cross_section`,源锚
   `sigma_el_p_hh.py:1-31`,caller `kinetic_h2.py:1070-1093`,实现 SHA-256
   `99ed2176…`):单拟合。修复:负能量拒绝。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 失败回归先行以显式序列证明:移除五个新模块后 10 个新测试文件收集期
  **10 errors ImportError**,恢复后 **47 passed**。
- 逐文件测试计数以 `pytest --collect-only` 记录(本轮起候选文档计数一律取自
  collection,r51/r52 的计数教训):直接 8+6+5+6+6=31,复放 4+3+3+3+3=16,
  合计 47。
- 独立 oracle:各拟合的闭式重算(双分支、分段),rtol 1e-15;裁剪端点逐位相等;
  H⁺–H 断点精确零、前导轴各秩保持、H–H 双分支分歧、H₂–H₂ 回退恒等均断言。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,五个实现文件分别
  SHA-256 绑定):一维/二维网格全部 `assert_array_equal` **逐位复现**;五份
  负能量修复差分见证 + H–H 选择器行为差分见证(含单元素数组被保存实现静默
  接受的实证)。
- 组合链:H–H 动量转移拟合直接作为 `average_cross_section_over_maxwellian`
  的 `cross_section_m2` 端口,产有限正速率。
- 保存包自身证据(各 operator.md 源锚、包级测试)作为有界历史对照引用。

## 开发验证(r53 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1128 passed,
  43 skipped**;计数断言 76→81、包级 `__all__` 更新,无既有数值断言弱化。
- 81/81 exact documents 源码态校验通过。
- 内部 wheel `scirel-0.1.0.dev26-py3-none-any.whl`(SHA-256
  `93325e639f0171bf45b0e4c63fd6b94e165225cd8b1834bc21f54af603ad9fc7`);开发
  catalog `complete: 81/81`,root digest
  `sha256:0a81e9d2121a5f7cb59bd6517860f21a73a3b46b022e1783240a513c1d69651e`。
- 干净离线 venv(fresh `build/venv-r53-clean`,wheelhouse 与 r31 记录逐哈希
  一致,`--no-index --no-deps --force-reinstall` 安装 wheel,`python -I` 隔离
  探针确认 `scirel` 解析到 venv site-packages):r45 文档化 source-free 子集
  **846 passed, 43 skipped, 0 failed**;全 tests 树 **1125 passed, 46 skipped,
  0 failed**;安装态文档校验 **81/81** 通过(`runtime_origin: installed`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、五个拟合对外部原子物理参考的正确性
  (`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、
  可信晋级或公开发行。
- H⁺–H/H–H₂ 的前导轴包装与保存文档样板句的矛盾、H⁺–H 断点零为开放专家评审
  问题(候选文档第 2、3 项)。
- KN1DPy 其余叶节点(解离速率族、壁面/源序列、自适应网格、跨网格插值、
  BoltzmannRHS 组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审说明见
  [r53 评审说明](review-version-2026-09-25-r53.md)。
