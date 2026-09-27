# 中性粒子输运

状态：开发期叶子关系导航，待领域专家划定完整输运问题；不代表 KN1D 代际迭代、碰撞闭合或终端诊断已经整合。

## 开发样例关系

- [中性物种热速度标度](../../catalog/examples/scirel.kinetic.thermal-speed-scale.json)从 eV 温度和以保存氢质量为基准的质量因子计算 m/s 速度；历史参数名 `mass_amu` 不表示标准原子质量单位。
- [单代中性分布密度归约](../../catalog/examples/scirel.kinetic.generation-density-reduction.json)按调用方提供的柱坐标权重和轴向单元宽度，将 `(nvr, nvx, nx)` 分布归约为 `(nx,)` 密度；它不构造速度网格或求解输运方程。

这两项没有直接资产依赖。链接指向 `catalog/examples/` 开发 pilot 的 exact documents，不代表专家批准或公开发布。

## 证据与待整理项

有效实数输入上的有限保存点与摘要锁定的 KN1DPy 归档实现精确相等；SciRel 对非实数输入、热速度派生质量下溢和密度溢出采用已声明的失败合同。来源项目的 whole-source D1 资格已撤回，有限点比较不能替代重新冻结、科学审核或许可证决定。其余中性输运算子、组合顺序、状态与停止条件仍待逐项核对。
