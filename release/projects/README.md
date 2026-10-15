# 外部项目交付与 SciRel 接收对账

本表是 SciRel 维护者的接收对账，核验日期为 2026-10-15。它记录从实际交付、整合历史和当前
发行物核对出的结论，不是外部拆解的第二套进度账。后续在此更新对账，不按每次运行新增副本。
外部项目身份和目录入口仍由 [目录引用](external-project-registry.json) 定位。

## 本次核验的边界

- Home 当前有 11 个项目目录；11 个均有唯一 FINAL，PDRF 的 FINAL 现已包含最新保留范围 D2 与技术 D3 交付。有 FINAL 不表示整项目已完成。
- 外部保存入口为 `/e/SciRel-lab/projects/<project>/decomposition/FINAL/`。其中部分交付明确只完成
  D0、D1 或局部 D2；这些范围必须保留，不能把保存成功计为完整拆解成功。
- 当前 wheel 按 [wheel 当前记录](../wheel/CURRENT.json) 解析；本批已构建并实际安装校验。
  以下“包内存在”来自该 wheel 的实际成员；运行结论另由安装验证记录限定。
- “技术闭环”指已保留的完整核心科学范围及安装应用证据，不等于无条件物理保证、人工认可或公开发行。

## 项目逐项对账

| 项目 | 可核验的最远交付 | 当前 SciRel 情况 | 接下来实际要做的事 |
| --- | --- | --- | --- |
| Pleiades | 完整核心 D2、六个全尺寸 BRB/WHAM D3 技术运行已接收 | 完整核心已合入；51 份遗漏合同及领域文档已恢复，当前安装包验证通过 | 本批整合收尾完成；从待拆解工作中移出，不因旧 pending 或历史文档失败重新开工 |
| GPDF | 后期修正的完整核心 D2/D3 已独立接收；Home 自足 FINAL 已收到 | 7 个科学/数据模块与已接收候选逐字节一致；22 份合同及领域文档已恢复，安装验证通过 | 本批整合收尾完成；Home FINAL 已逐文件核验，不再从 D0/D1 重做 |
| PDRK | 后期候选已有完整保留范围 D0–D3 技术接收 | 接收候选的 20 个 Python 文件保持一致；81 个原生资源及必要通知已补包，46 份合同已恢复；Home 唯一 FINAL 已补齐后期完整交付 | 本批整合收尾完成；安装后的原生算子和组合回归已通过，不再重新拆解 |
| PDRF | 完整保留范围 D2 已交付并合入；Home amd64 已接续 D3 | 当前 wheel、4 份合同和文档摘要逐项核对一致；Home 实际安装执行 40 项 D3 观察、独立读回和跨进程重复，全部通过；唯一 FINAL 已更新 | 技术 D3 收尾完成；保留 D2 未装载的 1.47GB D0 环境包限制，人工科学认可、权利和发行状态仍未改变 |
| fluidBW | 完整保留范围 D2 已冻结并合入；有早期范围的 D3 记录 | 37 个科学实现/原生文件与最终 D2 候选一致；7 份修正合同及中文文档已恢复，Home amd64 实际安装的 13 项原回归通过 | 合同与安装缺口已收口；早期 D3 对当前完整范围的继承仍按实际证据核对，不把最小示例通过当作整项目 D3 完成，也不重跑已完成阶段 |
| TORAX | bootstrap/FVM、profile/energy 等有界 D2 批次 | 多批局部能力已合入；原选择集 15 个合同未进入当前目录；交付明确未完成整个 TORAX D2 和 D3 | 先补合入批次文档，再按剩余整项目能力接续；不能把叶子或局部 D2 批次当作整个 TORAX 完成 |
| ASCOT5 | D1 CPU 后继的有界安装与对照交付 | 交付明确 whole_project_complete=false，独立整项目接收未完成；未发现整项目合入依据 | 从已保存 D1 继续 CPU 对照、来源行为及材料缺口；不重启已完成 D0 |
| BO | D1 保存前沿；15 个配置应用已尝试源/候选对照 | OWNER_RESOLUTION 明确 INCOMPLETE_PROJECT；成功的 Symbolic/native、时间戳与应用/图形成果仍有材料缺口 | 复用已有 15 应用证据，补指定成功分支材料与独立接收，不再重复遍历已有前沿 |
| BORAY | D1 有界轨迹、图形及功率组合 | 72 项 census 不等于 72 项动态闭环；完整默认求根、交错轨迹/吸收及原定运行接口仍有缺口 | 从既有 D1 继续缺失的完整默认/交错流程，保留原输入和失败；不能把已有绘图输出视为默认科学求解完成 |
| JOREK | D0 已固定；D1 有界交付，代码历史和科学数据已从旧卷导出 | D1 报告仍列 SPI 反馈桥、其余安装重组和七个可执行来源前沿；原 kinetic 终态失败保持失败 | 从 FINAL 中代码 bundle、wheel 与科学数据包恢复这些 D1 前沿；不重做 D0，不重跑已通过的 GVEC 安装证明 |
| CQL3D | 已有 D0 冻结；更后的索引语义修正 checkpoint 尚有 74 项 | 已合入的少量科学叶子不代表整项目完成；更后 checkpoint 明确不是接收，整项目 D1–D3 无完成证据 | 对照已固定 D0 和后期修正继续收口 74 项，保留 PGPLOT/编译及配套材料边界，再进入整项目 D1 |

本范围内，三项已有完整核心技术闭环，八项尚未建立整项目闭环。这个分组用于避免重复拆解，
不把当前包或文档交付缺陷伪装成来源项目没有完成，也不把局部合入抬高为整项目完成。

## 错位原因与本批处置

1. **判断 GPDF 未合入的依据错误。** 候选提交不是 HEAD 的祖先，不能证明后继没有移植其内容。
   当前主线的 `2decbd1` 已整合修正核心；本轮以实际 wheel 的 7 个模块摘要确认了内容一致。
   之前“GPDF 尚未合入当前 wheel”的表述撤回。
2. **源码合入与包内闭包曾脱节，现已修复。** 旧 wheel 缺少 PDRK 的 81 个必需原生文件；
   原生 transport 会严格解析资源目录。不能把其纯 Python 导入或其他两个案例运行通过概括为整个包可用。
   新 wheel 已逐字节纳入这些资源和当前保留的 21 份许可/通知文件，并新增实际构建回归。
3. **误把维护中的科学合同当成外部来源 catalog 移出。** 修复前，原来选定的 250 条记录中，有 134 个
   公共调用入口在当时的 141 份合同中无对应记录。此处按 module+symbol 比对，并处理了已明确的领域路径迁移：
   Pleiades 51、TORAX 15、GPDF 22、PDRK 46。fluidBW 修正族的 7 个入口此前也缺少当前合同。
   三项目的 119 份及后续 fluidBW 7 份现已恢复，当前有 267 份合同；TORAX 15 份仍属于后续独立范围。
   这不是新增能力的计数；恢复时保留科学字段，只维护领域 import 和当前安装绑定。已合入实现的科学合同、
   测试及必要许可属于 SciRel，独立于原始拆解目录。不能因原目录带项目名就把这些维护资产整体外移。
4. **外部 FINAL 曾落后于实际交付，现已对齐。** PDRK 已补齐现存后期 D1–D3、科学修正及独立接收材料；
   早期重复合同删除。Pleiades、GPDF、PDRK 三个唯一 FINAL 的清单内文件和合格 wheel 均已逐字节核验。
   外部 FINAL 只描述外部产物，不复制 SciRel 的合入或发布状态。
5. **本批已补齐两条版本线的接收绑定。** 新 wheel 记录绑定三个实际 FINAL 的清单摘要及候选包；
   文档独立推进，当前 267 份合同、中文说明及学科目录共同构建；两个教程沿用同一安装包的已执行且绑定不变的证据。
   已冻结历史记录不追改；旧 pending 只解释原候选，不再作为当前调度状态。

## 其他历史来源的管理盲区

当前 Home 的 11 项目录不是 SciRel 所有历史来源项目的全集。已核验的其他来源至少包括：

| 来源 | 当前能确认的事实 | 不能据此推断 |
| --- | --- | --- |
| KN1DPy | 当前科学文档有大量局部关系，其来源说明明确严格 D1 资格已撤回 | 不能算完整 KN1DPy 拆解或重新接收完成 |
| GSEQ | 已有若干磁场/几何关系；来源文档明确属于有界历史开发对照 | 不能算整项目 D1–D3 完成 |
| FIDASIM | 当前有 DD 中子运动学叶子；合同明确来源锚点来自保存包，未在该运行复核 Fortran | 不能算整个 FIDASIM 已拆完 |
| TokaGrad | 有旧拆解及源优先复核记录，神经输运分支与模型输入曾有实质缺口 | 不能凭早期 full_freeze 自报或平台测试包名称算完成 |

这些来源尚未在本轮定位到符合当前边界的唯一完整 FINAL；单有中央源码下载包也不证明已启动或完成拆解。
它们需要单独找回实际交付及责任范围，不能直接塞进上述 11 项的完成数量。

## 收尾次序与证据入口

本批三项整合收尾、fluidBW 合同安装验证和 PDRF 技术 D3 已完成；PDRF 的唯一 FINAL 已按最新完整交付更新，fluidBW 核对既有 D3 的完整范围继承；
随后按 TORAX 局部 D2 和 ASCOT5/BO/BORAY/JOREK 的 D1 前沿逐项回收，CQL3D 从后期 D0 修正接续。
缺原材料、缺环境或缺科学证明必须写成具体缺口，不用一个笼统“未完成”重新启动整条链。

- 完整核心独立接收：[Pleiades](../../provenance/validation/pleiades-root-full-core-20261014.json)、
  [GPDF](../../provenance/validation/gpdf-root-full-core-corrected-20261014.json)、
  [PDRK](../../provenance/validation/pdrk-root-full-core-20261014.json)。旧接收收据中的当时未合入字段保留原样，
  当前合入判断必须结合后继整合和实际 wheel。
- 已合入批次：[GPDF 科学映射](../../provenance/integrations/gpdf-full-core-20261014.json)、
  [PDRF D2](../../provenance/pdrf-d2/CANDIDATE_EVIDENCE.json)、
  [fluidBW D2](../../provenance/integrations/fluidbw-full-retained-20261013/comparison.json)、
  [TORAX bootstrap/FVM](../../provenance/integrations/torax-bootstrap-fvm-receiver-20261012.json)。
- 文档和资源比较基点：[原累积文档选择](../../provenance/selections/scientific-core-documents-20261014-r7.json)、
  [原累积科学选择](../../provenance/selections/scientific-core-20261014-r7.json)、当前 `catalog/examples/`、
  当前 wheel 实际成员。本批 [安装验证](../../provenance/validation/completed-project-installed-closeout.json)
  记录了 260 份合同绑定、三项目 609 项回归及两个教程运行；未重跑前驱全尺寸 D3。
  原扩展探针的 13 项 fluidBW 测试受 Linux amd64 运行合同限制；后续已在 Home 的该平台实际安装通过，
  并完成全部 267 份合同签名及隔离示例验证，见 [Home 安装收据](../../provenance/validation/fluidbw-amd64-installed.json)。
  Mac 的原平台限制失败仍保留，不改写为 ARM64 通过。
- 旧来源边界：[TokaGrad/CQL3D 源优先复核](../../docs/evaluations/2026-09-30-tokagrad-cql3d-source-first-gate.md)。
- 未完项目的具体科学 checkpoint 仍在各项目唯一 FINAL 的 D0/D1/D2 交付内；持续工作的目录在 WORK，
  项目描述和外部索引继续只保存身份与路径。

- PDRF D3 安装收据：[Home amd64 D3](../../provenance/validation/pdrf-d3-amd64-installed.json)、
  [唯一 FINAL 接收](../../provenance/integrations/pdrf-d3-final-reception.json)。
  原 Mac x86 模拟收据仍保留在外部 D3 packet 中；其验证器失败没有被改写，修正后继单独记录。
