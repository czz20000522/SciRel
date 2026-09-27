# SciRel 与 CodeFusion Plugin Contract

## 两个接面

SciRel 与 CodeFusion 只有两个需要长期维护的接面：

1. 中性 Agent 调用：CodeFusion 像 Codex、Claude Code 一样承载模型执行；
2. 专家审核 UI：CodeFusion 提供通用页面、身份、artifact 和动作投递，SciRel 提供领域内容。

CodeFusion 不实现 SciRel 的 L1 解析、去重、变体、合并、标准化或验证策略，也不新增
SciRel 专属 task、projection、finalize、receipt 或数据库状态。

## 真实 L1 包交接

CodeFusion 的通用 body runner 传输 UTF-8 JSON，因此原始目录或 ZIP 不能被手工改写成一个只含资产名的 JSON，也不能把 ZIP 二进制直接冒充 body。SciRel 提供 `scripts/build_l1_bundle.py` 和同源的 `scirel_workflow.l1_bundle` API，把一个 ImportIntake 项目目录或 ZIP 转为 `scirel.l1-bundle.dev`：

- 每个非生成文件保存规范相对路径、原始字节的 base64、字节数和 SHA-256；整个文件树另有稳定 `bundle_digest`；
- `scirel.import_l1` 校验全部内容身份后，从 `operators/<name>` 与 `task_graphs/<name>` 映射资产、三件套路径和 `task_graph.yaml` 的显式 `asset_ref`；
- candidate 的 `source_artifact_ref/source_digest` 继续绑定 CodeFusion 保存的确切 bundle Artifact，单项 `source_digest` 和 `package_files` 绑定各资产实际输入；
- 转换和导入都不执行 L1 Python/C 代码，不从名称猜科学字段，也不产生 AI/专家批准；`automated_checks` 仅记录已真实执行的 bundle 完整性、必要记录、文件、直接测试与依赖闭包检查。

目录和 ZIP 使用同一内容身份。ZIP 只接受安全相对路径、普通文件以及 stored/deflated 成员，拒绝路径穿越、符号链接、加密、重复/大小写冲突和超界内容；生成缓存不进入 bundle。若已有 ZIP 的中文路径编码存疑，应从保存的原目录重新转换。bundle JSON 限制在 14 MiB，为 CodeFusion 16 MiB 请求 wire 留出 envelope 空间；更大的项目按独立 L1 项目或有界批次拆分，而不是丢弃文件。

CodeFusion 可以让审核员上传原始包，并在通用 runner 中调用这个 SciRel 转换入口；平台只保存输入/输出 Artifact、调用身份和投递事实，不自行解析或猜测科学 domain 映射。转换后的 JSON Artifact 才作为 `scirel.import_l1` 输入。

## 中性 Agent 调用

调用输入为：

- `scirel-integration` skill snapshot，可带版本或内容摘要；
- 只读 L1 目录引用；
- 从冻结 SciRel baseline 派生的可写隔离候选 worktree/输出目录及其 Git base；
- 当前未发布候选池的只读比较视图或 artifact refs；
- 通用文件/终端/测试工具和权限；
- 自然语言任务目标与完成后的确定性验证命令。

模型只在候选 worktree/输出目录准备文档、代码和测试，不修改冻结 baseline。输出是通用运行证据：候选三件套、模型/skill/harness 身份、实际命令、
退出状态和需要保存的 artifact。工作目录和推理中间物不固定；上传边界由 SciRel 的
`scirel.standardization-submission.dev` 绑定逐项三件套与 exact 输入。CodeFusion 只保存和传递该 opaque
Artifact，不解析逐项关系判定，也不生成 SciRel domain 字段。

SciRel 可提供 `scripts/build_l1_inventory.py`、affected-test selector 和资产文档 validator 作为
可选工具。它们不是 Agent 调用协议，CodeFusion 无需调用或理解其输出。

模型完成后，通用 runner 可调用 `scripts/submit_standardization.py` 或等价 Python API，把 candidate、
submission 和候选池快照转换为 `scirel.workflow-state.dev(status=review_pending)`。这是确定性 SciRel
领域门禁，不是 CodeFusion 专用 operation，也不让 body runner 冒充模型执行过标准化。

### Plugin registration

开发期示例为
[`contracts/examples/scirel-plugin-registration.dev.json`](../../contracts/examples/scirel-plugin-registration.dev.json)。
它直接使用 CodeFusion 中性的 `PluginRegistration` wire shape：`release` 包含 `plugin_release_ref`、
ArtifactReference、skill entrypoint、connector descriptor 与 runtime dependency refs；外层只声明通用
capability、scope 和 UI extension。CodeFusion 把完整 release 当作一次运行固定的 opaque snapshot。旧运行
继续使用已固定 snapshot；更新或卸载只阻止新运行选择旧 release。

`scirel.review` 的可选 `reviewer_entry` 声明两个宿主入口：`scirel.import-l1` 映射
`scirel.import_l1`，`scirel.review-index` 映射 `scirel.review.list_items`。浏览器只提交 opaque
`intake_ref`、host context、Artifact 引用和 idempotency；CodeFusion 必须从已固定的 registration
在服务端解析 operation，不接受浏览器自报 operation。该元数据只用于通用工作台导航，不把 SciRel
领域状态或处理逻辑写入 CodeFusion。

bundle/catalog media type 分别为 `application/vnd.agent-skills.bundle+zip` 和
`application/vnd.scirel.catalog-snapshot+zip`。connector 使用 `mcp` 协议族，只暴露
`catalog.discover`、`asset.read`、`callable.resolve`、`callable.invoke` 四个 capability ref；认证、
授权、transport、timeout、sandbox 和审计由宿主包裹。运行时依赖使用 version-locked opaque
`runtime-dependency://...` 引用，SciRel 的 Python 模块布局不进入 CodeFusion 核心合同。

开发期容量提示为 skill bundle 32 MiB、压缩 catalog snapshot 512 MiB；它属于宿主安装 policy，不进入
registration。release 声明 `scientific-computation-asset-extraction`、`scirel-integration` 和
`scirel-solving` 三个主入口，但不能自行要求隐式加载；宿主选择后，specialist skills 再从入口 skill 渐进加载。
样例 artifact ref/digest 只是 wire-shape 占位，真实联调必须使用 ArtifactOwner 签发的身份。

## 确定性结果

`AutomatedCheckResult` 只表达确定性检查及证据引用，并绑定被检查的 candidate/source。
它不能修改 candidate，也不包含 `asset_updates`。发现缺直接测试、未解析依赖或科学差异时，
模型按照 skill 在冻结基线之外准备候选代码和测试，再对候选运行检查。

CodeFusion 的 run/job/attempt/timeout/权限和 transport 结果属于平台事实，不能转换为科学成功、
拒绝或批准。SciRel 的检查失败也不能伪装成平台故障。

### Approval resume 边界

CodeFusion 的 approval-resume provider-step、Tool Plan、runtime descriptor 和 MCP binding
snapshot 属于宿主运行态。SciRel 不持久化、不解释这些字段，也不把它们写入 candidate、workflow、
review 或 release artifact。候选上传后原 Agent run 可以结束；专家决定之后由新的固化 run 处理，
不要求 SciRel 恢复原 Agent 会话。宿主应将恢复后的执行结果投影为本合同已有的最小化
`PluginRunResult` 与结果 artifact；若把宿主快照字段直接加入 SciRel result wire，则属于宿主合同
越界，而不是 SciRel 的兼容要求。

## 专家审核 UI

模型完成候选准备后，可以上传包含许多 Operator/TaskGraph 的一个候选批次。上传者选择全部获准审核员或指定审核员可见；CodeFusion 的产品身份与项目授权负责在列表、详情、Artifact 和 action 入口执行访问控制，SciRel 插件负责每项内容、科学状态和可用动作。批次承载来源、冻结 SciRel 比较基线与上传/取回关系；单个资产/任务图是专家选择、领取和审核的 item，不能把整批当成一把写锁。SciRel 向 UI extension 提供：

- 候选文档、候选代码 patch/worktree 和候选测试 artifact；
- 逐项复用、重复、变体、组合、新增、冲突或未决判定；
- 资产文档、测试和实验依据；
- 未解决 gap 及允许的审核动作。

专家身份由宿主提供，审核动作语义由 SciRel 定义。SciRel 可以把批次、逐项已观测内容、逐项审核决定和批准子集的交接结果作为普通 plugin artifact 保存；CodeFusion 持有通用版本指针、reference/digest、写租约及平台审计，不把其中字段复制成平台科学真值，也不根据 run 状态推导可用审核动作。上传者可取回已完成项及全部审核证据，不必等整批结束；上传身份本身不构成科学批准。

上传前由模型完成候选整合和自动检查；上传时每项得到确切初始版本。此后 `review_pending` 项不由后台模型改写，是否已有专家查看都不改变这条规则。队列列表提供最小索引信息，完整详情按权限读取当前项的确切版本并记录所见；未领取者可以查看但不能修改。领取签发按 item ref 隔离、带代次的独占写租约，并绑定该轮的起始内容版本。领取和查看不是同一动作；有租约也不能覆盖旧版本，专家编辑形成有来源绑定的新提案/版本。

通用工作台以 item 的内容版本和操作事件两条关系承载历史：修改保存生成关联上一版本的内容快照，清空本轮修改将工作指针恢复到领取版本（不删除历史）；放回先保存当前版本再释放租约，该 item 仍待审且没有完成结论；显式提交才绑定最终内容版本、SciRel 审核动作和专家，并释放租约。内容不变时几个事件可指向同一快照，不能为了记录事件重复复制三件套；通用 diff UI 应比较插件声明可展示的文档、代码、测试，SciRel 提供差异的科学解释。旧租约代次或旧 expected revision 均不得写入；审核决定只针对提交的准确版本，不从放回、保存或平台 receipt 推导。

当前 reviewer body 接线使用以下最小合同：

- `scirel.review.list_items`：从一个 `review_pending` workflow batch 投影多个独立 Operator/TaskGraph item，返回中性 `codefusion.plugin-view-index.v1`。`item_ref` 由 candidate、draft、资产位置和稳定资产 ID 共同派生；同批 item 共用初始 batch Artifact digest 作为 revision，后续各自推进 current Artifact。每个 index item 都包含 SciRel 领域拥有的 `actions` descriptor；待审且无 gap 时依次提供批准、补证据、返工和拒绝，含 gap 时不提供批准，已完成项提供空数组。
- `scirel.review.open_item`：严格要求 list 返回的 `item_ref` 和 `revision == artifact_digest`，只读返回 `scirel.review-item-detail.dev`。详情携带该项完整资产、证据、依赖、gap 和当前决定，不调用 `start_review`，不改变 current pointer。
- `plugin.review.action`：这是 CodeFusion 固定的通用写操作。索引公开的 SciRel action refs 分别为 `plugin://scirel/review/approve`、`plugin://scirel/review/request-evidence`、`plugin://scirel/review/request-rework` 和 `plugin://scirel/review/reject`；descriptor payload 固定携带匹配的 `outcome` 与初始空 `notes`。SciRel 严格要求 action ref 与 outcome 匹配，并要求精确 item/revision、`extension_ref=scirel.review` 和 host 注入的 `reviewer.actor_ref`。缺少可信 reviewer context、旧 revision、错误 item 或带 gap 的批准都会被拒绝。
- action 成功返回唯一的 `codefusion.plugin-reviewer-successor-snapshot.v1`。其 predecessor 精确绑定输入 Artifact，opaque payload 保存下一版本完整 `scirel.review-item.dev` 科学内容和版本绑定的决定；result Artifact 自身由 CodeFusion CAS 为下一 current input。successor 同步携带下一状态的 `display_index`、`detail_action_ref` 和 `actions`；当前终态决定均输出空 `actions`。提交释放租约，但 CodeFusion 不解释其中 outcome。
- `scirel.review.list_completed`：对 current item Artifact 返回只读 `scirel.review-completed-results.dev`；所有已提交结论进入 `completed_items`，只有 approved item 进入 `approved_items`。两者都携带精确 current revision、资产、依赖、证据和决定，供上传者分批取回。

CodeFusion 的中性 index v1 每页最多 100 项，因此一个 review source Artifact 最多投影 100 个 item；更大的逻辑批次在上传准入时按 source Artifact 分片，批次来源关系仍由相同 candidate/draft 领域引用关联。SciRel 不返回超过宿主上限的无效 index，也不把分页游标塞入普通 generic run 的 `operation_payload`。

actor、tenant/project、correlation、idempotency、领取/续租、保存/清空/放回、CAS、diff 和事件历史仍属于通用宿主。SciRel 不复制 lease generation，也不从平台 receipt 推导审核结论。body action 的 reviewer 只能来自 CodeFusion 认证 host context，不能从客户端领域 payload 自报。当前 `WorkflowRecord.record_review()` 仍保留为 release fixture 的整 draft 状态机；真实 workbench 使用上述逐项 body，不以该旧方法作为并行审核事实。

只有逐项获专家批准、依赖闭包满足且 release 门禁通过的资产进入 catalog/runtime。candidate、临时报告、模型完成
状态和测试通过都不能单独产生发布。

候选提交工作台后，产生它的 Agent run 可以结束。上传者取得有审核版本和专家决定绑定的子集后，批准项触发新的固化 run，而不是恢复并长期占用原会话。UI extension 可以把“approved 且没有 release”显示为待固化，并展示最近一次固化 artifact 中的冲突；这些仍是 SciRel 领域投影。若当前基线与候选审核 base 在同一科学身份、合同、依赖闭包、TaskGraph 或 patch hunk 上冲突，固化 run 只提交关联的新候选，不覆盖旧批准，也不要求 CodeFusion 理解冲突的科学含义。

## 当前代码定位

`src/scirel_workflow/l1_bundle.py` 和 `src/scirel_plugin/adapter.py` 定义真实 L1 package 到 UTF-8 body wire 的 SciRel 接面；`scripts/build_l1_bundle.py` 是源码 checkout 下调用同一实现的入口。本地 HTTP listener 与 wire fixture 仍只是无认证的开发期 transport wrapper 和确定性合同测试，不属于 CodeFusion Agent kernel，也不能取代 skill 驱动的语义整合。

`FakeHost` 只证明 SciRel 领域代码不依赖 CodeFusion 数据库或网络。真实联合验收应使用同一
中性 invocation 分别运行 Claude Code 与 CodeFusion，再比较候选文档、候选 diff、证据和验证结果。

## 版本

当前开发期 artifact/schema 使用 `.dev`。首条真实闭环稳定后统一冻结为 `v1`；冻结前不为旧
开发协议保留兼容分支。
