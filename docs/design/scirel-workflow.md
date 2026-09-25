# SciRel Workflow 设计

## 设计原则

workflow 是 host-independent 的领域协调器。当前实现记录从 L1 比较得到的逐项候选、确定性检查和专家 action。存储和传输由调用方或 plugin adapter 负责。目标流程另区分隔离开发版、冻结待审版、专家认可的可信版及公开 release；现有 workflow 尚未实现版本晋级，旧逐项审核到发行的入口已阻断。

workflow 不执行科学标准化，也不规定模型必须使用的探针、脚本或中间文件。加载
`scirel-integration` skill 的模型负责理解 L1、比较当前 SciRel 与未发布候选池、修改隔离工作树和形成证据；
workflow 只记录其结果，并执行可确定验证的状态、摘要、文档结构和发布门禁。

`WorkflowRecord` 保存当前 draft/review，以及本次 run 的 draft/review history。这里的 draft 是逐项审核提案，可以对应隔离开发分支中已经实现的代码，但不等于整版认可。`draft` 和尚未被专家打开的 `review_pending` 可以原位替换并复用 `draft_id`；工作台在首次返回完整详情前调用 `start_review`，进入 `review_in_progress` 后内容冻结。返工只创建新的 draft 记录并保留前一次 action。任何操作都不覆盖 L1 source、审核快照或已经被专家观测的 artifact。

模型的比较视图由“确切开发 Git 基线 + 全部当前未发布候选 + 本次 L1”组成，另以最后可信版本作为审核差异基线。候选池用于语义去重、合并和冲突预判；提案本身不是第二套权威科学真值。已整合内容可进入隔离开发 import、内部 wheel 和标明非可信的 pilot catalog，但不得投影为面向用户的可信 release。

未观测候选的撤回由候选 artifact/队列层取消引用，不增加 `WorkflowStatus`。这样保留必要的通用运行证据，同时不把专家从未看到的版本升级为科学审核历史。

候选生成进程在提交 draft 后结束。工作台随后独立承载人工审核；当前 `approved` 是逐项结论，不能把含其他未认可科学增量的开发版本整体标可信，不要求原模型会话继续存活。

待审版从确切开发提交冻结 Git tree、exact documents 集合、相对上一可信版的累积科学差异、受影响反向依赖及证据；内部 wheel/catalog 若已构建也绑定其摘要。初次审核没有可信基线时明确首次审核集合。未变证据只在实现、合同、依赖和适用环境均未变化时复用。部分认可应在隔离开发版剔除或返工未认可内容，重验受影响闭包并冻结 successor；不可在原快照上只改批准标签。`scripts/freeze_review_version.py` 已实现首次开发快照的确定性绑定，输出 `pending_unapproved`，不做科学差异推断；专家认可、可信晋级和发行绑定仍待实现，不对应当前 `WorkflowStatus` 的新增状态。

`scripts/review_scope.py` 输出参与比较的原始 manifest SHA-256，供异步审核动作指向专家实际看到的确切快照；排版改变也会改变该身份，但不会因此扩大科学差异。摘要与 `ReviewDecision.reviewer` 字符串都不能证明审核者是获授权专家。未来版本级认可必须另取得可验证的人工身份/授权事件或等效签名，并绑定该快照和审核范围；在此之前保持 `pending_unapproved`，旧发行入口继续拒绝。

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
版本级专家认可 + 独立发行门禁 -> released（尚未实现）
```

状态由领域对象和 workflow transition 推导，不由 UI 文案或 CodeFusion job 状态直接替代。
Candidate 和 draft 在每次构造及 snapshot 恢复时重新推导 inventory/scientific contract gaps，
不信任 L1 或序列化 payload 自报的空 gaps。恢复出的 approved draft 如果重新检查后
存在 gap，整个 snapshot 视为非法。
恢复还会校验 result→candidate/source、draft→candidate、review→draft 的关系完整性，并要求当前 draft/review 存在于
对应历史。单个记录各自满足 schema 但跨记录绑定不一致时，整个 snapshot 拒绝恢复。
当前 draft 和 review 必须分别等于各自历史的末项，返工历史被重排时拒绝恢复。
含旧 release 的 snapshot 会被拒绝恢复；逐项 approved 无法证明整个版本已获专家认可。
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
- `release(...)`：旧调用签名保留用于明确拒绝，不生成 manifest；新版本级发行 API 待设计。

插件侧消费已完成的 generic run 使用
`SciRelPlugin.consume_automated_result_into_workflow(workflow, run_result)`：它先校验
平台 receipt、唯一 result artifact 和正文 digest，再把领域结果应用到 workflow，并保存
一个 `scirel.workflow-state.dev` 快照。平台失败或结果 artifact 非法时，workflow 不会
被修改。相同 `result_id` 与 `result_digest` 的重放是领域幂等 no-op，即使 workflow 已经
创建 draft 也返回当前 candidate；相同 `result_id` 携带不同正文则拒绝，不能覆盖第一次结果。

`create_draft` 只允许自动检查通过，或允许在 `needs_evidence`/`rework_requested` 后重新创建。`update_open_draft` 在 `draft` 或未被观测的 `review_pending` 状态替换当前内容，复用 `draft_id` 并替换 history 末项；它不保留专家从未看到的中间编辑版本。`start_review` 是观测边界：工作台必须先完成该 transition，再把同一个 `review_in_progress` 快照展示给专家。候选文档、代码和测试可以作为 task-local artifact/patch 被 draft 证据引用，不要求统一文件 schema。逐项 `approved` 后只能保存审核结论；`release()` 明确拒绝，直到整版专家认可及发行绑定实现。

`create_draft` 不要求上游标准化一次成功。它对每个资产执行无依赖的
`scirel.asset-document.v1` 顶层字段检查，并递归拒绝 tenant、job、session、credential
及旧 admission/case/decision 等私有字段；缺失、未知、错误 schema 或私有字段被记录为
`scientific_contract_*` gap。这样的 draft 可以进入专家工作台以请求证据或返工，但不能
执行 `approve`；UI projection 对此类 draft
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
scirel.workflow-state.dev
```

artifact 的 digest 和 reference 由 host 生成；领域 payload 由 SciRel contract 定义。旧 `scirel.release-manifest.dev` schema 仍可作为历史证据读取，但插件不再创建该 artifact，也不发出旧完成事件。正式发布前将有效的开发期 media/schema 名称统一冻结为 `v1`。

## 构建与运行绑定

Agent 可先在隔离开发分支写入代码、文档和测试，构建内部 wheel 做 source-free 验证；开发 pilot catalog 只供内部核对，不作为已发布目录。待审版的专家认可绑定确切版本及其科学增量；release build 再从获认可的版本读取实际标准化资产文档和验证结果，生成面向用户的 catalog、wheel 和 manifest。manifest 只描述这一次 release 绑定，不成为第二套科学真值。CodeFusion runtime 仅暴露已发布 callable。旧 `release` 实现按逐项 approved draft 绑定 candidate/draft、catalog 和 wheel，不能覆盖整版增量；现在 workflow、插件、直接 finalizer 和 `check.ps1 -Mode release` 均阻断该路径，版本绑定需后续实现。

draft、review action 和自动检查结果可以被工作台查询，但不得被运行时 callable resolver 当作 release。

### 开发整合冲突与版本确认

候选文档或通用 harness 运行证据记录比较时的 SciRel Git base。开发整合可在专家审核前发生；多候选并行时，对同一科学身份及依赖闭包保持协调，不覆盖已进入开发基线的其他贡献。旧批准后固化器是现有设计中的待迁移部分，不再是写入隔离开发包的必要步骤。

每次开发整合先计算候选涉及的科学身份、源码/文档 patch、直接依赖和 TaskGraph 反向依赖，再与比较 base 到当前 HEAD 的变化求交：

- 没有交集，或只有无关文件变化且 patch 可逐字保持时，整合候选并运行 affected tests；
- 同一 patch hunk、稳定 asset ID、公共 API/科学合同、依赖边或受影响 TaskGraph 发生变化时，判为冲突，不自动选取较新或较早候选；
- 冲突保留比较证据，并以当前 HEAD 为 base 重新判断关系和行动；旧 workflow 和旧 review 不改写；
- 新判断可以得出“已被前一个候选吸收/现在应复用”的结论，但仍需记录确切来源、条件及证据，不自动扩大旧审核结论。

不需要在 `WorkflowStatus` 中复制开发队列的瞬时状态。当前 API 的 `approved` 保留逐项含义；UI 不再展示 `release` 动作。具体版本记录、发布接口及工作台投影待实现时定义，不在此假定已交付。

“先写入开发包、后冻结审核”允许在隔离开发分支执行和构建内部 wheel；周期审查本身不能代替专家对确切冻结版本的认可。未认可内容不得进入可信发行基线、面向用户的 catalog/runtime 或公开 wheel。

## 验证策略

工作流单元测试验证合法/非法 transition；plugin contract tests 验证 host envelope 字段；垂直 fixture 验证从 L1 到逐项审核，以及旧 release 入口的拒绝。工作流源码、plugin 源码及其 `.dev` 合同由 `affected` 选择器映射到上述边界测试；只有无法归属的共享源码或合同变化才 fail closed 到全套测试。
