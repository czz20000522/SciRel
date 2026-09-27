# 解析等离子体色散函数开发整合记录

状态：隔离开发候选；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `6d90165` 为基线，逐项对照 intake `647d5db` 中的
`scirel.kinetic.plasma-dispersion-function`，只纳入该关系、公共导出、
直接测试、dev5 [exact document](../../catalog/examples/scirel.kinetic.plasma-dispersion-function.json)
及当前 catalog 计数。没有重绑来源 TaskGraph。

## 科学关系与边界

PDRK 和 fluidBW 保存算子都求无量纲复宗量的
`w(z) = exp(-z^2) erfc(-i z)` 与 `Z(z) = i sqrt(pi) w(z)`，但前者有
Weideman 阶数 `N`（默认 16），后者固定 `N=64`，还返回分支诊断。
它们的数学关系重合，近似输出和端口合同并不等价。SciRel 使用现有
`scipy.special.wofz` 计算解析关系，不暴露阶数或诊断；调用方必须先按
明确的热速度、漂移和波数约定构造 `z`。本批不接色散矩阵或求根图，
也不推断冷介电张量与本函数可直接组合。

保存的 fluidBW 文档把 `Z(0)` 写为 `i*pi`，其算子源码与解析恒等式
给出 `i*sqrt(pi)`。SciRel 的原点回归采用后者，不改写保存文档。
纯虚大正参数的来源乘积路径可能上溢再下溢，而 `wofz(30j)` 有限；
极深下半平面若解析结果超出 complex128，SciRel 抛 `ValueError`。

## 来源与独立数值核对

2026-09-28 只读核对归档 `D1待重审历史产物` 中两份
`operators/plasma_dispersion_function/scientific_operator.py`：PDRK SHA-256
`b951764f0f4829874444c198dba94006aef000d69b94403915da57d933f2b131`，
fluidBW SHA-256
`d16799ad771a5eb16dda2b3d41b40e49564c0fb1435bf086f71aa67d6b54ca16`。
两者与 intake 保存记录相符；这只固定了被比较的归档文件字节。

独立复算使用 `z = [0j, 1.5j, -2j, 0.5+0.5j, 2.0-0.8j, -3+0j]`。
运行时先断言 `scirel.__file__` 位于本候选工作树 `src/`，然后以
`python -B` 载入两份 SHA 已核对的归档实现；不写归档字节。
PDRK `N=32` 的最大绝对误差为 `w: 3.9238795802786605e-14`、
`Z: 6.9543963185638e-14`（验收界分别 `1e-12`、`2e-12`）；
fluidBW `N=64` 为 `w: 1.1443916996305594e-16`、
`Z: 2.2887833992611187e-16`（验收界 `1e-13`、`2e-13`）。
另在 `z=0.5`，PDRK 默认 `N=16` 的 `w` 与解析值相差
`1.2362285584712998e-07`，不能声称默认输出等价。
首次独立命令意外导入已安装 SciRel；其结果未用于本批证据，
随后显式置入候选 `src/` 并断言导入路径后重跑。

这些有限点对照不证明任意复宗量的来源逐位一致，也不证明两个
来源项目已完成 whole-source D1。合格 D1 交付根在本批核查时为空；
两份保存目录位于待重审历史归档。许可证、科学身份、数值误差上限、
适用域和后续组合仍待专家决定。

## 本批验证

- 新增直接回归先因公共函数不存在而在收集阶段失败，加入实现后 11 项通过。
- `python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples`
  校验 17 份 dev5 文档的签名与示例。
- `pwsh ./scripts/check.ps1 -Mode affected` 选择五个测试文件，88 项通过，
  未触发全套回退；新算子在当前主仓没有反向 TaskGraph。
- `git diff --check` 通过。上述均为开发验证，不改变待审与发行状态。
