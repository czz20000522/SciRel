# SciRel 开发与增量整合流程

本流程将来源拆解、科学库整合与用户应用作为完整链路；各阶段交接可核对的事实，不重复生产同一份信息。
领域需求见 [workflow](requirements/scirel-workflow.md)，信任边界见 [版本设计](design/development-trust-versions.md)。

## 阶段职责与入口

| 阶段 | 负责的结果 | 统筹入口 | 不重复承担的工作 |
| --- | --- | --- | --- |
| D1 来源拆解 | 全来源科学范围、Operator/有序 TaskGraph、可运行实现、源实现与数值对照、来源与证据锚点 | [来源拆解](../skills/extraction/scientific-computation-asset-extraction/SKILL.md) | 不提前为临时资产写正式文档，不做跨项目标准库去重 |
| D2 库整合 | 对照开发/可信基线及未发布候选，比较、去重、变体、修正与组装，受影响验证和开发包 | [库整合](../skills/integration/scirel-integration/SKILL.md) | 不重做仍有效的源对照，不给吸收项生成正式文档或审核项 |
| D3 用户应用 | 真实需求、追加输入、坏数据、恢复、独立复跑及科学解释 | [用户项目](../skills/usage/scientific-project-implementation/SKILL.md) | 不重复拆源，不用单个案例证明整个库 |
| 最终审核与发行准备 | 汇集稳定代码、唯一正式科学文档、累积差异和证据，交最终拍板 | [最终待审准备](../skills/integration/scirel-review-preparation/SKILL.md) | 不把人工作为日常开发调度器，不把开发验证当批准 |

统筹 skill 只维护目标、条件路由、交接和停止条件；专业方法按需加载。各阶段不必全串行：
D1 有明确范围且所声称科学验证通过的可运行批次可进入 D2，但部分交付不得称完整项目 full_freeze。
D2 开发 wheel 可供 D3 使用。D3 按用户目标与影响选场景，不为每个库变更发明新用户项目。

## D1：完整性与来源正确性

盘清源项目的科学能力、实现、调用顺序、状态/反馈及边界。交付可执行算子、机器可读图和必要 glue，
来源位置/版本、输入输出映射、源实现对照、数值证据与明确缺口。不能以文件数、字段数或文档数量替代完整性。

代码、YAML、签名、docstring、测试或已有记录能唯一表达的信息直接引用。
不能可靠恢复的单位、约定、假设、分支选择或证据局限补在一个最小科学记录中。
缺少正式 operator.md、task_graph.md 或根报告不构成科学不合格；缺少科学含义、来源映射、
源对照或真实结果仍是相应科学缺口。D2 结构转换成功不自动确认 D1 科学合格。

断言写错时先从独立来源/推导确认正确期望和判据，再重放已有原始输出或最小验证；
不能从输出反推期望、调容差或改科学含义。脚本位置、展示格式、文档路径或包装摘要问题，
能确认原实现、输入、环境和结果归属时修复引用、检查新包装并复用数值证据。
不能证明归属、原始输出不足或科学行为变化时，只补必要证据；不伪造旧 receipt 或回写冻结记录。

## D2：整合后生成正式文档

上一阶段交付只读。固定输入和比较基线，在独立分支开发，按科学家族并行、私有产物、单写者整合。
本阶段的重复判定、来源参考、修正理由和实现约定写在本阶段派生代码的注释、docstring、函数/模块说明
或已有接续记录中。它们不是面向人的正式审查文档，不要求另写一份 Markdown，也不回写上游资产。
上一可信版不可被开发进展改写；开发分支可修改 src/scirel、公开 callable、内部 catalog 和 wheel，
明确 pending_unapproved。没有可信版本不阻断开发，也不得虚构批准基线。

先比较关系、方向、假设、单位/轴、边界、状态、数值方法和失败语义，再比较代码。
哈希、名称和相似度只筛选对象；相同样例不独立证明等价。逐输入记录一次处置与证据：
复用、重复吸收、明确覆盖、新增、变体、适配、组合或未决。子图包含和局部重叠不自动消除独立能力。
Agent 调查并解决有依据的中间分歧，不必交人类逐次裁决；不能判等时保持分离，继续独立工作。

源直接测试在 API 映射后可作对照；入口不匹配只证明不能直接替换，不直接证明科学冲突。
真实科学修改先有失败回归，验证改变资产和受影响反向依赖。未知源码归属沿用 affected 的全套回落。
代码和身份稳定后，仅为保留的新/变公共资产生成或更新唯一 scirel.asset-document.v1。
复用既有文档；重复/吸收项保留来源与处置依据。人读页面、摘要、catalog 均为同一正式文档的投影，
不再同时维护 relation page、operator.md、task_graph.md 和全文审核副本。
审核说明只解释差异并引用 exact document。进入 catalog 前仍验证依赖、签名与示例。
文档可按最终科学家族并行；过程草稿留 run 内，根报告在完成或冻结时汇总。

## D3：用户价值与反馈

固定实际消费的 wheel/catalog/代码版本及信任状态。完成需求澄清、输入检查、实现运行和独立复跑，
报告解释边界以及 Agent 自修、独立 Agent 纠错、用户救援的区别。评审建议的替代答案仍须独立核实。
缺库能力回 D2 比较；缺来源语义或实验回 D1 指定分支；不以重跑整链代替定位问题。

## 最终审核

以**上一可信版本**为基线呈现累积科学增量，不逐开发提交审批。独立 Agent 审查记录真实身份、
模型版本与发现，可走通开发链路，不能冒充人类认可。保留增量完整可评估后送审；
未解决科学缺口补证或明确排除，不强迫人类接手日常调试。

待审快照绑定 Git、exact documents、代码/测试、比较处置和有效证据；已有 wheel/catalog 同时绑定。
SciRel 将稳定待审快照登记为统一发布索引中的候选版本；返工另建关联版本。索引是最终发布版本的
选择入口，catalog、wheel 和单次 manifest 只绑定该版本的实际内容，不自行授予发布状态。
review_units 只包括保留新增/改变项；input_dispositions 完整记录无改变的复用、重复或覆盖。
纯无变化批次终结为 no_changes，不产生新 draft、审核项、批准或 release。复用不提升目标信任状态。
上传后不静默覆盖；返工另建 successor，保留原版及审查记录。人工最终可要求返工或排除；
批准只覆盖确切版本及依赖，科学实质变化须重新确认。

## 验证、提交与发行

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
pwsh ./scripts/check.ps1 -Mode affected -BaseRef <merge-base-or-release-ref>
pwsh ./scripts/check.ps1 -Mode focused -TestPath tests/<affected-test>.py
pwsh ./scripts/check.ps1 -Mode full
python scripts/release_index.py --item-artifact <review-pending-workflow.json> --git-revision <frozen-git-sha> --output <candidate-index.json>
pwsh ./scripts/check.ps1 -Mode release -ReleaseIndex <candidate-index.json> -CandidateEntryId <candidate-entry-id> -ApprovedResults <completed-results.json> -ReviewArtifactsDir <exact-review-artifacts> -ReleaseId <release-id> -OutputRoot build/verification/<new-run>
```

内循环按影响选检查并复用有效证据；纯文档验证结构、链接、signature 与相关示例，不重跑源数值。
共享合并前运行适当工作流/科学测试，发行再运行 release 门禁。
交付实际文件、SHA、检查和未验证边界；按 owner 聚焦提交并合并，保护冻结记录及其他贡献者的成果。

开发 wheel 用普通 Python 构建入口；不要用需要 approved workflow 的 release 模式阻断开发。
正式 release 仍需最终批准、许可证与依赖、完整文档、catalog/wheel/版本绑定及发行授权。
通过这些门禁后才从索引候选形成已发布条目；正式发行前把相关开发期版本和合同统一冻结为 `v1`。
索引的开发期字段布局可以随真实闭环调整，当前 `pending_unapproved` wheel/catalog 不登记为已发布。
`release_index.py` 从待审 workflow 或单项 artifact 登记每个 item 的原始 artifact revision、文档摘要及冻结 Git 提交；
当前仓库唯一的开发期索引为 `provenance/release-index.dev.json`。新开发 wheel/catalog 先用
`--snapshot-id`、`--catalog-release`、`--wheel`、来源绑定、`--source-qualification` 和 D3
证据/去向文件登记 `development` 条目；进入待审时用 `--item-artifact` 登记 `candidate`。
从现有索引用 `--existing-index` 写新文件，校验旧条目未变后更新该路径。出库 owner 提供
实际消费 manifest 和 digest，D2 单写者负责身份、来源与科学证据并核对登记；工作台当前逐项
审核状态继续由审核 artifact/投影提供。完整开发 catalog 不等于专家批准，来源混合的开发
快照不因 `pending_unapproved` 而自动取得 D1 资格；正式公开发行前合同统一冻结为 `v1`。
开发条目或待审候选的替换、撤回用 `--lifecycle superseded|withdrawn`、`--subject-entry-id`、
精确 `--evidence` 和 `--existing-index` 追加事件；替换还须给出同类的 `--successor-entry-id`。
旧条目及摘要不改写，当前未发布入口排除已替换、撤回和已发行的候选。开发条目的替换只改变
开发快照当前身份，不继承或更新独立待审候选的逐项审核身份。旧 52 项快照只保留历史定位；
正式公开发行前将有效决策和合同统一收敛到 `v1`。
同一候选的宿主开发验收用 `--review-host-evidence`、`--candidate-entry-id` 和 `--existing-index`
追加证据条目；这不产生新候选，也不替代宿主逐项审核状态或批准。
同一 workflow 的多项共享原始 revision，只产生 `candidate` 条目。多个 artifact 可重复传入 `--item-artifact`，
但重复 item 或资产会被拒绝。审核宿主导出的 `approved_items` 与各项原始 artifact 必须一起输入；artifact 以
`<sha256-hex>.json` 命名，内容摘要须与投影 revision 一致，并包含提交前版本和批准 successor。
`finalize_release.py` 核对原始/批准 revision、决定、文档、许可状态、依赖闭包、批准代码与测试文件、
Git 变更、catalog 与 wheel，重新执行批准项的测试文件，再追加 `released` 条目。批准代码目前支持
`files` 或明确 `none` 复用；`patch` 需先固化为逐文件内容。旧单 draft finalizer 仅保留为内部
生命周期 fixture，不再是 release 命令入口。
首发准备器从 exact approved projection 生成只含所选模块与审核绑定支持模块的源码树、过滤后的包初始化文件、
文档集和测试路径；release catalog 的声明总数来自该文档集，历史 admission 账本不参与门禁。源码仍跑全套工程测试，
安装后只跑所选资产的审核测试与文档示例。现有准备器仅支持首发；后续条目的 baseline 资产、文档与支持模块
尚无可验证的继承输入，因而会拒绝增量发行，不能仅凭索引中的资产 ID 复建上一可信版。

审核导出必须来自有认证及授权记录的工作台 artifact 存储；本地 JSON 摘要只能核对内容，不能证明
操作者的真实身份或发行授权。开发 fixture 的专家名称和批准动作不能作为真实审核输入。当前候选
仍无真实批准与许可，不得因本门禁可运行而称已发行。索引与 manifest 仍为 `.dev`，首条真实
闭环后在正式公开发布前统一冻结到 `v1`。
当前 `check.ps1 -Mode release`/`finalize_release.py` 只核对本地审核投影和 artifact 字节，尚未验证
同一批次的宿主认证选择快照；逐项 `items` 分页、`open`、下载和前后重读没有跨页快照 token，不能替代该证明。
真实 `released` 条目进入统一索引前，宿主导出或等价在线协议须绑定项目/plugin/view、候选身份、候选
总数及明确所选子集的 item_ref→当前不可变 artifact 全集、每项认证审核事件及 actor、submitted/predecessor/successor
引用和摘要、截止版本，并在发布前复核所选项未被后继覆盖。当前命令产物只用于开发期技术 fixture，
不得作为经宿主认证的发行结果追加到 `provenance/release-index.dev.json`。
插件的旧 `complete_release`/`scirel.release-manifest.dev` 仍是单 draft 生命周期 fixture；
它不消费新的逐项 manifest，也不能作为本次索引的公开发行入口。消费者切换须随正式 `v1`
合同收敛完成，并在真实获批批次上核对。
未批准内容不能混入可信发行；首次可信发布须覆盖全部可见发布资产。
旧 52 项历史候选不再作为本轮整合和索引设计的盘点门禁；发行门禁仍以实际拟发行内容为准。

source-free 必须确认不从 SciRel 源 checkout import。当前脚本通过 .pth 暴露开发解释器 NumPy/SciPy/Pytest
目录，只证明不依赖 SciRel 源码，不证明其他包完全隔离；正式发行仍需固定离线 wheelhouse 和工具链。
分别报告开发测试、Agent 科学审查、人工认可和公开发行。
