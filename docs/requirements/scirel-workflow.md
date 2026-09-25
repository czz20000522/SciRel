# SciRel L1 到 Release 需求

## 目标

SciRel 负责从保存的 L1 产物开始，完成语义理解、与当前开发基线及未发布候选池比较、隔离开发整合、冻结待审版本、专家审核、可信版本确认和 release。CodeFusion 是中性的 Agent 宿主，不拥有 SciRel 的科学状态和资产语义。

语义理解和标准化由加载 `scirel-integration` skill 的模型完成；代码不尝试用固定状态机、脚本或 JSON patch 代替这项工作。Agent 可在隔离开发分支直接整合 `src/scirel`、exact documents、TaskGraph 和测试，构建供内部验证的 wheel。开发包可执行不等于科学可信或公开发布；专家审核的是冻结 SciRel 版本相对上一可信版的科学增量及反向依赖，而不是每次写入开发代码前逐项批准。

## 生命周期目标与现状

目标边界是“隔离开发整合 -> 冻结待审版本 -> 相对上一可信版的增量科学审核 -> 专家认可的可信版本 -> 独立发行门禁”。无可信版本时应明确首次审核集合；跳过若干开发版时仍须展示相对上一可信版的累积差异。未变且未受影响的资产可复用经核实仍有效的证据；专家只认可部分增量时，必须剔除或返工未认可内容，重新验证并冻结 successor，不能把原快照整体标可信。

下列逐候选状态是**当前 workflow API**，仍可承载候选比较、专家分工和审核事件；它尚未实现上述版本晋级，不得把一次 `approved` action 当成整个开发版本的可信认可：

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

`draft` 和尚未被专家打开的 `review_pending` 可以复用同一 `draft_id` 替换内容，不产生需要专家逐份处理的草稿历史。工作台在返回完整候选详情前执行 `start_review`；进入 `review_in_progress` 才表示发生专家观测并冻结三件套。`needs_evidence` 和 `rework_requested` 通过新的 draft 返工并保留已发生的审核记录。每个 workflow 保留一个 `run_id`，draft 和 review action 按顺序记录；开发期不引入额外的版本服务。

候选生成与专家审核是两个异步流程。模型提交 draft 后即可结束运行，不等待耗时不可控的人工审核。当前 API 中的 `approved` 只表示该 draft 的逐项审核结果，不自动批准其他开发增量或发行。未获认可的开发资产不得进入面向用户的可信 catalog/runtime；但隔离开发分支中的代码、测试、内部 wheel 和开发 pilot catalog 可用于验证，并须标明非可信。当前没有可用的 `released` 转换，旧逐项批准到发行的入口必须拒绝。

## 领域对象

- **L1 payload**：来源项目拆解阶段保存的输入。SciRel 只依赖 payload 和来源 artifact reference，不依赖源项目 checkout、CodeFusion 数据库或网络。
- **L1 inventory**：`scripts/build_l1_inventory.py` 提供的可选结构探针。它可以帮助定位相对路径、直接测试和显式依赖缺口，但不是模型整合 L1 的必经输入或标准化协议。
- **CandidatePackage**：绑定 `run_id`、来源 artifact、source digest、单一 `project_id`、候选资产和自动检查结果。多项目 inventory 必须先拆成 `to_project_l1_payloads()` 的独立 payload，不能在一个 candidate 中混合推进。
- **Candidate comparison view**：当前开发基线、全部当前未发布候选和本次 L1 输入的联合检索视图。它用于提前发现重复、可合并项和冲突；未发布候选的提案不自动成为已验证或可信资产，即使其中一部分已在隔离开发包中实现。
- **StandardizedDraft**：逐项审核工作台使用的候选，包含以文字为主的候选文档、候选代码/patch、候选测试、依赖关系、科学证据、capability gaps，以及本次比较使用的确切 SciRel Git base。未发生专家观测前可替换；它与冻结待审的完整 SciRel 版本不是同一对象。
- **ReviewDecision**：绑定 draft ID、专家身份、动作和说明。身份由宿主提供，动作语义由 SciRel 定义。
- **ReleaseManifest**：绑定 candidate ID/digest、draft digest、approved asset IDs、catalog ref/digest、wheel ref/digest 和实现版本。
- **Workflow state snapshot**：由 SciRel 序列化当前 candidate、自动检查结果、draft/review 历史和 release，供工作台查询或进程重启后恢复。它不承载宿主平台字段。

SciRel 可以通过宿主 artifact store 保存 `scirel.workflow-state.dev` 快照；这只是状态恢复记录，不是第二套科学资产真值，也不要求 SciRel 引入数据库。

冻结待审版本至少绑定 Git tree/提交、参与审核的 exact documents、科学增量与受影响依赖闭包、验证证据，以及已构建的 wheel/catalog 摘要。证据复用须核实实现、合同、依赖和适用环境仍未变化；机械版本号或文案变化本身不触发全库科学重审，但发行工程验证仍需重做。此版本审核与晋级记录尚未由当前 `WorkflowRecord` 实现。

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

模型准备开发整合与审核材料时必须同时检索当前开发基线、当前未发布候选池和本次 L1，并保留对照的确切版本与来源；与尚未被专家观测的候选重复或可合并时，优先更新、合并或撤回该候选，减少专家对已知重复内容的审核。进入 `review_in_progress`、已审核或已批准的候选不可静默改写，只能以关联返工或新候选表达变化。冻结待审版本发生实质变化也必须形成新的待审版本。

撤回未观测候选只是候选存储或队列取消引用，不新增科学状态；通用 Agent run 证据可以保留，但不再投影为待审核对象。已经发生专家观测的内容不能用这一方式消失。

候选文档是专家审核的主入口。新增或改变公共资产时，其中拟议的 canonical asset document 必须使用现有 `scirel.asset-document.v1` 合同；候选代码和候选测试用于核对其主张。缺少科学关系、单位、坐标、适用域、失败语义或证据时登记 gap，不从名称、源码相似度或项目经验猜补。

审核工作台只展示 SciRel 的 draft、证据、依赖和候选差异。CodeFusion 提供 UI、身份和动作投递；审核结论写入 SciRel workflow 记录。

逐项审核结论只覆盖候选中明确列出的内容。可信版本审核覆盖冻结快照相对上一可信版的累积科学变化及受影响反向依赖；它不因逐项候选结论而自动完成。改变科学合同、API、依赖或测试主张必须反映在新的待审版本和增量中，不能静默扩大认可范围。

## 开发整合与候选冲突

隔离开发分支可在专家审核前持续整合、修复、测试和构建内部 wheel；原 Claude Code、CodeFusion 或 Codex 运行不需要等待专家。并发整合仍需对照实际基线，避免候选覆盖彼此或其他贡献者的修改。逐项审核工作台可以继续分配大量候选，但不是开发代码进入隔离分支的前置门禁。

每次整合先把候选比较时的 Git base 与当前开发基线比较：

1. 相关资产、公共合同、依赖、TaskGraph 和 patch hunk 均未变化时，可按提案整合代码和测试；
2. 基线有无关变化但 patch 仍能原样应用时，应用后运行 affected tests 和候选声明的直接测试；
3. 同一科学身份、公共合同、依赖闭包、TaskGraph 或 patch hunk 已变化时，停止自动套用，不采用 last-write-wins；
4. 冲突候选基于最新基线重新比较并形成关联处置，即使变成重复或直接复用也保留来源与比较证据；
5. 旧审核记录保持冻结，只证明旧候选曾获审核，不能自动认可新代码或新的待审版本。

这里不把开发合并、版本审核与发行压成逐项 workflow 状态。`approved` 保留逐项审核含义，但旧 `release` API、插件完成事件与直接 finalizer 已 fail closed；版本级确认与发布绑定需要后续实现。冲突时保留原审核证据，重新比较受影响关系。

允许候选增量堆积在 artifact、review directory、branch 或 worktree 中，也允许隔离开发分支的已整合内容进入内部 import、内部 wheel 和标明非可信的开发 pilot catalog。它们不得通过面向用户的可信 catalog/runtime 投影；定期功能审查不能替代冻结版本的专家认可。

## Release 门禁

目标上，公开 release 必须从专家认可的确切可信版本构建，并满足下列门禁。当前 `scripts/check.ps1 -Mode release`、workflow 和插件旧入口均拒绝逐项 `approved` 到发行的转换；版本级专家认可与发行绑定尚未实现。

1. 待审版本的累积科学增量及反向依赖已获专家认可，且发布构建只包含该确切版本；
2. 待审版本的认可范围没有未解决的科学 gaps，且包含明确的标准化资产集合；
3. 每个资产都有稳定 `asset_id`；
4. 实际 diff、资产文档和测试与认可快照可核对，catalog、wheel 和 release manifest 来自同一构建结果；
5. manifest 绑定获认可的确切版本与实际构建 artifact，相关 candidate/draft digest 仍可追溯且一致；
6. release version 与 catalog/document implementation version 一致。

开发期合同使用 `.dev` schema；首条稳定闭环后统一冻结为 `v1`，不保留旧 `.dev` 流程兼容分支。

## 测试要求

每个 workflow 变更必须覆盖直接状态转换测试。科学资产测试仍由 `scripts/check.ps1 -Mode affected` 根据资产和 TaskGraph 反向依赖选择；无法归属的 workflow、plugin 或公共合同变化 fail closed 到全套测试。

生命周期 fixture 可以在没有 CodeFusion、数据库、网络和源项目 checkout 的环境中验证 candidate、draft 和逐项 review，以及旧 release 入口的拒绝；它不声称能替代模型从真实 L1 完成科学整合。
