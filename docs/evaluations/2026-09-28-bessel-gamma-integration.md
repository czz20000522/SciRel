# 指数缩放 Bessel-Gamma 开发整合记录

状态：隔离开发候选；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `2f73d31` 为基线，只整合 fluidBW 保存候选中的
`scirel.kinetic.bessel-gamma` 叶子关系。科学合同在
[exact document](../../catalog/examples/scirel.kinetic.bessel-gamma.json)，
实现与直接测试分别在 `src/scirel/kinetic/bessel_gamma.py` 和
`tests/operator_contracts/test_bessel_gamma.py`。有限谐波色散张量仍在 intake，
其另一个依赖 `scirel.kinetic.plasma-dispersion-function` 已在主仓；本批
不重绑任务图，也不声称已验证整个色散求和。

## 科学关系与来源

归档 fluidBW 的 `bessel_gamma_functions` 算子以指数缩放的 `ive`
计算 `Gamma_n(x)=exp(-x) I_n(x)` 和导数
`Gamma'_n(x)=exp(-x)[(I_(n-1)(x)+I_(n+1)(x))/2-I_n(x)]`。
缩放因子 `exp(-x+abs(Re(x)))` 与 `ive` 配合，避免先形成大正实数
参数的未缩放 `I_n`。SciRel 保留该公式，并将阶数限制为有限、精确
可表示的整数，拒绝布尔、非整数、不可广播或不可表示的结果。
来源算子先把阶数转为 float64，某些非整数输入可继续运行；因此
此处是明确的开发合同收紧，不是错误输入上的逐位来源复刻。

只读核对历史归档 `D1待重审历史产物/fluidBW-e39cf9e7`：
`operators/bessel_gamma_functions/scientific_operator.py` SHA-256 为
`2aa8a7079c0d248b25832dc15a09e5c2e019244afd62a721581c9e032c1e080c`，
其直接测试 SHA-256 为
`8d98d3deb98e859ac66ce21188c8c015f60956cdd1c5b7b879fd4c12bd36432d`。
两者均与 intake 锁定记录一致。`python -B` 对照命令先断言
`scirel.__file__` 位于本候选 `src/`，从保存测试安全解析 98 点 oracle，
再与 SHA 已核对的保存实现及候选结果比较；没有写入归档。
候选相对 oracle 的最大绝对误差对 `Gamma_n`、`Gamma_prime_n` 均为
`2.7755575615628914e-17`；最大相对误差分别为
`3.570785169055376e-15`、`1.3824711310933914e-14`，满足
`1e-15` 绝对和 `1e-13` 相对验收界。该实参数有限网格不证明
任意复平面来源等价、谐波截断收敛或物理归一化选择。

fluidBW 保存目录位于待重审历史归档，合格 D1 交付根在本批核查时
为空。其旧 D1 标签、保存 oracle 和开发测试都不是当前 whole-source
资格或专家批准；许可证和科学适用域仍待人审。

## 本批验证

- 新直接回归先因模块缺失在收集阶段失败；加入实现后 15 项通过。
- exact document 的 dev5 签名和示例通过本仓验证器；当前开发 catalog
  由 17/64 增至 18/65。
- 主仓 `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 2f73d31` 选择五个测试文件，
  **93 passed**，未回退全套。18 份 exact documents 通过 runtime/example
  校验；`git diff --check 2f73d31..HEAD` 通过。这些只构成开发验证。
