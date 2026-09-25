# SciRel Bosch-Hale 来源资格更正待审 successor r27

状态：**开发期待审，不是科学认可或公开发行**。r26 的冻结字节和判断保留；目前没有上一可信版本，首次专家审核仍覆盖全部 68 个公共资产。本轮没有合格新 L1，没有修改 `src/scirel`、公共签名、数值默认值、直接测试或 `0.1.0.dev15` 内部 wheel。

## 本轮变更与审核范围

独立 whole-source 审查撤回了 ASCOT5 和 TokaGrad 的项目级严格 D1 资格。此前 Bosch-Hale exact document 将二者写成当前严格冻结来源，超出了最新交接证据。本轮修正该文档的 provenance 和 evidence ceiling，并同步修正聚变领域草稿；原开发整合记录追加日期更正，不改写当时的判断或数值比较。保存的候选树、ASCOT5 编译源码金值和 TokaGrad source-free 对照仍是有界历史开发证据，不能据此称为当前合格 L1。资格撤回的具体源码缺口与归档位置见[开发整合记录](intake-2026-09-25-bosch-hale-reactivity.md)及第一阶段交接。

相对 r26 的开发差异建议审阅 `scirel.fusion.bosch-hale-reactivity` 的来源与证据上限，不是新的数值关系或依赖图变动。旧直接测试和运行时证据在其原有适用范围内仍有效；它们不证明完整源项目复现、物理拟合全域有效或专家认可。r26 未获专家认可，不能作为可信基线来豁免首次全版科学审核。

## 待专家决定

四通道拟合的科学身份和可信温度范围、历史来源证据是否足够支持该开发实现、许可证，以及 TokaGrad 舍入和夹取变体是否应保留，仍需专家判断。当前 68/68 文档覆盖只说明开发目录的当前范围；68/68 来源许可证仍为 `pending-human-decision`，不能推断可公开发行。版本级可信晋级和公开 release 继续阻断。确切提交、文档、catalog、wheel 及执行证据由本版 review manifest 绑定。
