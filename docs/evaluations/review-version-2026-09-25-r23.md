# SciRel Frank-Egedal 与自由边界接线待审 successor r23

状态：**开发期待审，不是科学认可或公开发行**。r22 原样保留；没有上一可信版本，首次专家审核仍覆盖全部 68 个公共资产。本轮没有合格新 L1，也没有修改运行代码、公共签名、数值默认值或 `0.1.0.dev15` 内部 wheel。

## 科学增量与反向依赖

[Frank-Egedal 压强闭合图](../../catalog/examples/scirel.kinetic.frank-egedal-pressure-closure.json)的径向包络使用归一化比值 `(psi-psi_axis)/(psi_edge-psi_axis)`，而不直接使用绝对磁通量。新增直接回归证明：在选定输入上同时以 `2*pi` 重标度 `psi`、`psi_axis` 和 `psi_edge`，两个压强输出及径向形状不变；保留未重标度的 `psi_edge` 则改变压强。历史来源图的 `Wb` 标签并未被改写，维护图的 `psi` 端口改为调用方约定坐标；当前 SciRel 自由边界图的 `psi=R A_phi` 为 `Wb/rad`，接线时轴、边值必须使用同一坐标。

新增组合回归把真实 Frank-Egedal 闭合作为[自由边界各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.free-boundary-anisotropic-picard.json)的调用方端口。在 7x7 制造网格、单个活跃电流单元、无墙、`maxiter=1` 的条件下，图产生非零电流；离源点的 `psi/BR/BZ` 与圆丝直接响应比较，终态压强与使用返回 `psi/B` 重新调用闭合所得结果比较。两个图、径向包络 exact document 和领域草稿据此更新；没有把名称相似的闭合或平衡图合并，也没有更改任何运行时依赖绑定。

这只证明一个选定参数和制造几何下的数值端口接线，不证明任意磁通面识别、压强模型适用性、墙分支三场一致性、迭代收敛、自洽物理平衡或同输入源码复现。`psi_axis`/`psi_edge` 的物理选择、Frank-Egedal 参数与求积适用域、来源许可证仍待专家判断。冻结的 L1 和历史来源记录均未改写；确切执行与产物摘要见本版 `test-evidence.md`。
