# SciRel 解离速率族整合 r54

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空,未消费任何合格 L1 输入。本版是 r53(`e3f2ebe559e57e35eff2e23170211377db24b0a8`,快照 `build/verification/review-2026-09-25-r53-elastic-cross-sections`)的 successor;既有快照原样保留。

## 科学增量(九项新增资产,KN1DPy 解离速率族)

r46/r49 缓付的解离速率族按证据兑现:氢分子与其离子的九个电子碰撞通道速率。对照 r53 基线与未发布候选池,九个保存叶均为新增能力;九叶保持兄弟身份不合并(每通道是物理上不同的速率,各有独立冻结系数表)。

1. **资产 82–86(H₂ 电子碰撞解离五叶)**:`scirel.collisions.h2-dissociation-h1s-h1s-rate-coefficient`、`…h1s-h2s…`、`…h1s-hn3…`、`…h2p-h2s…`、`…p-h1s…`(callables `evaluate_hydrogen2_*_dissociation_rate`),源锚 `sigmav_h1s_h1s_hh.py:5-27` 等,caller `kinetic_h2.py:938-993`。
2. **资产 87–90(H₂⁺ 电子碰撞四叶)**:`scirel.collisions.h2-plus-two-proton-dissociation-rate-coefficient`、`…p-h1s…`、`…p-hn2…`、`…h1s-hn-dissociative-recombination-rate-coefficient`,源锚 `sigmav_p_h1s_hp.py:5-35` 等;双质子叶锚 `kinetic_h2.py:977-983`。

统一关系形状:temperature-only 九系数对数多项式,源 Horner 求和序、裁剪 [0.1, 2.01e4] eV、×1e-6 逐位保留。统一修复(各保存文档声明而实现未执行):**非正温度拒绝**。生成方式:共享模板 + 系数 `repr(float(v))` 位精确往返抽取(规避 COLLRAD 转录错误类),四个生成器脚本纳入 proposal 供审计。

## 科学证据

- 失败回归先行以显式序列证明:移除九个新模块 → 18 个新测试文件 18 errors ImportError;恢复 → 81 passed。
- 逐文件测试计数以 `pytest --collect-only` 记录:54 direct + 27 replay = 81。
- 独立 oracle:polyval 同表重算 rtol 1e-12;裁剪端点逐位相等。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,九个实现文件分别 SHA-256 绑定):`assert_array_equal` 逐位复现,含九份非正温度修复差分见证。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1209 passed, 43 skipped**;计数断言 81→90、包级 `__all__` 更新,无既有数值断言弱化。
- 90/90 文档源码态与干净离线 venv 安装态(`--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净离线 venv(fresh `build/venv-r54-clean`,wheelhouse 与 r31 记录逐哈希一致):r45 文档化 source-free 子集 **927 passed, 43 skipped, 0 failed**;全 tests 树 **1206 passed, 46 skipped, 0 failed**。
- 内部 wheel `scirel-0.1.0.dev27-py3-none-any.whl`,SHA-256 `7768b32bbc95bb0b36604bde6d89fd0543deaf656d906d1f2b765f6ce7b00e03`;开发 catalog `complete: 90/90`,root digest `sha256:2399fdbcae4fc8c7e6b0147d964548d3e1556a4803317c21401194e05b99d344`。

## 边界与待决

- 不宣称:合格 L1 消费、九个拟合对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 90 项资产。
