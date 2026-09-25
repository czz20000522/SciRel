# SciRel 弹性动量转移截面族整合 r53

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空,未消费任何合格 L1 输入。本版是 r52(`380cdb1a7f86f4b2690c9d05a380e16a4f06f758`,快照 `build/verification/review-2026-09-25-r52-evidence-correction`)的 successor;既有快照原样保留。

## 科学增量(五项新增资产,KN1DPy 弹性动量转移截面族)

r46/r49 缓付清单中的弹性动量转移截面族按证据兑现:五个氢粒子对(H–H、H⁺–H、H–H₂、H₂–H₂、H₂–H⁺)的独立截面拟合。对照 r52 基线与未发布候选池,五个保存叶均为新增能力;五者保持兄弟身份不合并,H–H 叶的粘性分支为源的不同量,H₂–H₂ 叶的同拟合回退为源声明行为。

1. **`scirel.collisions.atomic-hydrogen-elastic-cross-section`**(`evaluate_atomic_hydrogen_elastic_cross_section`):源锚 `sigma_el_h_h.py:19-38`(实现 SHA-256 `129bc8e2…`)。动量转移/粘性双分支,源裁剪逐位保留。修复:负能量拒绝;0-d 标量选择器要求(保存实现依赖 `bool()` 强转——静默接受 0-d/单元素数组、多元素数组抛通用 ambiguous 错误;该前提经实证探针修正)。
2. **`scirel.collisions.proton-atomic-hydrogen-elastic-cross-section`**(`evaluate_hydrogen_proton_elastic_cross_section`):源锚 `sigma_el_p_h.py:1-42`(实现 SHA-256 `b92dbb2a…`)。10 eV 断点分段拟合,源裁剪逐位保留。修复:负能量拒绝。断点严格取零与 `np.array([E])` 前导单元素轴作为声明源行为逐位保留,与保存文档样板句的矛盾作为专家评审问题。
3. **`scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section`**(`evaluate_hydrogen_h2_elastic_cross_section`):源锚 `sigma_el_h_hh.py:1-31`(实现 SHA-256 `4377ae23…`)。修复:负能量拒绝;前导轴包装矛盾同上。
4. **`scirel.collisions.molecular-hydrogen-elastic-cross-section`**(`evaluate_hydrogen2_hydrogen2_elastic_cross_section`):源锚 `sigma_el_hh_hh.py:1-31`(实现 SHA-256 `0c10fbb9…`)。保存实现自身的标量布尔/整数选择器验证与同拟合回退作为声明合同保留。修复:负能量拒绝。
5. **`scirel.collisions.proton-molecular-hydrogen-elastic-cross-section`**(`evaluate_hydrogen2_proton_elastic_cross_section`):源锚 `sigma_el_p_hh.py:1-31`(实现 SHA-256 `99ed2176…`)。修复:负能量拒绝。

## 科学证据

- 失败回归先行以显式序列证明:移除五个新模块 → 10 个新测试文件 10 errors ImportError;恢复 → 47 passed。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 8+6+5+6+6=31,复放 4+3+3+3+3=16,合计 47(r51/r52 计数教训落实)。
- 独立 oracle:闭式重算 rtol 1e-15;裁剪端点逐位相等;断点精确零、前导轴各秩保持、双分支分歧、回退恒等均断言。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,五个实现文件分别 SHA-256 绑定):`assert_array_equal` 逐位复现,含五份负能量修复差分见证与 H–H 选择器行为差分见证(含单元素数组被保存实现静默接受的实证)。
- 组合链:H–H 动量转移拟合直接喂 `average_cross_section_over_maxwellian`,产有限正速率。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1128 passed, 43 skipped**;计数断言 76→81、包级 `__all__` 更新,无既有数值断言弱化。
- 81/81 文档源码态与干净离线 venv 安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净离线 venv(fresh `build/venv-r53-clean`,wheelhouse 与 r31 记录逐哈希一致):r45 文档化 source-free 子集 **846 passed, 43 skipped, 0 failed**;全 tests 树 **1125 passed, 46 skipped, 0 failed**。
- 内部 wheel `scirel-0.1.0.dev26-py3-none-any.whl`,SHA-256 `93325e639f0171bf45b0e4c63fd6b94e165225cd8b1834bc21f54af603ad9fc7`;开发 catalog `complete: 81/81`,root digest `sha256:0a81e9d2121a5f7cb59bd6517860f21a73a3b46b022e1783240a513c1d69651e`。

## 边界与待决

- 不宣称:合格 L1 消费、五个拟合对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- H⁺–H/H–H₂ 前导轴包装与保存文档样板句的矛盾、H⁺–H 断点零为开放专家评审问题(候选文档第 2、3 项)。
- KN1DPy 其余叶节点(解离速率族、壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 81 项资产。
