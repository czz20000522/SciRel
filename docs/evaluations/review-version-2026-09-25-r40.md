# SciRel 磁通剖面坐标约定文档对齐 r40

状态：开发期冻结待审，不是领域专家认可、可信版本或公开发行。当前合格 L1 交付根（`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`）为空，本轮未消费任何合格 L1 输入。

本轮把 `scirel.geometry.flux-surface-profile` 的 exact document 开发合同从"psi 与 target 使用同一 Wb 约定"放宽为"调用方自选且内部一致的约定，`psi=R A_phi` 的 `Wb/rad` 或完整环连磁通 `Wb`，算子不做任何换算"。这是文档-实现对齐，不是算法变更：

1. 实现（`src/scirel/geometry/flux_surface_profile.py`）是纯排序去重后的一维线性插值，不包含任何 `2*pi` 或单位换算；坐标整体缩放时插值结果按比例等变。
2. 反向依赖 `scirel.kinetic.grid-mirror-kinetic-closure` 的图合同已声明其 `psi` 输入为"调用方一致的 Wb 或 Wb/rad"，并注明嵌入 Hall 图时传入 `Wb/rad`；旧文档的 `Wb` 标签与该消费方合同矛盾。
3. 代码库约定已有 [P4 记录](p4-flux-convention-development-2026-09-25.md)：真空场链的 `psi` 是 `R A_phi`（`Wb/rad`），不加自动 `2*pi` 转换。领域草稿 [磁通坐标剖面与路径采样](../domains/flux-coordinate-sampling.md) 也早已只要求"`psi_samples` 和 `target` 使用同一磁通约定"。

新增直接回归 `test_consistent_flux_coordinate_scaling_preserves_profile_values`：同一 values 下，把样本与 target 同步缩放 `2*pi`（Wb -> Wb/rad 反向演示），插值 values 与 profile_values 不变、返回 `psi` 同步缩放。文档 `verification.scope` 相应新增该坐标重标度不变性条目；`known_limitations` 明确算子不在 `Wb/rad` 与 `Wb` 间转换。源码态与 `0.1.0.dev18` 安装态（wheel SHA-256 `25a9d71b82965ddab8136b619aaacf05a7593ee71dfe3619eb6dd7269c9994f7`，未重建）均通过 68 份文档运行时校验，安装态探针亦复现缩放不变性。

相对 r39 的科学增量仅此一份文档与其直接测试；未修改科学 callable、其他文档、开发 catalog 结构或 wheel。无可信基线，首次专家审核仍覆盖全部 68 项。测试通过、文档校验和冻结都不构成科学认可；专家需决定规范磁通约定、重复样本处置及本放宽是否成立。
