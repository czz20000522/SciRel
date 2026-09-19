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

`draft` 和尚未被专家打开的 `review_pending` 可以复用同一 `draft_id` 替换内容，不产生需要专家逐份处理的草稿历史。工作台在返回完整候选详情前执行 `start_review`；进入 `review_in_progress` 才表示发生专家观测并冻结三件套。`needs_evidence` 和 `rework_requested` 通过新的 draft 返工并保留已发生的审核记录。每个 workflow 保留一个 `run_id`，draft 和 review action 按顺序记录；开发期不引入额外的版本服务。

候选生成与候选审核/固化是两个异步流程。模型提交 draft 后即可结束运行，不等待耗时不可控的人工审核。`approved` 表示该候选有资格进入独立固化流程，不表示已经修改 SciRel。只有批准内容完成固化且 release 构建成功，才能产生 `released`。candidate、draft、候选代码和候选测试不得在批准前进入维护基线、运行时 catalog 或 wheel。

## 领域对象

- **L1 payload**：来源项目拆解阶段保存的输入。SciRel 只依赖 payload 和来源 artifact reference，不依赖源项目 checkout、CodeFusion 数据库或网络。
- **L1 inventory**：`scripts/build_l1_inventory.py` 提供的可选结构探针。它可以帮助定位相对路径、直接测试和显式依赖缺口，但不是模型整合 L1 的必经输入或标准化协议。
- **CandidatePackage**：绑定 `run_id`、来源 artifact、source digest、单一 `project_id`、候选资产和自动检查结果。多项目 inventory 必须先拆成 `to_project_l1_payloads()` 的独立 payload，不能在一个 candidate 中混合推进。
- **Candidate comparison view**：冻结 SciRel 基线、全部当前未发布候选和本次 L1 输入的联合检索视图。它用于提前发现重复、可合并项和冲突；未发布候选不是可运行资产，也不改变权威基线。
- **StandardizedDraft**：待专家审核的候选，包含以文字为主的候选文档、候选代码/patch、候选测试、依赖关系、科学证据、capability gaps，以及本次比较使用的冻结 SciRel Git base。未发生专家观测前可替换；当前名称是开发期命名，不表示已经写入 SciRel。
- **ReviewDecision**：绑定 draft ID、专家身份、动作和说明。身份由宿主提供，动作语义由 SciRel 定义。
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

模型准备候选时必须同时检索冻结基线、当前未发布候选池和本次 L1；与尚未被专家观测的候选重复或可合并时，优先更新、合并或撤回该候选，减少专家对已知重复内容的审核。进入 `review_in_progress`、已审核或已批准的候选不可静默改写，只能以关联返工或新候选表达变化。

撤回未观测候选只是候选存储或队列取消引用，不新增科学状态；通用 Agent run 证据可以保留，但不再投影为待审核对象。已经发生专家观测的内容不能用这一方式消失。

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

release 前必须满足：

1. draft 已获得 `approved`，且批准的候选代码/测试已经按候选文档应用到 SciRel；
2. draft 没有未解决 gaps，且包含至少一个标准化资产；
3. 每个资产都有稳定 `asset_id`；
4. 实际 diff、资产文档和测试与批准候选可核对，catalog、wheel 和 release manifest 来自同一构建结果；
5. manifest 中的 candidate/draft digest 与实际 artifact 一致；
6. release version 与 catalog/document implementation version 一致。

开发期合同使用 `.dev` schema；首条稳定闭环后统一冻结为 `v1`，不保留旧 `.dev` 流程兼容分支。

## 测试要求

每个 workflow 变更必须覆盖直接状态转换测试。科学资产测试仍由 `scripts/check.ps1 -Mode affected` 根据资产和 TaskGraph 反向依赖选择；无法归属的 workflow、plugin 或公共合同变化 fail closed 到全套测试。

生命周期 fixture 可以在没有 CodeFusion、数据库、网络和源项目 checkout 的环境中验证 draft/review/release artifact 关联；它不声称能替代模型从真实 L1 完成科学整合。
