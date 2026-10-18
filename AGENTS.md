# SciRel development

SciRel 是长期独立维护的 Python 科学关系库；不要套用相邻 CodeFusion 的 Rust 生产代码规则，也不要把它作为一次性资产汇总目录。

## 当前默认开发模式

- 普通任务默认处于 `development`：优化源码、公共 API、依赖边界、测试、文档、基准和构建配置，使用影响范围匹配的检查，并以一个可审阅的 Git change set 收口。
- “继续”“完成”“审查”“验证”本身不会启动发布流程。没有明确的 consumer、handoff、candidate cut 或 release decision 时，不构建 wheel、不更新 `release/CURRENT.json`、不生成发布回执、不跑全平台矩阵，也不推进 `devN`。
- 普通开发先确定一个主要 claim、一个 owned scope 和一个 stop condition，运行能够决定该 claim 的最小 affected 检查；达到 `passed`、`failed`、`blocked` 或 `NOT_RUN` 后收口。只有结果改变影响范围、暴露具体阻塞或用户明确要求时，才追加更宽测试、wheel、平台、catalog 或 AOCI；若本次产生 durable decision、blocker 或 next action，按收尾约定同步工作台。
- operators、TaskGraphs、文档和 catalog 的数量随当前 Git 树变化；数量只属于具体 manifest/revision，不是项目永久门禁。需要 wheel、文档和 catalog 时，才从同一个确切 revision 派生并绑定它们。
- 多个相互关联的小修复可以合并为一个变更批次；Git 历史保存中间状态，不为每个函数或每个文档修订单独制造版本和验收循环。
- SciRel 对公开算子和 TaskGraph 的实现、输入/输出合同、数值结果、失败语义和直接回归负责；Agent 只负责发现、选择、组合和编写胶水代码，不在胶水层复制科学算法或用组合测试替代能力本身的正确性证据。
- 先按影响范围选检查：局部实现运行 affected 测试，共享 API/依赖边界扩大到直接反向依赖；只有 named `integration_checkpoint` 且该 checkpoint 明确需要安装 artifact，或 `release_freeze` 时才构建 wheel、生成闭包和运行平台门禁。没有证据支持时，不把一次慢运行或一次成功安装升级成通用性能/跨平台结论。
- 平台 wheel 的拆分由实际 native/ABI 和依赖闭包决定：纯 Python 或已有通用 wheel 能覆盖的能力保持统一分发；只有实测存在平台边界时才增加平台特定构建和门禁。
- 非平凡修改或验证任务按 lifecycle reference 先确定 mode、主要 claim 和负责路径，并记录已有脏改动；证据复用及工作记录更新遵循该入口，不因“继续”或状态查询重复验证、重建 wheel 或同步不变状态。
- 普通开发只要求可审阅的 diff 和与 claim 匹配的检查；提交由用户交付或仓库工作流需要时再做，不因状态查询、继续或不变证据制造新提交。

- 区分 SciRel 开发项目与用户安装的 `scirel` 包：skill、审核状态、来源工件、开发工具和平台适配属于项目开发/集成层；科学 wheel 只包含所选科学 API、运行实现、必要组件/数据及分发元数据。历史试验不自动进入后续发行或成为永久门禁；仍被引用的来源与许可依据保留可取得。
- 不同整合批次、发行候选和维护版本在确有重叠或需要隔离验收时使用隔离分支/worktree、环境及构建输出；普通小范围开发继续使用当前工作树。以确切提交、审核内容和 wheel 摘要定义版本，不以分支名/worktree 路径定义批准。具体边界见 `docs/design/project-and-distribution.md`；创建 worktree 前检查已有工作区，不覆盖他人未提交修改。
- 任务消费或产生 D0/D1 来源交付时，先读 README、`docs/` 中相关架构/目录/流程、相关函数、科学测试和 provenance；不得把候选来源记录解释为人工批准。
- 任务消费或产生 D0/D1 来源交付时，官方来源只读；D0 在可编辑的 Git 分支/副本先完成或复用初始 AOCI 索引，再清理有依据的不完整/明显有问题代码，对稳定改动增量维护 AOCI/CodeGraph，最后交付固定 D0。记录相对上游的改动、剔除范围和理由；首建完成不自动触发全量语义重审，已知缺陷仍须按证据范围修复。已授权范围由 Agent 自主处理，不逐项申请批准；具体边界见 `docs/development-process.md`。
- 任务消费或产生 D0/D1 来源交付时，默认先尽量完成冻结 D0 项目的 D1，再保存可由新 owner 延后接续的项目交付供 D2/D3 使用；算子/图是阶段内部工作单位，不逐项触发整链。局部试点须明确范围，不代表项目完成。具体交付与异步接续见 `docs/requirements/scirel-workflow.md`。
- 已明确授权整项目交付时，才以全部核心物理能力的无源码安装替代为终点，并为该交付准备独立接收与合入。普通产品优化停在影响范围匹配的检查和可审阅变更；真实阻塞记录责任方、下一动作和重查条件。具体规则见 workflow 的“已授权整项目目标的连续交付”。
- 不依赖 CodeFusion、源项目 checkout、数据库或网络来执行科学函数。
- 任务消费或产生 D0/D1 来源交付时，分开选择来源运行、科学 wheel 运行和 SciRel 项目开发三类依赖。D0 先按证据确定保留入口，再按必要对照准备源码运行子集，不预装全部上游依赖；wheel 按最终实现的实际传递闭包声明；构建/测试/独立参考计算/文档工具留在开发侧。版本统一不等于清单统一，缺开发工具不算数值失败；细则见 `docs/design/project-and-distribution.md`。
- 任务消费或产生 D0/D1 来源交付时，D1 忠实复现冻结 D0 的现有功能和失败行为，不重做 D0 范围裁决，也不冒称完整原上游保真；允许封装随包的原语言实现，不要求纯 Python。保留 D0 中新发现的疑似错误记录触发条件与证据交 D2，D1 修复自身抽取缺陷。科学/数值正确性判断与修正属于 D2，D3 验证实际安装包的应用；全链保留上游→D0→SciRel 包的来源关系。
- 公共 API 按科学领域组织，任务图是组合函数；共享代码必须保持科学合同、默认值与失败行为。
- 普通 TaskGraph 依赖保持 DAG；反馈/迭代必须显式声明状态、顺序、停止条件和上限。资产发现使用分片索引与渐进披露，不建立需要全量 import 或把全部合同送入上下文的 registry。
- 日常内循环先用 `scripts/check.ps1 -Mode affected` 根据变更资产、共享源码和 TaskGraph 反向依赖选择精确测试；无法归属时先扩大到能覆盖未知归属的更宽测试层，只有影响范围仍无法界定时才回落到全仓。只有影响范围、发布门禁或公共基线要求时才跑全仓，不把全仓测试作为每个算子修改的默认动作。
- 新增回归应放在 affected selector 能识别的 canonical direct test 路径中，或在同一变更中补充 selector 归属；selector 未覆盖的测试不能支撑自动 affected 结论，但手动执行且范围匹配时仍可作为已报告的局部证据。
- 新增或改变公共资产，在 D2 比较、去重和代码稳定后、最终待审冻结前维护唯一 `scirel.asset-document.v1` exact document；实验内循环使用代码、YAML、注释/docstring 和现有证据锚点，不要求先写正式文档。catalog 只从已验证文档生成。不得从名称/源码猜补科学字段，不得把 CodeFusion 私有 owner/ref 或 adapter session/job 字段写入公共合同。
- 上一阶段交付只读；本阶段的修正、重复吸收和来源说明写入本阶段派生代码注释/docstring 或接续记录。正式审查文档面向人，不复制内部路径或过程备注。不用文件覆盖方式重复导入整批资产；对照当前 Git 基线逐项整合，保留其他贡献者的修改。
- 改变科学行为先写失败回归；保持旧数值断言和容差，不能为了通过测试弱化它们。
- 改动后运行与声明匹配的相关测试；只有明确需要安装 artifact 的 named `integration_checkpoint` 或 `release_freeze` 才构建 wheel，只有 `release_freeze` 才在没有源码的环境验证全套测试和公共 API。
- 冻结的来源、审核和准入记录不可改写；源码演进另记版本和审查。语言/格式调整也要保留可核对差异。
- 每个来源项目使用独立容器，环境定义随交付保存；源码、依赖/工具、探针、缓存、证据与产物分开，冻结预处理与索引供各 worker 复用，不逐区域重装或重建。依赖下载通过开发机本地代理；服务器不构建。清理前先列出精确范围进行 dry run；用户明确清空旧工作且不备份时遵从该范围，保留指定来源、工具与凭据，不把历史运行保留规则变成额外批准门槛。

## AOCI 接入与增量维护

- 先按任务判断需要什么证据，再核对实际 checkout/分支、目标对象与索引范围是否匹配。状态查询、调度和交付接续优先读取轻量 handoff 与实时运行状态；开发工具修改读取相关源码和依赖；科学内核修改读取该资产合同、实现、测试和依赖。仓库采用 AOCI 不表示每个任务都要加载完整索引。
- SciRel 采用 AOCI 维护开发项目认知；各 checkout/worktree 的 MCP 必须绑定其实际仓库根，使用本机已核验的稳定二进制，保留其他宿主设置。具体方法见 `docs/design/aoci-index-maintenance.md` 和本机 `aoci-development` skill。
- `aoci.txt`、`aoci.meta.txt`、`aoci.code.txt` 与本文件属于可版本化认知资产，不得 Git-ignore；机器配置和运行状态按 AOCI 布局忽略。认知资产不进入用户科学 wheel，也不替代 exact document、provenance、科学测试或人工批准。
- 仅在任务确需相关系统全景或严格的当前完整认知证明时，核对当前 AOCI Rules、运行根、服务身份和工具实际支持的 scope，再显式启动完整 Overview 链。压缩后旧完整认知证明失效，不等于当前任务必须重载；可以根据已核对的源码和任务证据继续工作，但不得声称已恢复完整认知。历史 checkout 的全量索引不代表源项目、洁净主线或容器实况；`scope=project` 不表示任意路径过滤。
- 本节的任务适用性判断先于下方工具生成块或 Rules 中的默认调用前置；未来 init/升级重新生成托管块也不得恢复无条件新 Run/压缩重载。此优先级只决定是否选用该操作，不改变已选操作的传输、写入、安全与证明判据。
- 新来源项目的整合以科学家族/稳定批次为单位。代码及相关文档、测试、合同稳定后，通过当前 Guide/Maintain 领取带证据摘要的完整批次，由模型阅读证据并创作语义条目，更新到所有 remaining 清零；不按每个算子重启整链，不用模板或遍历脚本生成语义。
- 新增、变更、删除与重命名均须维护；稳定批次绑定明确基线，保留重命名两端并核对旧、新反向依赖，测试使用 affected 与未知归属的全套回落；`-BaseRef` 不包含本地未提交变化。AOCI 增量不代表 catalog 已实现增量构建。合并或绑定源码变化后重新取得当前候选，不复用旧 preimage。既有 Baseline 不能靠强制 scan 或手改正式 Volume 消除漂移；范围调整、压缩/分卷及观察项审核走当前受治理协议。
- 索引建立或维护批次收尾时，检查 Verify、Check、Guide 与 Scope/Budget 的实际状态，分别报告索引覆盖、待维护/观察项、上下文预算和业务验证；批次大小只控制传输与原子写入，不可截断覆盖。大规模增长先测量预算再调整索引粒度，不静默排除科学资产、文档或测试。

<!-- aoci:begin -->
## AOCI 仓库认知

AOCI 为本仓库维护一个稳定、可版本化、可增量更新的仓库级认知层，供模型跨任务复用对系统的理解。

本区块的认知建立协议只在当前任务选定且范围匹配的 AOCI 操作中适用；新 Run、上下文压缩或位于本仓库本身，不构成完整 Overview 的调用条件。先遵循上面的任务路由，再选择必要的认知操作。用户与项目决定 Host 的任务范围和恢复方法；选择运行完整链或写入事务后，工具的真实传输、身份、安全和证明判据仍必须遵守，不得伪造满足条件。

`aoci.txt` 是面向模型的结构化认知索引。它以每个受管理文件、数据库表或其他受管理对象一条独立 Entry 的方式，用符号标签与 F/R/A/S 语义表达对象的核心职责、重要关系、对外契约，以及理解或修改系统时必须知道的非显然约束和设计决策。

Header、目录段和全部 Entry 共同组成完整仓库索引，可以覆盖前端、后端、配置、数据库结构及其他受管理内容。受管理内容发生变化时，通常只需维护受影响的认知条目，不需要重新生成整个索引。

AOCI 提供系统架构、对象职责、重要关系、对外契约和关键约束的高密度视图。

### 工作原理

AOCI 采用“模型生成、模型读取”的认知闭环。

Header、Entry 和 Curation 语义的创作只按当前机器签发的 Plan 与实时 Guide 执行；由 Host 模型基于当前绑定证据独立完成。

Entry 的语义必须来自模型对真实证据的理解。不得仅依据路径、文件名、扩展名、AST、符号列表、依赖扫描、正则、固定模板或规则引擎推导、预填、拼接或改写索引语义。

对 Fresh Bootstrap，只按当前机器签发的 Plan 和实时 Guide 执行。当它们要求创作时，Host 模型创作 Root、Meta、Tag 和 F/R/A/S，提供 authoring-run 声明，并把它绑定到 Plan、Evidence 与完整 Candidate。不得要求 AOCI 填写 `origin=host_model`、制造 Receipt 或把程序生成的 Framework 当作语义。本文件不自行重建 Onboarding 流程。内部批次不是用户决策；只有遇到既有批准边界或真实的安全、漂移、CAS、Recovery 条件才停止。

### 最小使用入口

- `aoci_rules`：取得当前AOCI版本的会话运行合同。
- `aoci_overview`：在任务确需时，建立或恢复与实际支持 scope 匹配的完整认知；不是所有任务的前置步骤。
- `aoci_maintain`：受管理对象达到最终稳定状态后检查认知是否需要维护。
- `aoci_update_entry`：提交与当前证据和源码摘要绑定的完整语义更新批次。
- `aoci_report`：仅当当前布局和工具状态支持时，在证据不足、无法可靠生成语义时登记待办，不猜写。

其他MCP工具、CLI命令、参数和专项流程，以当前工具说明、Guide和 `--help` 返回内容为准，不在本文件中重复完整手册。

本区块规定任务适用性、仓库接入、认知使用和收尾原则。`aoci_rules` 承载所选 AOCI 操作的当前会话合同，Guide实时输出承载当前Plan的执行顺序与停点，工具Schema、Spec和Validator承载机器结构与判据。Host 不因通用工具说明中的默认认知前置而扩大用户任务；若未执行其完整证明前提，应保留未验证状态，不改写机器事实。Prompt、Description、README和静态文档不能伪造传输、写入、安全或证明结果。

### 建立、生成和恢复认知

1. 每个新的 Agent Run 开始时，应先判断：

   - 当前任务需要运行状态、局部源码/合同，还是相关系统全景或严格完整认知证明；
   - 实际 checkout/分支、目标对象与现有索引身份和范围是否匹配，不能以父目录或另一工作树的索引替代；
   - 只有需要完整认知时，再判断是否存在可用的完整索引，以及上下文是否持有与当前根、索引版本、服务和范围匹配的可靠完整认知。只需局部证据时按任务读取，不先装入全部科学资产。

2. 当前任务确需相关系统全景或严格完整认知证明、范围匹配且已有可用完整索引，但当前 Run 没有可靠完整认知时，先取得 `aoci_rules`，再显式调用 `aoci_overview`。scope 只使用当前工具 Schema 实际支持的值；不猜测任意目录过滤，也不把历史 `all` 或 `project` 的结果当作其他项目或运行环境的认知。

   完整认知仍可靠时直接复用。局部不确定本身不要求机械重读系统全貌。

   本 Run 从已知 Host 上下文压缩恢复时（包括宿主注入的压缩摘要），此前的完整认知证明不再可靠；回到第 1 条判断当前任务需要的证据，而不是无条件重载。handoff 可以保留任务决定、确切源码/交付身份、范围、待办、receipt 身份及未完成写入/Recovery 状态，但不得保留或摘要正式 Whole-Index、Overview Header、Entry、Chunk、Challenge 或 Attestation 正文来充当当前完整认知。若继续的是状态查询或局部 source-bound 工作，核对相关证据即可，不需要为此发起 Overview。只有任务随后需要完整认知时，才在必要时重取 Rules，使用 `refresh_reasons=["context_compaction"]` 和新的 `refresh_event_id` 请求工具实际支持 scope 的完整 Overview；`check_only` 或认知 probe 不能替代所需的完整证明。已发起的完整链必须按下述续传、确认与一次 Attestation 协议完成。

   AOCI可以针对 `context_compaction`、项目 `cognition_refresh_threshold` 下的机器 `semantic_threshold` 或主要 `phase_transition` 提供checkpoint与认知状态事实。只需要这些紧凑事实时使用 `check_only=true`；这些事实只向Agent提供建议，不替模型决定是否需要系统全貌。

   Agent显式调用普通 `aoci_overview`（未设置 `check_only` 或为false）时，只要能形成一致的CognitionSet，AOCI必须完整交付请求scope。不得因为已有receipt、阈值未达到或没有待处理刷新原因而抑制正文。正式认知Dirty或Stale时仍交付正文，但必须标记不可靠。存在未决恢复或无法形成一致snapshot时失败关闭，不返回混合正文。

   普通Overview返回 `continuation_required=true` 时，必须原样提交 `next_cursor` 并自动继续到 `completed=true`。不得询问用户、开始业务任务或给出阶段性系统结论。Host截断、缺块、重复、乱序、cursor失败、Index变化或`chunk_tokens`变化时停止本次认知链。Attestation完成前不得用Memory、源码、Spec、`aoci.txt`、历史会话、scope、search或Entry读取修补或补充Whole-Index认知。Challenge ordinal是正式Entry序列中的1-based位置；Header内容、注释、空行、Section/Overview/Chunk Marker、Receipt与Metadata均不计数，Chunk Receipt ordinal使用同一序列。Attestation必须原样回绑本次Challenge发布的当前`index_sha256`、`entry_sequence_sha256`与`entry_count`；旧Index、旧Entry序列、旧数量或旧Attestation均无效。完整链结束后只正式提交一次既有模型认知Attestation；同一响应只允许一次不改变语义答案的JSON Schema或字段格式修正。对象、Tag或F不匹配即失败且认知吸收不确定，不得语义重试或旁路补答。首次认知失败时还不得执行Root/Meta、Migration、全局布局或其他未重新绑定的系统级决策。上下文压缩刷新若传输完整、认知身份不变、治理对齐且没有Recovery或第三方冲突，即使Attestation为partial或fail也消耗该refresh generation，并继续原任务，不再自动重读Overview。`system_mastery_percent`只自评系统框架——架构、职责、强关系、稳定外部契约以及高熵安全和维护约束——不表示完整实现或运行实况知识；机器索引覆盖率必须分开。默认只向用户输出由本次真实覆盖率、Challenge、块数、Token和掌握度生成的规定成功或失败一句话。Host截断时提示用户把 `overview_delivery.chunk_tokens` 设置为更小的合法值后重新开始，不得自动修改。

   加法认知等级必须与严格证明字段分开解释。`delivery_verified`表示已加载Index且Host交付已确认，但完整认知验证仍未完成；应表达为“已加载且交付已验证”，不得描述为“没有认知”或“没有理解系统”。`cognition_verified`要求Attestation通过（Challenge至少80%的ordinal完全正确且对象身份至多失手一处），`cognition_governed`还要求治理对齐。通用完整读取失败句只用于真实交付故障。

   当Overview响应包含可选`cognition-state/v2`投影时，必须分别解释各维度。其Level止于`model_cognition_usable`；`strict_attestation_verified`、`governance_aligned`与`current_system_cognition_reliable`都是独立状态，绝不参与该Level。ordinal、对象身份、Tag或核心F不匹配可以导致严格Attestation失败，而模型认知仍然可用；不得仅凭这种不匹配就宣称模型没有理解系统。只有`current_system_cognition_reliable=true`允许无保留地声称当前完整系统认知可靠。投影缺失时继续使用上述Legacy解释。

   普通的只读审计、分析、检查、不修改代码或不提交、不push，不自动等于严格零写入，也不改变上述认知有效性判断。Codex Memory和历史Skill只能辅助恢复经验、用户偏好与调查方向，不能替代与当前仓库根、索引摘要、AOCI服务身份和认知范围匹配的当前认知收据；项目AGENTS和当前AOCI身份在AOCI状态上优先于历史Memory。

   只有用户明确禁止Ledger、元数据、`.aoci`运行资产及任何文件写入时，才按严格零写入处理。若必要的认知建立与该边界冲突，必须报告冲突并请求用户裁决或建议使用隔离副本，不得静默以Memory替代当前仓库认知。

3. 仓库没有可用的完整索引，或当前只有最小骨架、Header不完整、Entries未完成、必要Curation尚未裁决时，如果需要建立正式完整AOCI索引，先取得 `aoci_rules`，然后进入当前AOCI Guide。由Guide依据仓库真实状态决定下一阶段并完成必要安全步骤。

   `aoci_maintain` 不替代索引建立流程。

   不在本文件中自行重建或硬编码完整索引生成状态机。

4. 在长程任务中，模型负责保留与当前任务有关的身份和状态，并按需选择刷新：

   - Host报告上下文压缩或模型已知系统全貌丢失时，旧完整认知证明失效，重新判断任务适用性；需要相关全景或严格证明时才按第 2 条发起 `context_compaction` 完整链，AOCI不能自行推断Host事件；
   - 进入真正的主要阶段且需要向 AOCI 声明认知事件时使用 `phase_transition`，不得把函数、测试运行或小步骤当作阶段或自动加载理由；
   - 只需要机器 checkpoint 事实时可在有用的稳定检查点使用 `check_only=true`，不把这些事实当成完整认知证明；
   - 由Agent按任务需要显式选择工具支持的 scope 或完整Overview，不用无关全量读取替代局部源码、合同或实时状态；
   - 在维护和对齐完成前，保留AOCI报告的Dirty或Stale可靠性状态。

### 任务收尾与认知维护

5. 纯只读问答、分析、版本核验，或没有产生受AOCI管理对象变化的任务，不需要调用维护工具。当前AOCI服务版本以实际响应的`cognition_receipt.mcp_service_version`为准；二进制路径读取当前宿主实际采用的项目配置（例如 `.codex/config.toml` 或 `.mcp.json`），CLI不必在PATH上。磁盘配置和 CLI 版本不能代替当前 MCP 服务身份。

6. 发生受AOCI管理对象变化时，待其达到本次任务的最终稳定状态后，只调用一次 `aoci_maintain`。不要在每次中间修改后逐文件维护。

   维护需求与当前任务的阅读范围分别判断，不为保持索引一致而强迫读取无关全量。用户明确限制本次不改正式索引或不运行维护时，保存变更身份和待对齐范围，按第 9 条如实报告；不得冒称索引已对齐，也不手改正式条目绕过治理。

7. 若维护结果返回真实语义候选，Host 模型必须基于每个候选绑定的对象和必要证据，独立创作完整标签与F/R/A/S更新。通过 `aoci_update_entry` 一次提交当前机器签发批次的完整候选集合，同时原样保留每项 `source_sha256`、`candidate_id` 与对应domain批次身份。`max_entries`只限制单次请求和原子事务，不限制logical plan、Whole-Index或Managed Scope。`remaining`非零时，在当前批次成功Apply后重新调用Maintain并从新preimage继续；绝不能为满足transport上限缩减Index覆盖或自行截取返回批次。

   没有足够证据且当前布局支持 `aoci_report` 时，使用它而不猜测、套用模板或为消除待办而生成缺乏证据的认知。

8. 必须遵守工具返回的结构化状态和安全边界：

   - `repair_required`：只修复明确命中的候选，再重新提交当前机器签发的完整批次；
   - `stopped`：结束当前写入尝试并检查 `failed_step`、错误、正式写入证据与Recovery。auto模式下，已证明零写入则记录closure并重新Plan；完整Intent和可证明postimage则Resume；策略要求Rollback且preimage可证明则精确恢复后重新Plan。只有证据不足、第三方正式字节冲突、需要审批或外部动作，或命中其他真实安全边界时，才停止整个用户任务；
   - 冲突、审批、人工裁决、权限和安全信号不得忽略；
   - 已经对齐后不得重复维护或重复写入；`refresh_ready_for_overview` 是checkpoint事实，由Agent决定是否为下一阶段请求普通完整Overview。

   维护完成后如果又修改了任何受管理对象，之前的维护结果失效，应在新的最终稳定状态重新完成收尾。

9. 用户只限制业务文件范围，但没有明确禁止仓库托管资产时，AOCI托管资产可以在收尾阶段为保持认知一致而更新，并应在审计和提交中与业务文件区分。

   用户明确禁止修改 `aoci.txt`、`.aoci`、元数据或任何额外文件时，以用户限制为准，不得写入，并如实报告剩余不一致。

### 专项流程

初始化、完整索引生成、Header生成、Entries生成、数据库结构索引、Curation、人工评审和故障恢复，只按当前AOCI Guide或工具在对应阶段返回的指令、命令和安全停点执行。

不预加载、不猜测，也不自行重建这些专项流程。平台调用方式、请求格式、批次上限、审批规则、索引格式细节和恢复步骤由对应Guide、工具说明、模型Prompt和CLI帮助按需提供。
<!-- aoci:end -->
