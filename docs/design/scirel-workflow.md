# SciRel Workflow 设计

## 设计原则

workflow 是 host-independent 的领域协调器。它记录从 L1 比较得到的候选、确定性检查、专家 action，以及最终批准绑定的 catalog、wheel 和 release version。存储和传输由调用方或 plugin adapter 负责。

workflow 不执行科学标准化，也不规定模型必须使用的探针、脚本或中间文件。加载
`scirel-integration` skill 的模型负责理解 L1、比较当前 SciRel 与未发布候选池、修改隔离工作树和形成证据；
workflow 只记录其结果，并执行可确定验证的状态、摘要、文档结构和发布门禁。

模型交接使用 `scirel.standardization-submission.dev`。每个 review unit 绑定一个目标 asset document、
一个面向专家的候选文档、候选代码或明确的无代码理由、候选测试与实际结果、来源 L1 asset IDs、
处置和依赖。外层绑定 candidate/source digest、Git base、候选池快照及 producer 身份。
`submit_standardization()` 校验这些事实及全部 L1 asset 的覆盖；有保留增量时生成 `review_pending` draft，无增量且 input_dispositions 完整时生成 `no_changes`；
submission 不能声明或改写 automated checks。

下述 `WorkflowRecord` 与 transition API 仍描述单 draft release fixture。实际 reviewer body 已在插件边界把 batch 投影为逐个 Operator/TaskGraph item，支持只读打开、逐项结论、完整 successor 和批准子集取回；它复用 CodeFusion 中性 workbench 的 lease/CAS，不把平台协调字段写回 `WorkflowRecord`。

`WorkflowRecord` 保存当前 draft/review，以及本次 run 的 draft/review history。这里的 draft 是最终待审的冻结三件套，可引用已在隔离 SciRel 开发版实现并验证的代码；它不是可信发行证明。当前开发 fixture 只允许在 `draft` 状态原位替换并复用 `draft_id`；`submit_for_review` 代表上传边界，之后初始版本固定。fixture 仍在 `start_review` 时把单个 draft 推进到 `review_in_progress`，这只是内部人工审核状态，不是目标工作台的“首次打开才冻结”合同。目标流程中查看只记录所见版本，返工另记版本和决定，任何操作都不覆盖 L1 source、冻结基线或已存版本。

模型的比较视图由“冻结 SciRel 基线 + 全部当前未发布候选 + 本次 L1”组成。候选池用于上传前的语义去重、合并和冲突预判，可在隔离开发包 import、构建内部 catalog/wheel，但不得冒充可信基线。上传后的 item 没有后台模型更新；领取绑定的起始版本在本轮必须保持可恢复。新的 AI 准备运行只能产生关联候选，由上传者明确提交，不能覆盖已上传版本。

上传前草稿撤回由候选 artifact 层取消引用，不增加 `WorkflowStatus`。已上传项的撤回必须是上传者的显式队列操作，保留初始内容引用和事件，而非基于“尚未观测”静默删除。

候选生成进程在提交 draft 后结束。工作台随后独立承载人工审核；`approved` 只把候选送入批准后固化队列，不要求原模型会话继续存活。

工作流还可以通过 `SciRelWorkflow.to_dict()` 生成
`scirel.workflow-state.dev` 快照，并用 `SciRelWorkflow.from_dict()` 恢复。
这是 SciRel 自己的最小持久化边界：candidate、自动检查结果、draft、审核记录和
release 都在快照中，宿主只负责把快照作为 artifact 保存。快照不包含 tenant、job、
session、credential 或平台审计字段，因此恢复不依赖 CodeFusion 数据库。

## 状态决策

```text
没有检查结果       -> candidate
检查进行中         -> automated_checking
有失败或 gap       -> automated_rejected / retry / rework_requested / needs_evidence
检查通过且无显式阻断动作 -> automated_ready
检查通过但 next_action 要求补证据或返工 -> needs_evidence / rework_requested
完整无变化处置     -> no_changes (无 draft/review/release)
有 draft            -> draft / review_pending / review_in_progress
审核 action         -> needs_evidence / rework_requested / rejected / approved
approved + 构建完成 -> released
```

状态由领域对象和 workflow transition 推导，不由 UI 文案或 CodeFusion job 状态直接替代。

### 批次与逐项审核目标

批次固定 L1 来源、SciRel 比较基线、候选池引用和上传者交接关系；每个 Operator/TaskGraph 在上传时得到可独立检索的 item ref、初始三件套版本、依赖 refs 和审核状态。专家可以浏览整批，领取不同 item 并行处理。未领取的授权人员只有只读权限；打开完整详情记录所见版本，不改写内容或锁定同批其它项。同项的有效写租约只有一个。CodeFusion 通用工作台负责领取/续租/放回的 holder、generation、expiry，内容版本指针、通用事件和 diff UI；SciRel 提供候选内容及科学审核动作，并对 item revision、依赖和科学前置条件再验证。放回队列不删除已发生的查看或审核记录，也不表示审核完成。

已观测的候选版本不覆写。通用领取事件绑定当前版本作为本轮基点；持租约的专家保存修改时产生关联前一版本的内容提案，清空本轮修改则把工作指针恢复到领取基点，历史仍可看。放回保存当前内容指针、记录事件并释放租约，内容不变时复用旧快照；该项继续待审，可由另一专家领取。提交则保存最终版本、记录 SciRel 审核动作和决定、释放租约，才是该项审核完成。领取、放回和提交可以指向同一内容版本，但事件各自保留；通用工作台展示各版本的文档、代码、测试差异，SciRel 负责解释科学变更。多名专家可以只读同一 item，但本轮主要并行性来自不同 item 的领取，不要求每个算子都由多人审批。若逐项意见不一致，只有有权限的科学裁决者能形成最终决定，平台租约或投票数不能替代该决定。上传者可取回已完成的批准子集及各项证据；TaskGraph 固化仍要求其依赖闭包已批准或已在维护基线中。

因为上传时已有固定初始版本，`scirel.review.open_item` 只读返回 exact item detail，不推进 current snapshot；不需要特殊的首读 pin 或无租约 mutation。领取和内容编辑仍用通用 lease、expected revision 和 CAS。fixture 的 `start_review` 只供旧 transition/release 测试，不参与工作台 open。

reviewer body 的 item ref 由 candidate、draft、资产位置和 asset ID 生成，一个 batch 可投影多个稳定 item。`plugin.review.action` 要求精确 current revision 和 host reviewer context，返回带 exact predecessor 的 CodeFusion v1 successor；successor opaque payload 保留完整 SciRel item，不能只返回展示投影。`record_review()` 仍会关闭整 draft，但仅属于旧 release fixture，不参与工作台逐项审核。
Candidate 和 draft 在每次构造及 snapshot 恢复时重新推导 inventory/scientific contract gaps，
不信任 L1 或序列化 payload 自报的空 gaps。恢复出的 approved/released draft 如果重新检查后
存在 gap，整个 snapshot 视为非法。
恢复还会校验 result→candidate/source、draft→candidate、review→draft 以及
release→candidate/draft/digest/approved-assets 的关系完整性，并要求当前 draft/review 存在于
对应历史。单个记录各自满足 schema 但跨记录绑定不一致时，整个 snapshot 拒绝恢复。
当前 draft 和 review 必须分别等于各自历史的末项，返工历史被重排时拒绝恢复。
含 release 的 snapshot 还会重新要求 candidate 已通过自动门禁、当前 draft 为 approved、
当前 review 明确为 approved；存在 release 字段本身不能替代这些发布前置条件。
更一般地，只要 snapshot 已包含 draft 历史，candidate 就必须仍为 automated-ready，
不能通过改写 candidate 检查结果恢复出本来无法创建的 draft 或 review 状态。

## 当前开发 fixture 的 Transition API

下列最小 API 只描述当前单 draft fixture，用于验证候选、审核决定和 release 的基本绑定；它不是上传后批量逐项审核的目标接口：

- `CandidatePackage.from_l1(payload, source_artifact_ref, source_digest, run_id)`；
- `SciRelWorkflow(candidate)`；
- `create_draft(...)`；
- `update_open_draft(...)`；
- `submit_for_review()`；
- `start_review()`；
- `record_review(ReviewDecision(...))`；
- `release(release_id, catalog_ref, catalog_digest, wheel_ref, wheel_digest, release_version)`。

正式模型交接不调用上述低层 `create_draft()`/`submit_for_review()` 组合，而调用
`submit_standardization(StandardizationSubmission, expected_...)`。源码 checkout 下的确定性入口为：

```powershell
python scripts/submit_standardization.py <candidate.json> <submission.json> <candidate-pool.json> <new-workflow.json>
```

它从当前 checkout 读取 exact Git HEAD 和 `scirel-integration` skill 文件摘要，重新计算候选池的
canonical JSON 摘要，并拒绝覆盖已有输出。工作区布局、探针和语义比较仍由模型决定；该命令只处理最终交接。

插件侧消费已完成的 generic run 使用
`SciRelPlugin.consume_automated_result_into_workflow(workflow, run_result)`：它先校验
平台 receipt、唯一 result artifact 和正文 digest，再把领域结果应用到 workflow，并保存
一个 `scirel.workflow-state.dev` 快照。平台失败或结果 artifact 非法时，workflow 不会
被修改。相同 `result_id` 与 `result_digest` 的重放是领域幂等 no-op，即使 workflow 已经
创建 draft 也返回当前 candidate；相同 `result_id` 携带不同正文则拒绝，不能覆盖第一次结果。

在这个 fixture 中，`create_draft` 只允许自动检查通过，或允许在 `needs_evidence`/`rework_requested` 后重新创建；`update_open_draft` 只可在上传前的 `draft` 状态替换当前内容，复用 `draft_id` 并替换 history 末项。`submit_for_review` 后禁止模型更新。`start_review` 会把整个 draft 推进为 `review_in_progress`，这是旧单项测试夹具的人工审核状态机，不得解释为目标工作台的“首次打开即冻结”要求。目标工作台遵循前述规则：上传固定逐项初始版本，只读打开不改内容，领取后由人工修改产生新版本。候选文档、代码和测试可以作为 task-local artifact/patch 被 draft 证据引用，不要求统一文件 schema。fixture 的 `release` 只允许最新 draft 获得 `approved`，并要求调用方先完成批准后整合，再提供 candidate/draft digest、asset ID、catalog ref/digest 和 wheel ref/digest。
release 还逐项要求资产文档的 `version.implementation_version` 精确等于请求的
`release_version`；snapshot 恢复时重复执行同一检查，不能通过改写 manifest 版本绕过。

`create_draft` 不要求上游标准化一次成功。它对每个资产执行无依赖的
`scirel.asset-document.v1` 顶层字段检查，并递归拒绝 tenant、job、session、credential
及旧 admission/case/decision 等私有字段；缺失、未知、错误 schema 或私有字段被记录为
`scientific_contract_*` gap。这样的 draft 可以进入专家工作台以请求证据或返工，但不能
执行 `approve`，也不能通过 release 的 unresolved-gap 门禁；UI projection 对此类 draft
只暴露 `needs_evidence`、`rework_requested` 和 `reject`。端口、单位、坐标、适用域、版本和 TaskGraph 结构的
完整嵌套验证仍由 `scripts/validate_asset_documents.py` 在发行构建时执行；顶层检查不能被解释
为完整科学正确性证明。

自动检查结果不能修改 candidate。合同、实现、直接测试或依赖问题由模型在隔离候选工作树
中处理，随后针对真实变更重新运行门禁。这样既允许模型按具体科学问题选择验证方法，也避免
把一次任务的修复形态固化为通用 patch schema。

## 无变化交接与兼容性

input_dispositions 是可选字段；每项包含 source_asset_ids、disposition（reuse/exact_duplicate/covered_by）、
target_asset_id、target_ref、target_digest 和 evidence。它与 review_units 一起完整且无重复地记账。
目标引用绑定实际比较版本；领域对象不读取外部 artifact，也不证明科学等价，D2 必须提供实际比较依据。
纯无变化 submit_standardization 返回 None，workflow.status 为 NO_CHANGES；官方 CLI 仍序列化 workflow，
插件无待审 item。快照保存 no_change_submission，恢复时重新验证绑定、检查结果、输入覆盖和 gaps。
该终态不能新建 draft 或被新检查修改；完全相同的既有检查回放保持幂等。
旧 payload/快照省略新增空字段，既有摘要和读取方式不变；无需数据库迁移。
这条路径不为目标资产创造批准或 release，release 的 approved 门禁不变。

## Artifact 适配

`SciRelPlugin` 不把 workflow 状态写入宿主数据库，而是通过宿主已有 artifact store
保存领域快照。它把领域对象序列化为以下 artifact：

```text
scirel.l1-bundle.dev
scirel.candidate-package.dev
scirel.standardization-submission.dev
scirel.standardized-draft.dev
scirel.review-decision.dev
scirel.release-manifest.dev
scirel.workflow-state.dev
scirel.review-item.dev
scirel.review-item-decision.dev
scirel.review-item-detail.dev
scirel.review-completed-results.dev
codefusion.plugin-reviewer-successor-snapshot.v1
```

artifact 的 digest 和 reference 由 host 生成；领域 payload 由 SciRel contract 定义。最后一项是 CodeFusion 已冻结的中性宿主 envelope，SciRel 领域内容只位于其 opaque `payload`。正式发布前将 SciRel 自有的开发期 media/schema 名称统一冻结为 `v1`。

## 构建与运行绑定

D2 在开发分支已整合代码与测试并可构建开发 wheel。专家最终批准后，独立步骤确认实际版本符合已批准快照；任何科学实质偏离形成 successor 重新审核。release build 再读取实际标准化资产文档和受影响测试结果，生成 catalog、wheel 和 manifest。manifest 只描述这一次 release 绑定，不成为第二套科学真值。CodeFusion runtime 读取 manifest 后验证 candidate/draft、catalog 和 wheel 的绑定，再暴露已发布 callable。

draft、review action 和自动检查结果可以被工作台查询，但不得被运行时 callable resolver 当作 release。

当前开发期发布索引由 `scripts/release_index.py` 产生 `scirel.release-index.dev` 的 append-only
候选条目。候选绑定同一 candidate/draft 下每项待审 artifact 的 SHA-256、初始资产文档摘要、依赖
和 Git 提交；条目 digest 覆盖完整内容，不能据此推断审核通过。`scripts/finalize_release.py` 的正式
命令入口要求工作台导出的 completed/approved 投影及所有 exact review artifact；复查批准 successor
与提交前 item、批准文档和逐文件代码/测试材料，再核对发行 Git diff、实际文件、wheel、catalog 和
许可状态。批准项测试由 finalizer 在发行源码上重跑。通过后在输出目录写入新的索引副本，其中
`released` 条目保留候选 predecessor 和 manifest digest；已有索引不回写。单 draft
`finalize_single_draft_fixture` 仍服务旧生命周期测试，不参与发行命令。

artifact 摘要保证导出内容一致，不认证审核 actor。工作台必须提供经授权流程形成的投影与 artifact，
发行负责人仍须确认发行授权。开发期的索引和 manifest 字段是 `.dev`；正式发布前统一收敛为 `v1`。

### 固化队列与乐观并发

候选文档或通用 harness 运行证据记录比较时的 SciRel Git base。第一版固化器串行消费已批准候选，每次都从当前基线开始；这里的串行窗口只覆盖基线检查、应用和测试，不阻塞候选生成或人工审核。

固化器先计算批准候选涉及的科学身份、源码/文档 patch、直接依赖和 TaskGraph 反向依赖，再与审核 base 到当前 HEAD 的变化求交：

- 没有交集，或只有无关文件变化且批准 patch 可逐字保持时，应用原候选并运行 affected tests；
- 同一 patch hunk、稳定 asset ID、公共 API/科学合同、依赖边或受影响 TaskGraph 发生变化时，判为冲突，不自动选取较新或较早候选；
- 冲突产生一个固化失败 artifact，并以当前 HEAD 为 base 创建关联的新候选。旧 workflow 和旧 review 不改写；
- 新候选可以得出“已被前一个候选吸收/现在应复用”的结论，只保留可核对的 input_dispositions；无公共合同改变时无需新文档或审核。

因此不需要在 `WorkflowStatus` 中复制队列系统的每个瞬时状态：`approved` 表示等待固化，存在 release 表示固化和发行均完成。工作台可由 approved workflow、release 缺失和最近一次固化结果投影“待固化/冲突”。若后续真实负载证明串行固化成为瓶颈，再只对影响闭包互斥的候选增加并行调度。

隔离开发包可执行和验证，最终待审与可信版采用独立版本绑定。开发进展不改写上一可信版本。正式文档在 D2 去重/代码稳定后为保留增量生成；源注释和派生代码中的内部实现备注不复制成正式审核文档。

## 验证策略

工作流单元测试验证所有合法和非法 transition；plugin contract tests 验证 host envelope 字段；垂直 fixture 验证从 L1 到 release 的串联。工作流源码、plugin 源码及其 `.dev` 合同由 `affected` 选择器映射到上述边界测试；只有无法归属的共享源码或合同变化才 fail closed 到全套测试。
