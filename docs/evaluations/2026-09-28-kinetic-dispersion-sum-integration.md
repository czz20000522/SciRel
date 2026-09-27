# 有限谐波动理学色散张量开发整合记录

状态：已进入 SciRel 开发基线；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `11baa5e` 为基线，逐项对照 intake `647d5db` 的
`scirel.kinetic.kinetic-dispersion-sum`。公共科学合同在
[exact document](../../catalog/examples/scirel.kinetic.kinetic-dispersion-sum.json)。
其两个直接依赖 [解析等离子体色散函数](../../catalog/examples/scirel.kinetic.plasma-dispersion-function.json)
与 [Bessel-Gamma 项](../../catalog/examples/scirel.kinetic.bessel-gamma.json)
已经进入主仓，普通依赖仍为 DAG；本批不重绑来源 TaskGraph。

## 科学关系与边界

该算子在均匀 z 向磁场、实频率和 x-z 平面实波矢的约定下，
对每个 Maxwellian 物种求和 `n=-lmx..lmx` 谐波项，返回复介电
张量 `K`、减去 Maxwell curl 项的 `D`、`det(D)` 和派生尺度。
`f` 以 Hz、`Ts0` 以 K 输入，`kx` 与 `kz` 均不可为零；有限
`lmx` 是调用方选定的截断，不证明谐波收敛或模态根。
它与来源 `dielectric_tensor_diagnostic` 只有有界重叠：后者默认
`lmx=15`、允许复 `kx` 且非有限传播约定不同，不在本批合并。
现有冷等离子体张量也属于另一模型。

保存 fluidBW 算子使用 Weideman `N=64` 的 `Z` 近似，SciRel 使用
已合入的解析 `Z` 和缩放 Bessel-Gamma；有限点数值接近不构成逐位
等价。来源将 `lmx=1.5` 截断成 1，且 `kx=0` 会进入除零；
SciRel 对这些输入明确抛 `ValueError`，属于已声明的开发合同收紧。

## 来源与数值核对

只读核对 `D1待重审历史产物/fluidBW-e39cf9e7/operators/kinetic_dispersion_sum_n/scientific_operator.py`
的 SHA-256 为
`06c1cb9c6c3c61288afe3438ccea90c48d31fb72c6591af1b71f31a8580f075e`，
与 intake 锁定值一致。以 `python -B` 载入归档实现前，断言
`scirel.__file__` 位于本候选工作树 `src/`；没有写入归档。
一组分 `lmx=5`、一组分 `lmx=15`、两组分 `lmx=5` 的三个保存波点上，
`K`/`D` 逐元满足 `rtol=atol=1e-12`，行列式相对差分别为
`1.68259971967077e-15`、`2.597491330023073e-16` 和
`3.723324535126775e-15`。最大 `K` 绝对差分别为
`2.3137198024142196e-13`、`2.3137199853937286e-13` 和
`3.253907165344266e-11`；`D` 最大绝对差相同。
这些是有界回放，不证明任意频率/波矢上的来源等价、截断收敛、
根位置或物理模型选择。

## 合同缺口与修复

intake 原实现对正的极小密度 `ns0=1e-320` 返回有限张量和
`wps2=0`，违背 exact document 对等离子体频率平方严格为正的
输出合同。新回归先在原样实现上单独失败，旧数值断言 18 项通过；
随后仅在派生量门禁加入 `wps2<=0` 拒绝，19 项直接测试全部通过。
这不改变正常波点的谐波公式或既有数值断言。

fluidBW r6 保存产物因 `bonk/fDtensor.m` 的九个终端 `Kij` 和 `DD`
没有由任务图与 canonical/holdout 收据完整覆盖，位于待重审历史归档。
本地三点张量对照不能恢复项目级冻结资格。合格 D1 交付根在本批
核查时为空；许可证、科学身份、适用域和后续组合仍待专家审查。

## 本批验证

- `python -m pytest tests/operator_contracts/test_kinetic_dispersion_sum_n.py -q`：
  修复后 **19 passed**；来源行列式、九个张量分量与容差未弱化。
- 19 份 dev5 exact documents 的签名与示例通过 runtime 校验。
- 主仓 `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 11baa5e`：
  精确选择 5 个测试文件，**98 passed**，无全套回退。
- 主仓 `python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples`：
  19 份 exact documents 均通过，运行时签名和示例已检查。
- 主仓 `git diff --check 11baa5e..HEAD`：通过；科学关系和文档提交为
  `b4b4e92`，README 两处计数提交为 `3439229`。
