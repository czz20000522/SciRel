# SciRel 速度空间族合同反例修复 r47

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根仍为空,KN1DPy 保存包仅为 provisional 历史对照。本版是 r46(`23d1630fc6e5d973a81796ea2f14432e433b74ea`,快照 `build/verification/review-2026-09-25-r46-velocity-family`)的 successor;r46 原样保留。

## 合同反例与修复(监控方只读复核两项,均复现成立;另按同一类合同自查 seed 一项)

1. **负径向网格产生负测度**:`vr=[-2,-1]` 满足旧的"有限严格递增"输入约束却被接受,第二个径向单元测度为 `π(0.25−2.25) = −2π`、体积为负,与 exact document "finite and strictly positive" 输出承诺矛盾;保存包历史 operator.md 亦写明最终正径向速度约定。修复:**vr 域限制为非负**(径向速率轴;`vr[0] ≥ 0` 且严格递增时全部面非负、测度严格正),负节点按参数名拒绝。
2. **浮点上限溢出**:`vr=[1e308, 1.5e308]` 有限递增,但镜像 ghost 面 `2·vr[-1]−vr[-2]` 溢出为 inf、面的平方溢出,测度/体积出现 inf 与 `inf−inf = NaN`;axial ghost 同理(`vx[0]=−1.7e308`)。修复:全部浮点输出(测度、面、dvx、体积、ghost 系数、速度平方)计算后做可表示性检查,非有限即按 `ValueError("…not representable…")` 拒绝;溢出警告由 `errstate` 显式接管(与 Maxwellian 模块同一先例),不是只改文档掩盖无效网格。
3. **seed 同类可表示性核查(顺带,证据充分故一并修复)**:`tnorm_ev=1e308` 使 thermal speed 溢出为 inf(违反其 finite 输出承诺);`tnorm_ev=1e-300` 配 `shift=1e308` 使 `shift/vth` 溢出、raw exponent 为 `−inf`(违反 exponent 的 finite 约束,distribution 因 clamp 仍有限但不能带着坏 exponent 返回)。修复:thermal speed 与 raw exponent 各自计算后做可表示性检查,非有限即拒绝。未扩大到任何无根据的全局规则。

失败回归先行:5 项新回归先失败(负网格被接受、两个溢出 witness 返回非有限输出、seed 两个可表示性 witness),修复后通过;正网格的来源 parity 保持(双臂复放 9 passed 不变,复放网格全部为正)。普通正网格数值逐位不变。

## 验证

- `tests/operator_contracts/test_cylindrical_velocity_quadrature.py` + `test_shifted_maxwellian_seed.py`:**54 passed**(49 既有 + 5 新),无既有断言弱化;开发期发现 four-pi 计算位于 errstate 块外导致一条 RuntimeWarning 泄漏,已随本修复移入块内并重建 wheel。
- `check.ps1 -Mode full`(最终字节,源码态全仓):**1010 passed, 52 skipped**;71/71 文档源码态与干净离线 venv(`--no-index` wheelhouse,`python -I`)安装态校验通过;干净安装态 source-free 套件 **737 passed, 43 skipped**(L1 根已配置,复放真实运行)。
- 内部 wheel `scirel-0.1.0.dev22-py3-none-any.whl`,SHA-256 `92ceac03516e0c1ccca9d4aa624795f2a90cf6d242fe79162ea600fbbb1e642b`;开发 catalog `complete: 71/71`,root digest `sha256:7db0c7616626f571fc032fcec6fc573fd8740a26848f4a815abf4f75fe0f0a8c`。

## 边界

非负径向域是把保存源"最终正径向速度"约定显式化为输入合同;专家仍需裁决该约定及 ghost-face 约定对其他 scheme 的适用性。合格 L1 根仍为空,KN1DPy 仍为 provisional;许可证、可信晋级、公开发行未完成;无可信基线,首次专家审核仍覆盖全部 71 项。
