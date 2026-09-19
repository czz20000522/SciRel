# SciRel Workflow 设计

## 设计原则

workflow 是 host-independent 的领域协调器。它记录从 L1 比较得到的候选、确定性检查、专家 action，以及批准后整合产生的 catalog、wheel 和 release version。存储和传输由调用方或 plugin adapter 负责。

workflow 不执行科学标准化，也不规定模型必须使用的探针、脚本或中间文件。加载
`scirel-integration` skill 的模型负责理解 L1、比较当前 SciRel 与未发布候选池、修改隔离工作树和形成证据；
workflow 只记录其结果，并执行可确定验证的状态、摘要、文档结构和发布门禁。

`WorkflowRecord` 保存当前 draft/review，以及本次 run 的 draft/review history。这里的 draft 是冻结基线之外的候选三件套，不是已经写入 SciRel 的资产。`draft` 和尚未被专家打开的 `review_pending` 可以原位替换并复用 `draft_id`；工作台在首次返回完整详情前调用 `start_review`，进入 `review_in_progress` 后内容冻结。返工只创建新的 draft 记录并保留前一次 action。任何操作都不覆盖 L1 source、冻结基线或已经被专家观测的 artifact。

模型的比较视图由“冻结 SciRel 基线 + 全部当前未发布候选 + 本次 L1”组成。候选池用于语义去重、合并和冲突预判，不进入公共 import、catalog 或 wheel，因此不成为第二套权威基线。

未观测候选的撤回由候选 artifact/队列层取消引用，不增加 `WorkflowStatus`。这样保留必要的通用运行证据，同时不把专家从未看到的版本升级为科学审核历史。

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
有 draft            -> draft / review_pending / review_in_progress
审核 action         -> needs_evidence / rework_requested / rejected / approved
approved + 构建完成 -> released
```

状态由领域对象和 workflow transition 推导，不由 UI 文案或 CodeFusion job 状态直接替代。
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

## Transition API

最小 API 为：

- `CandidatePackage.from_l1(payload, source_artifact_ref, source_digest, run_id)`；
- `SciRelWorkflow(candidate)`；
- `create_draft(...)`；
- `update_open_draft(...)`；
- `submit_for_review()`；
- `start_review()`；
- `record_review(ReviewDecision(...))`；
- `release(release_id, catalog_ref, catalog_digest, wheel_ref, wheel_digest, release_version)`。

插件侧消费已完成的 generic run 使用
`SciRelPlugin.consume_automated_result_into_workflow(workflow, run_result)`：它先校验
平台 receipt、唯一 result artifact 和正文 digest，再把领域结果应用到 workflow，并保存
一个 `scirel.workflow-state.dev` 快照。平台失败或结果 artifact 非法时，workflow 不会
被修改。相同 `result_id` 与 `result_digest` 的重放是领域幂等 no-op，即使 workflow 已经
创建 draft 也返回当前 candidate；相同 `result_id` 携带不同正文则拒绝，不能覆盖第一次结果。

`create_draft` 只允许自动检查通过，或允许在 `needs_evidence`/`rework_requested` 后重新创建。`update_open_draft` 在 `draft` 或未被观测的 `review_pending` 状态替换当前内容，复用 `draft_id` 并替换 history 末项；它不保留专家从未看到的中间编辑版本。`start_review` 是观测边界：工作台必须先完成该 transition，再把同一个 `review_in_progress` 快照展示给专家。候选文档、代码和测试可以作为 task-local artifact/patch 被 draft 证据引用，不要求统一文件 schema。`release` 只允许最新 draft 获得 `approved`，并要求调用方先完成批准后整合，再提供 candidate/draft digest、asset ID、catalog ref/digest 和 wheel ref/digest。
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

## Artifact 适配

`SciRelPlugin` 不把 workflow 状态写入宿主数据库，而是通过宿主已有 artifact store
保存领域快照。它把领域对象序列化为以下 artifact：

```text
scirel.candidate-package.dev
scirel.standardized-draft.dev
scirel.review-decision.dev
scirel.release-manifest.dev
scirel.workflow-state.dev
```

artifact 的 digest 和 reference 由 host 生成；领域 payload 由 SciRel contract 定义。正式发布前将这些开发期 media/schema 名称统一冻结为 `v1`。

## 构建与运行绑定

专家批准后，独立实施步骤按候选文档应用候选代码和测试；任何实质偏离都返回审核。release build 再读取实际标准化资产文档和受影响测试结果，生成 catalog、wheel 和 manifest。manifest 只描述这一次 release 绑定，不成为第二套科学真值。CodeFusion runtime 读取 manifest 后验证 candidate/draft、catalog 和 wheel 的绑定，再暴露已发布 callable。

draft、review action 和自动检查结果可以被工作台查询，但不得被运行时 callable resolver 当作 release。

### 固化队列与乐观并发

候选文档或通用 harness 运行证据记录比较时的 SciRel Git base。第一版固化器串行消费已批准候选，每次都从当前基线开始；这里的串行窗口只覆盖基线检查、应用和测试，不阻塞候选生成或人工审核。

固化器先计算批准候选涉及的科学身份、源码/文档 patch、直接依赖和 TaskGraph 反向依赖，再与审核 base 到当前 HEAD 的变化求交：

- 没有交集，或只有无关文件变化且批准 patch 可逐字保持时，应用原候选并运行 affected tests；
- 同一 patch hunk、稳定 asset ID、公共 API/科学合同、依赖边或受影响 TaskGraph 发生变化时，判为冲突，不自动选取较新或较早候选；
- 冲突产生一个固化失败 artifact，并以当前 HEAD 为 base 创建关联的新候选。旧 workflow 和旧 review 不改写；
- 新候选可以得出“已被前一个候选吸收/现在应复用”的结论，但仍需新的候选文档和审核。

因此不需要在 `WorkflowStatus` 中复制队列系统的每个瞬时状态：`approved` 表示等待固化，存在 release 表示固化和发行均完成。工作台可由 approved workflow、release 缺失和最近一次固化结果投影“待固化/冲突”。若后续真实负载证明串行固化成为瓶颈，再只对影响闭包互斥的候选增加并行调度。

“先写入包、后周期审查”只允许作为隔离候选存储：候选路径不得被 `scirel` 导入，不得进入 catalog 或 wheel。只要代码能够通过维护中的公共包执行，它就已经改变冻结基线，必须先有专家批准。

## 验证策略

工作流单元测试验证所有合法和非法 transition；plugin contract tests 验证 host envelope 字段；垂直 fixture 验证从 L1 到 release 的串联。工作流源码、plugin 源码及其 `.dev` 合同由 `affected` 选择器映射到上述边界测试；只有无法归属的共享源码或合同变化才 fail closed 到全套测试。
