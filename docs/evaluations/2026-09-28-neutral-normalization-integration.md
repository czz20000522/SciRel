# KN1DPy 中性边界与空间源归一化开发整合记录

状态：已进入 SciRel 开发主仓；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `b2535a2` 为基线，逐项对照 intake `647d5db` 的
`scirel.kinetic.incoming-boundary-flux-normalization` 和
`scirel.kinetic.spatial-source-shape-normalization`。两项均为无直接资产
依赖的归一化叶子关系，未重绑 TaskGraph；公共科学合同分别见对应的
[边界归一化](../../catalog/examples/scirel.kinetic.incoming-boundary-flux-normalization.json)
和[空间源归一化](../../catalog/examples/scirel.kinetic.spatial-source-shape-normalization.json)
exact documents。

## 科学身份与现有能力

边界关系只积分 `vx > 0` 的调用方形状和柱坐标权重，以预缩放通量
`Vth * sum(volume * shape * vx)` 求 `abs(target)/incoming_flux`，并将
非正向半空间置零。零目标通量合法，返回零尺度和零边界。它消费调用方
提供的热速度数值，但不调用或重定义现有热速度资产；柱坐标权重同样由
调用方提供，不建立未审查的速度积分权重依赖。

空间源关系按调用方的米制空间坐标做梯形积分，返回单位积分形状和
原始积分。两者在现有主仓没有等价公共函数，输入、输出和失败合同也
不同，故保留为两个独立 Operator。两者均不求解 KN1D 代际输运。

## 来源与修正

只读核对归档 `D1待重审历史产物/KN1DPy-631d0bf1/operators/` 中的
两份实现，SHA-256 分别为
`7251bb29eca994683134966abac0a7f731baf557202db1d19fc798f70474768e`
和 `83b2d7b9e860d8ee57cef6b5332b97fe31a6269a861c6e2a6df42506bfd18629`，
与 intake 锁定值一致。`python -B` 比较先断言 `scirel` 来自隔离工作树
`src/`；边界函数的正、负、零目标各一例和空间源函数的三组有限有效
剖面，均与归档实现逐项精确相等。没有修改来源树。

归档边界实现未完整检查 `vx`、柱坐标权重和热速度的有限性、权重的
非负性以及派生通量、尺度和边界的有限性；归档空间源实现接受布尔
和数值字符串强制转换，复数输入可能抛 `TypeError`。SciRel 按实数
输入和有限输出合同拒绝这些情况，统一抛 `ValueError`。边界 exact
document 还修正了 intake 将零目标的尺度误写为正数的矛盾，保留来源
实际的零尺度行为。修正前，校正过手算期望值的回归在来源实现上
**16 failed、10 passed**；补入两个派生输出极值回归后，直接测试
**28 passed**。有效数值路径
的公式和运算顺序未变，旧数值断言与容差未弱化。

KN1DPy 严格 D1 资格已撤回；摘要锁定的有限点比较只是历史开发证据，
不能证明 all-input parity、整体输运物理、许可证许可或专家批准。
合格 D1 交付根在本批核查时为空。

## 本批验证

- 直接科学测试：隔离源码路径下 **28 passed**。
- 摘要锁定的只读来源回放：两种关系各 3 个有限有效点精确相等；
  NaN 热速度和数值字符串源剖面的差异已单独观察。
- 隔离候选提交 `559850c`；主仓整合提交 `84d78e1`，仅暂存本批
  20 个文件，README 的其他 owner 改动仍未暂存。
- 主仓 `pwsh ./scripts/check.ps1 -Mode affected -BaseRef b2535a2`
  精确选中 7 个测试文件、**125 passed**，无全套回退。
- 主仓 24 份 exact document 通过 `--check-runtime --execute-examples`；
  `git diff --check b2535a2..84d78e1` 通过。
- 集成后再核查，合格 whole-source D1 交付根仍为空；intake
  `647d5db` 工作树干净，其 `pending_unapproved` 状态不变。
