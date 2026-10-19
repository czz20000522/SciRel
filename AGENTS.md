# SciRel development

SciRel 是长期独立维护的 Python 科学关系库；不要套用相邻 CodeFusion 的 Rust 生产代码规则，也不要把它作为一次性资产汇总目录。

## 当前默认开发模式

- 普通任务默认处于 `development`：以当前 Git 源树为真相，先确定一个主要 claim、owned scope 和 stop condition，再做影响范围匹配的检查。模式、证据复用、停止、artifact 和版本规则以 `skills/development/references/development-lifecycle.md` 为唯一流程来源。
- 生命周期只有三个边界：`development` 只优化源树并运行 claim 匹配的最小检查；`integration_checkpoint` 只在明确的 consumer、handoff 或 owner 请求下生成有界 artifact/安装闭包；`release_freeze` 只在明确的 candidate cut、发布或 release decision 下冻结并验收。
- 未发布阶段的普通工作不会自动进入发布流程，也不会因为“继续”“完成”“审查”或“验证”改变模式。没有明确 checkpoint 或 release decision 时，不构建 wheel、不更新 `release/CURRENT.json`、不生成发布回执、不跑全平台矩阵、不推进 `devN`。
- 长程 goal 是 claim 队列，不是执行调度器。继续同一 claim 时只做轻量身份检查；达到 `passed`、`failed`、`blocked` 或 `NOT_RUN` 且没有新范围或阻塞就收口，不重复相同检查，也不自动启动下一项优化。
- incubation 期间 capability、operator、TaskGraph、document 和 catalog 的数量随 manifest/revision 变化；数量不是永久门禁。需要 projection 时从同一确切 revision 派生并绑定 wheel、文档和 catalog；普通开发不为追赶旧 projection 重建它们。
- 版本按能力线和批次处理：首次公开发布前只用 Git 累积工作，不推进历史 `devN`；公开后，兼容修复、数值修正、性能优化和内部重构可合并为同一维护批次。只有大范围新增或删减公共能力，或公共 API、失败合同、依赖/平台/分发边界发生不兼容变化时，才开启新的能力线；单个函数修改、文档小修或计数变化本身都不是大版本边界。具体切候选和版本选择见 `docs/design/scirel-release-batching.md`。
- 按 SciPy 式标准库结构维护一个当前源树：`src/scirel`、直接测试、公共文档、构建/测试工具和依赖声明各保留一套 Git 表示；Git 历史保存旧版本，不复制平行 wheel、文档或 catalog 树。SciPy 只提供结构参考，不决定 SciRel 的 Python 下界、依赖 pin、classifier 或 native 分发。
- SciRel 对每个公开 Operator 和 TaskGraph 的实现、输入/输出合同、数值结果、失败语义和直接回归负责；Agent 只发现、选择、组合和编写 glue，不复制科学算法，也不用组合成功替代能力正确性。
- 日常检查采用 selector-first：先运行 affected selector；只有 selector 显示共享边界或 claim 明确需要时才追加反向依赖、API/import/failure 或 benchmark；未知归属才扩大测试层。性能声明由 owner 选择最小可复现命令或脚本；性能基准没有统一入口或运行条件时只将性能子声明记为 `NOT_RUN`，保留 affected correctness 结果。只有 named checkpoint 或 `release_freeze` 才生成安装 artifact 或闭包；checkpoint 只运行 consumer/claim-scoped 的安装与闭包检查，只有 `release_freeze` 才运行全平台门禁。
- exact document/catalog 是 handoff、checkpoint、review preparation 或 release 的投影。普通开发可用 docstring、注释和直接测试；形成 exact-document projection 时检查 document→export 与 function-export→document 双向绑定。类与异常由 public-surface/asset-document 测试覆盖。
- 平台 wheel 的拆分由实测 native/ABI 和依赖闭包决定；纯 Python 或通用依赖能覆盖的能力保持统一分发。Linux amd64 + CPython 3.14 是开发基线，其他平台只能由明确 claim 提供证据。运行时闭包 receipt 必须明确 `BOUND`/`UNBOUND`；`BOUND` 还要求实际执行过隔离子进程，脏源、身份漂移、无 child 测量或目标不匹配都保持未绑定。
- skill/AGENTS 维护与候选 diff 审查是两个独立 claim：先完成 skill 的轻量合同检查和结构检查，候选审查保持只读；候选 diff 只有在另有明确产品 claim 时才进入产品变更。受管文件达到最终稳定状态后只做一次 AOCI maintenance。checkpoint 产生的 wheel、文档、catalog 和 receipt 必须绑定同一个确切 `source_revision`。
- 任务消费或产生 D0/D1 来源交付时，先读相关 README、架构、函数、科学测试和 provenance；官方来源只读，保留来源改动、剔除范围和失败证据。没有 exact D1 packet 时不制造 D1 manifest 或完整 denominator。
- D1 忠实复现冻结 D0 的现有功能和失败行为；D2 负责科学比较、修正和归一化；D3 验证实际安装包的应用。来源运行、科学 wheel 运行和项目开发依赖分开选择，wheel 只声明最终实现的实际传递闭包。
- 普通 TaskGraph 依赖保持 DAG；反馈/迭代显式声明状态、顺序、停止条件和上限。资产发现使用分片索引和渐进披露，不建立需要全量 import 或把全部合同送入上下文的 registry。
- 改变科学行为先写失败回归并保持原数值断言和容差。冻结来源、审核和准入记录不可改写；源码演进另记版本和审查。清理资产前先做精确 dry run。

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
