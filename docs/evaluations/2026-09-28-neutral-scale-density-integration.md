# KN1DPy 中性热速度与单代密度归约开发整合记录

状态：已进入 SciRel 开发主仓；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `4e264b7` 为基线，逐项对照 intake `647d5db` 的
`scirel.kinetic.thermal-speed-scale` 和
`scirel.kinetic.generation-density-reduction`。两个独立叶子关系均无
直接资产依赖，公共科学合同分别见
[热速度 exact document](../../catalog/examples/scirel.kinetic.thermal-speed-scale.json)
与[密度归约 exact document](../../catalog/examples/scirel.kinetic.generation-density-reduction.json)。
本批不重绑 TaskGraph，不推断 KN1D 完整输运链。

## 科学身份

热速度是 `sqrt(2*e*T_ev/(mass_amu*m_H))`，其中参数名沿用历史 API，
`mass_amu` 实际是保存氢质量 `1.6726231e-27 kg` 的倍数，不能按标准
原子质量单位解释。它与 SciRel 现有的无量纲热电子速度比及 fluidBW
物种平衡尺度在单位、常数或输出结构上不同，保持独立身份。

密度归约接收调用方的 `(nvr,nvx,nx)` 单代分布、柱坐标权重及轴向
单元宽度，按来源的非均匀二维、径向一维或均匀列路由返回逐空间格
密度。它不生成网格、不推进代际状态，也不提供输运停止条件。

## 来源与行为差异

只读核对归档 `D1待重审历史产物/KN1DPy-631d0bf1/operators/`
中热速度与密度归约实现的 SHA-256，分别为
`9867b3fbc30317e519d0b1ed62d885c8550d00337d889542b5653c267b82fda8`
和 `d11b3ece9c168f6e19df37a14aec5e46adf279f379f6bf835b0e26271cb8776c`，
与 intake 锁定值一致。`python -B` 回放先断言 `scirel` 导入自隔离
工作树 `src/`；热速度 3 个有效点、密度 3 条权重路径各一个有限
算例与归档实现逐项精确相等。没有修改来源树。

归档热速度实现接受布尔值和数值字符串，且极小正质量的 kg 换算
下溢后抛 `ZeroDivisionError`。归档密度实现接受布尔权重、字符串
分布和复数数组的实数强制转换，并可对有限极值输入返回 `inf`。
SciRel 依两份 exact document 的实数输入与有限输出合同，拒绝这些
情况并抛 `ValueError`。类型回归先在原样 intake 实现上复现 10 项
失败；派生质量下溢回归先复现 `ZeroDivisionError`，随后最小检查
修复。旧正常点公式、运算顺序和数值断言未弱化。直接测试现为
**23 passed**，其中包含密度溢出拒绝。

KN1DPy 严格 D1 资格已撤回；归档来源及有限点回放仅是历史开发
比较，不能证明 all-input parity、整体输运物理、许可证许可或专家
批准。合格 D1 交付根在本批核查时为空。

## 本批验证

- 两项直接科学测试：显式隔离源码路径下 **23 passed**。
- 摘要锁定的只读来源回放：热速度 3 点、密度 3 条权重路径精确相等；
  溢出与类型差异已单独观察。
- 隔离候选提交 `4d5511a`；主仓整合提交 `12bed57`，仅暂存本批
  20 个文件，README 的其他 owner 改动仍未暂存。
- 主仓 `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 4e264b7`
  精确选中 7 个测试文件、**119 passed**，无全套回退。
- 主仓 22 份 exact document 通过 `--check-runtime --execute-examples`；
  `git diff --check 4e264b7..12bed57` 通过。
- 集成后再核查，合格 whole-source D1 交付根仍为空；intake
  `647d5db` 工作树干净，其 `pending_unapproved` 状态不变。
