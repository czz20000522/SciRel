# SciRel 首次整版待审 successor r3

状态：**冻结待审材料草稿，未获专家科学认可，不可公开发行**。上一份[待审说明](review-version-2026-09-25-r2.md)绑定 `f311a34` 的历史 `16/64` 快照，不修改、不视为可信基线。本说明将由新的确切 Git commit/tree、wheel、catalog 与测试证据冻结为 successor；在该 manifest 生成前不宣称快照已经冻结。

## 首次审核范围

SciRel 仍没有上一可信版。当前开发树有 **65 个公共资产（53 个 Operator、12 个 TaskGraph）**，因此专家首次整版审核不能仅看本次 Git diff。`catalog/examples` 包含 **17** 份 exact documents，开发 catalog 目标为 `partial: 17/65`，其余 **48** 份尚缺完整 exact document。旧 admitted 标签和两个历史待审快照都不构成整版可信认可。

相对 r2，本次科学增量是[四通道 Bosch-Hale 热反应率](../../catalog/examples/scirel.fusion.bosch-hale-reactivity.json)。[关系族审查](intake-2026-09-25-bosch-hale-reactivity.md)将 ASCOT5 四通道拟合与 TokaGrad 的 DT 舍入/夹取变体区分；未改变旧 DD 能量入口或任何 TaskGraph 依赖。第一阶段最新交接已将 PDRK 与 aorsa3d 从当前合格 D1 集合撤出，历史字节仅作开发输入；此前 r2 的色散函数、r1 的波矢及已有 aorsa3d 开发关系仍在首次审核集合中，其来源论据必须等新严格冻结后重核，不能因本次不修改而自动获批。新聚变领域[草稿](../domains/fusion.md)仅组织有依据内容，领域结构及适用域由专家确认。

## 可审材料与待决

- 文档为 17 份 `scirel.asset-document.v1` exact documents；本次四通道反应率的代码和直接/来源测试随 Git tree 固定。随快照 `test-evidence.md` 应列实际受影响测试、整仓、安装态与来源对照，不能从待审标签推断通过。
- ASCOT5 与 TokaGrad 的严格 D1 交接固定来源候选树；SciRel 的对照只证明所列温度、通道与容差，不证明来源项目整体科学功能等价。PDRK 历史路径不属于当前合格交付根，先前 r1/r2 对它的来源判断需按新交接重新限定。
- PDRK 的历史数值测试可用 `SCIREL_HISTORICAL_PDRK_ROOT` 单独指定已移出的只读目录；该参数只恢复旧比较的可运行性，不把旧产物重新认定为合格 D1。
- aorsa3d 的旧来源测试可用已有 `SCIREL_L1_AORSA3D` 指向已移出的只读目录；测试通过同样不恢复其 D1 资格。
- 专家需确定四通道的拟合精度和适用温度域、TokaGrad 舍入/夹取是否单列变体、ASCOT5 截面/运动学及 TokaGrad 源项的后续路线，并决定许可证。
- 首次整版仍缺 48 份 exact documents、12 个现有 TaskGraph 的领域审阅和可信版晋级机制。专家若只接受部分内容，应在开发树剔除或返工后另冻 successor；`-Mode release` 继续关闭。
