# SciRel 磁通核与 Picard 单步合同待审 successor r15

状态：**开发期待审，不是科学认可或公开发行**。r14 冻结快照不改写；目前没有上一可信版本，专家首次审核仍覆盖全部 68 个公共资产。本轮没有新的合格 L1 输入，也没有修改科学 callable 或 `0.1.0.dev15` wheel。

## 本轮可复核的合同

SciRel 圆丝 Green 的 `gpsi` 是 `psi=R A_phi`，不是完整环连磁通 `2*pi*psi`。稠密 Green 的每一列在非奇异目标上与单个圆丝 `gpsi/gBR/gBZ` 一致；反射对称网格上的镜像 Green 矩阵与直接逐丝构造的稠密 `gpsi` 一致。因此这两项响应的开发单位从旧 `Wb/A` 更正为 `Wb/rad/A`，没有乘入 `2*pi`，也没有改写轴源或非有限自项的零约定。

一条 17x17 制造网格回归把外部圆丝真空 `psi_vac`、镜像 Green 和单个非零等离子体 cell current 送入轴对称 Picard 单步；在离源目标上，由更新后 `psi` 反推的 `B_R/B_Z` 与两个圆丝直接场在 2% 内一致，错误乘 `2*pi` 则不能通过。故该单步的 SciRel 轴对称端口标为 `psi`/`psi_vac`: `Wb/rad`、`g_psi`: `Wb/rad/A`。边界算子是齐次线性修正：把场磁通和两个 Green 矩阵同时乘 `2*pi`，所得边界电流不变、磁通输出同时缩放；SciRel 轴对称标准输入标为 `Wb/rad`，完整 `Wb` 只可在**所有**相关输入同步转换后使用。

四项 exact documents 是 [稠密 Green](../../catalog/examples/scirel.field.dense-axisymmetric-green.json)、[镜像 Green](../../catalog/examples/scirel.field.mirror-plasma-green.json)、[Picard 单步](../../catalog/examples/scirel.equilibrium.axisymmetric-picard-update.json)和[边界修正](../../catalog/examples/scirel.field.ideal-conductor-boundary.json)。公共函数签名、数值、默认值和失败行为均未变；旧 `Wb` 标签的消费者若此前把值当完整环连磁通，需要重新核对物理解释与输入尺度，不能只改显示文字，也不能只缩放磁通而不缩放 Green。

## 验证与未闭合范围

`pwsh ./scripts/check.ps1 -Mode affected` 选中四组直接测试及文档测试，**38 passed**。`python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples` 对当前 68 份文档通过。原 dev15 wheel 的隔离 venv 以 `python -I` 从 `site-packages` 导入并运行四组更新测试，**24 passed**；科学依赖复用开发机环境，不证明全依赖离线重装。新增组合回归只比较一个离源目标和一组制造输入，不证明奇点、自场、真实材料壁、实际装置或源项目同输入全链复现。

本轮**仅闭合 P4 真空圆丝 → 稠密/镜像 Green → Picard 单步 → 离源极向场**的数值与单位链，以及边界算子的同步换算规则。各向异性、约化 Hall、自由边界、各向同性和镜端 TaskGraph 的旧 `Wb` 标签、压力闭合对 `psi` 的依赖、墙修正后 `BR/BZ` 不同步、网格/边界条件与物理适用域仍须逐项核对；不能据此把 P4 真空输出直接标成完整等离子体平衡。r14 的近零分母相对残差仍按默认严格门禁拒绝，未放宽容差。来源许可证、首次专家认可、可信晋级及公开发行均未完成。
