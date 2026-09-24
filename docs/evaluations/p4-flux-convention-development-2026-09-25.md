# P4 磁通约定开发修正

状态：开发期合同与回归，不是领域专家认可，也不授权真空场到平衡图的直接接线。

圆电流丝 Green 关系返回的 `gpsi` 在当前实现中是 `psi = R A_phi` 的每安培响应，不是完整环连磁通 `Phi = 2*pi*psi`。直接响应 `gBR/gBZ` 与用 `gpsi` 经 `B_R = -(1/R)dpsi/dZ`、`B_Z = (1/R)dpsi/dR` 反推的场，在 41x41 个点的离源内部网格上最大归一化差分别小于 `2e-3`；错误地乘 `2*pi` 后，差约 `5.28`。测试见 `tests/operator_contracts/test_circular_filament_green.py::test_flux_normalization_recovers_direct_green_field`。该数值试验只检验当前圆丝模型和网格，不证明所有几何、轴边界或奇点。

因此本轮将四份现有 exact documents 的开发合同对齐：`circular-filament-green.gpsi` 和 `current-green-superposition.gpsi` 为 `Wb/rad/A`；叠加 `psi`、多线圈 `psi_vac` 和 `poloidal-field-from-flux.psi` 为 `Wb/rad`。字段名、函数签名、数值实现和默认值不变，不加入自动 `2*pi` 转换。旧文档中把这些值当完整 `Wb` 使用的调用方，其解释有兼容影响，必须重新核对数值来源和坐标约定；只做字符串重标不能修复已作过的错误物理换算。

本轮仅覆盖圆丝 Green -> 当前叠加 -> 多线圈真空场 -> 磁通导场这一闭包。稠密 Green、镜像 Green、径向积分、理想导体边界及各平衡图仍有 `Wb`/`Wb/A` 标签；它们的公式、参考边界、网格和依赖合同须分别核验。故 P4 仍可交付真空场预览，但不能因本轮改标就把 `psi_vac` 输入平衡映射或材料支撑并称为等离子体平衡。出库侧复测应检查其真空计算保持原数值、单位说明改为 `R A_phi`、没有擅加 `2*pi`，并继续阻断未经审查的后续接线。

领域专家仍需确认规范单位、其他关系的迁移范围和公共字段命名；许可证与整个开发版本的科学认可也未完成。
