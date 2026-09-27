# SciRel L1 到 Release 需求

## 目标

SciRel 负责从保存的 L1 产物开始，完成语义理解、与冻结基线及当前未发布候选池比较、候选准备、专家审核、批准后整合和 release。CodeFusion 是中性的 Agent 宿主，不拥有 SciRel 的科学状态和资产语义。

语义理解和标准化由加载 `scirel-integration` skill 的模型完成；代码不尝试用固定状态机、脚本或 JSON patch 代替这项工作。模型只在冻结基线之外形成候选文档、候选代码和候选测试。专家批准后，独立的实施步骤才把批准内容应用到 SciRel。

## 生命周期

```text
candidate
  -> automated_checking
  -> automated_ready | automated_rejected
  -> draft
  -> review_pending
  -> review_in_progress
  -> needs_evidence | rework_requested | rejected | approved
  -> approved candidate integration/build
  -> released
```

候选包可以包含数十或数百个 Operator/TaskGraph；上述审核状态应逐项解释，而不是给整个批次加一把锁。上传前的 `draft` 可以由模型整合、替换或撤回；上传后每项 `review_pending` 都已有确定的初始内容版本，队列中没有模型继续改写。查看某项完整详情只记录该专家看过的版本，不改变同批其它项。领取是另一件事：它记录本轮修改的基点并授予该项的独占写租约；未领取的授权专家仍可只读查看。返工保留先前版本和审核记录。SciRel reviewer body 已实现逐资产投影、只读打开、精确版本决定、完整 successor 和批准子集返回；租约、版本历史与 diff 仍由 CodeFusion 通用工作台实现和验收。

候选生成与候选审核/固化是两个异步流程。模型提交批次后即可结束运行，不等待耗时不可控的人工审核。逐项 `approved` 只使该项有资格被上传者取回并进入独立固化流程，不表示整个批次已批准或已经修改 SciRel。只有批准项及其依赖闭包完成固化且 release 构建成功，才能产生 `released`。candidate、draft、候选代码和候选测试不得在批准前进入维护基线、运行时 catalog 或 wheel。

## 领域对象

- **L1 bundle / payload**：来源项目拆解阶段保存的真实输入。目录或 ZIP 先由 SciRel 的转换入口生成 `scirel.l1-bundle.dev`，逐文件保存安全相对路径、原始内容和摘要；`scirel.import_l1` 再从这个受 source Artifact digest 绑定的 bundle 映射资产。CodeFusion 不得手工构造资产列表或猜测 domain 映射。SciRel 不依赖源项目 checkout、CodeFusion 数据库或网络，也不在转换或导入时执行输入代码。
- **L1 inventory**：`scripts/build_l1_inventory.py` 提供的可选结构探针。它可以帮助定位相对路径、直接测试和显式依赖缺口，但不是模型整合 L1 的必经输入或标准化协议。
- **CandidatePackage**：绑定 `run_id`、来源 artifact、source digest、单一 `project_id`、候选资产和自动检查结果。多项目 inventory 必须先拆成 `to_project_l1_payloads()` 的独立 payload，不能在一个 candidate 中混合推进。
- **Candidate comparison view**：冻结 SciRel 基线、全部当前未发布候选和本次 L1 输入的联合检索视图。它用于提前发现重复、可合并项和冲突；未发布候选不是可运行资产，也不改变权威基线。
- **StandardizationSubmission**：模型完成语义工作后的正式交接，绑定 exact candidate/source、SciRel Git base、未发布候选池快照、harness/model/skill 身份，以及逐项文档、代码或无代码理由、测试、处置、依赖、证据和 gaps。它不携带或覆盖自动检查结果。
- **StandardizedDraft**：确定性门禁接受 submission 后形成的开发期对象。资产文档作为专家主入口，逐项三件套和模型运行身份保存在其 evidence 中；批次只承载来源和比较上下文，不应成为审核锁粒度。
- **Item revision / review event**：每项 `scirel.review-item.dev` 关联资产文档、代码/测试证据、依赖和 gap；review action 绑定 exact predecessor Artifact，successor Artifact 成为下一 current version。观测、领取、保存、清空修改、放回和提交事件及 diff 由 CodeFusion 保存，同内容可复用快照。
- **ReviewDecision**：仅由显式 `plugin.review.action` 提交产生，绑定 item ref、最终 Artifact ref/digest、host 认证的 reviewer actor、outcome 和说明；同一批次可独立形成多项结论。旧 `ReviewDecision`/`record_review()` 仍只服务单 draft release fixture，不作为工作台逐项事实。
- **ReleaseManifest**：绑定 candidate ID/digest、draft digest、approved asset IDs、catalog ref/digest、wheel ref/digest 和实现版本。
- **Workflow state snapshot**：由 SciRel 序列化当前 candidate、自动检查结果、draft/review 历史和 release，供工作台查询或进程重启后恢复。它不承载宿主平台字段。

SciRel 可以通过宿主 artifact store 保存 `scirel.workflow-state.dev` 快照；这只是状态恢复记录，不是第二套科学资产真值，也不要求 SciRel 引入数据库。

## 自动检查

自动检查至少覆盖资产合同/实现记录、结构、依赖、许可证/来源记录、构建、直接测试 replay
和标准文档完整性。检查结果只能说明机器门禁范围内的事实，不能替代专家对科学适用性的判断。

检查失败必须保留结构化原因。存在失败或缺口时，workflow 不得创建可审核 draft。

第一阶段产物不要求完美。`AutomatedCheckResult` 只回传确定性检查事实和证据引用，不能携带
源码、合同、测试映射或依赖的补丁，也不能修改 candidate。模型按照 skill 在隔离的 SciRel
工作树中理解并修复问题，然后对实际变更重新运行适合该问题的检查。未解决的问题继续阻断，
并可按 `next_action` 暴露为 `retry`、`rework_requested`、`needs_evidence` 或 `rejected`。
即使 checks 全部通过，只要结果明确要求 `needs_evidence` 或 `rework_requested`，candidate
仍保持相应阻断状态，不能被自动标记为 `automated_ready`。
对 L1 inventory 形状的结果还要由 SciRel 重新检查直接测试映射、TaskGraph 依赖引用，
并确认 TaskGraph 依赖保持 DAG，不能仅凭执行器声明的 `passed` 清除这些缺口。

## 标准化与审核

工作目录和模型推理过程不固定，但上传边界必须形成
`scirel.standardization-submission.dev`。`SciRelWorkflow.submit_standardization()` 重新校验
candidate/source digest、SciRel Git base、候选池与 skill digest、L1 资产记账和每项三件套内容摘要，
成功后一次性产生 `review_pending` workflow。该门禁只验证绑定和结构，不把模型自报的命令结果
解释为科学正确或平台执行事实，也不运行模型。

上传者将一个批量候选交给独立工作台，并在项目权限内选择对全部获准审核员可见或指定审核员可见。列表、详情、三件套 Artifact 和动作的权限都必须在服务端复核；可见不等于可写或已领取。专家按单个 Operator/TaskGraph 自行领取，工作台按 item ref 签发带代次的写租约；同一项只允许一个有效持有者，不同项可并行。领取事件绑定当时的内容版本，作为本轮清空修改的返回点。过期或旧代次提交不得覆盖当前版本。

上传时确定的逐项初始快照已经可追溯；首次只读打开完整详情记录所见内容版本，不需要为了冻结内容改变它。持有租约的专家可以保存修改，形成关联前一版本的新提案，不能覆写已有版本；工作台需按文档、代码和测试展示版本间差异。清空本轮修改应恢复到领取时绑定的版本，不删除已有历史。放回队列时保存当前内容版本（未变化则复用已有版本）、记录放回事件并释放租约，该项仍未完成审核，供其他专家领取；放回不是提交，也不能隐式批准。只有显式提交审核动作才记录完成结论及其最终确切版本（未变化也可复用版本），并释放租约。即使内容相同，领取、放回和提交事件仍分别保留；不必为每个事件复制内容快照。TaskGraph 依赖的 Operator 尚未获批准或已返工时，可以继续只读分析该图，但不能绕过依赖闭包固化。

工作台把每项已提交的结论、版本关系和差异集中交还上传者；放回但未提交的修改留在待审核队列。上传者是收集与固化协调者，不因上传而自动成为科学批准者。逐项最终批准必须由有权限的专家明确作出；意见冲突需要有权裁决者处理，不以数量或平台 action receipt 自动投票通过。允许取回已完成的子集，不要求数百项全部审核完毕才开始独立固化。

模型在上传前准备候选时必须同时检索冻结基线、当前未发布候选池和本次 L1；发现重复或可合并时，优先整合上传前草稿以减少重复审核。已上传批次的内容不能由模型静默改写，不以专家是否已经打开或领取为条件。需要模型重新准备时另起短任务，产生可追溯的新候选，并由上传者明确决定后续上传和关联方式。

上传前草稿的撤回只是候选存储取消引用，不新增科学审核状态。已经上传的候选不能以“专家未打开”为理由静默替换或消除其初始版本和平台事件；需要撤回时由有权限的上传者显式操作并保留可追溯记录。

候选文档是专家审核的主入口。新增或改变公共资产时，其中拟议的 canonical asset document 必须使用现有 `scirel.asset-document.v1` 合同；候选代码和候选测试用于核对其主张。缺少科学关系、单位、坐标、适用域、失败语义或证据时登记 gap，不从名称、源码相似度或项目经验猜补。

审核工作台只展示 SciRel 的 draft、证据、依赖和候选差异。CodeFusion 提供 UI、身份和动作投递；审核结论写入 SciRel workflow 记录。

批准只授权候选中明确列出的内容。实施时发现需要改变科学合同、API、依赖或测试主张，必须形成新候选或回到专家审核，不能静默扩大批准范围。

## 批准后固化与候选冲突

批准后由新的短任务完成固化，原 Claude Code、CodeFusion 或 Codex 运行不需要等待专家。第一版按串行队列处理已批准候选；只有受影响科学身份和依赖闭包明确不相交时，才允许并行固化。

每次固化先把候选审核时的 Git base 与当前 SciRel 基线比较：

1. 相关资产、公共合同、依赖、TaskGraph 和 patch hunk 均未变化时，原样应用批准的候选代码和测试；
2. 基线有无关变化但批准 patch 仍能原样应用时，应用后运行 affected tests 和候选声明的直接测试；
3. 同一科学身份、公共合同、依赖闭包、TaskGraph 或 patch hunk 已变化时，停止固化，不采用 last-write-wins；
4. 冲突候选基于最新基线重新比较并形成关联的新候选。即使它因此变成重复或直接复用，也必须把新处置作为文档候选交给专家，不能静默丢弃；
5. 旧批准记录保持冻结，只证明旧候选曾获批准，不能自动批准新代码。

这里不新增复杂的长期状态机。当前 `approved` 即“已批准、等待固化”；固化成功后才能调用 `release`。冲突时保留原 workflow 和固化失败证据，另起一个候选 workflow。工作台把“已批准待固化、固化冲突、已发布”作为现有记录的投影视图即可。

允许候选增量堆积在 artifact、review directory、branch 或 worktree 中。即使候选目录位于 SciRel 仓库，它也必须排除在公共 import、catalog 和 wheel 之外；否则就已经是在修改维护基线，不能等到周期性功能审查再补审核。

## Release 门禁

目标批量流程的 release 前必须满足（reviewer body 已能返回逐项批准子集；批准后固化器仍需消费该子集）：

1. 每个拟发行 item 的最终确切版本已逐项 `approved`，且其候选代码/测试已按批准文档应用到 SciRel；未批准项不随同批次进入发行；
2. 拟发行项没有未解决 gaps，且 TaskGraph 的必需依赖已在维护基线或同一批准固化闭包内；
3. 每个拟发行资产都有稳定 `asset_id`；
4. 实际 diff、资产文档和测试与逐项批准版本可核对，catalog、wheel 和 release manifest 来自同一构建结果；
5. manifest 中的 candidate/batch、逐项审核版本与批准记录的 digest 均与实际 artifact 一致；
6. release version 与 catalog/document implementation version 一致。

开发期合同使用 `.dev` schema；首条稳定闭环后统一冻结为 `v1`，不保留旧 `.dev` 流程兼容分支。

## 测试要求

每个 workflow 变更必须覆盖直接状态转换测试。逐项审核实现需另外覆盖：同批两项并行领取互不阻塞、同项只能有一个有效写租约、未领取只读、上传后无后台改写、首次打开记录该项所见版本而不修改内容、领取版本作为清空修改的基点、保存后 diff、放回保存修改并释放租约但不产生审核结论、提交绑定最终版本、相同内容复用版本但保留事件、过期代次与旧快照不能提交、批准子集不能带入未批准依赖。科学资产测试仍由 `scripts/check.ps1 -Mode affected` 根据资产和 TaskGraph 反向依赖选择；无法归属的 workflow、plugin 或公共合同变化 fail closed 到全套测试。

生命周期 fixture 可以在没有 CodeFusion、数据库、网络和源项目 checkout 的环境中验证 draft/review/release artifact 关联；它不声称能替代模型从真实 L1 完成科学整合。
