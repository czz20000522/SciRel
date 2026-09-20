# CodeFusion 宿主插件需求

## 边界

CodeFusion 是领域中性的 Agent harness。它提供模型循环、上下文压缩、workspace、skill
snapshot、工具、权限/审批、执行、恢复和通用运行证据，不理解 SciRel 的去重、变体、合并、
标准化或科学审核语义。

SciRel 拥有两类能力：

- `scirel-integration` skill 定义模型如何从只读 L1 和当前 SciRel 基线形成专家可审查变更；
- SciRel 代码与测试提供确定性门禁、审核状态和 release 绑定。

CodeFusion 不需要新增 SciRel 专属数据库表、task/projection/finalize/receipt 协议或候选状态机。
它也不得从通用 run/job 状态推导科学批准或发布。

## Agent 调用

一次整合调用只向中性 harness 提供：

1. 可选 skill snapshot 及其内容身份；
2. 一个或多个只读 L1 目录；
3. 一个从冻结 SciRel baseline 派生、可写且隔离的候选 worktree 或输出目录；
4. 当前未发布候选池的只读比较视图；
5. 完成任务所需的通用文件、终端和测试权限；
6. 任务目标，以及完成后需要运行的确定性验证命令和成功/失败判据。

模型直接读取 L1 与冻结 SciRel，按 skill 选择检索、临时脚本、数值实验和测试，并只在隔离区准备候选文档、代码和测试。CodeFusion
不要求模型生成固定 manifest、receipt、workspace 布局或 SciRel JSON patch。运行证据可以记录
输入引用、skill identity、worktree/base、候选三件套、执行命令、退出状态和输出 artifact；这些
都是通用 harness 事实，不是科学结论。

同一调用方式必须也能由 Claude Code、Codex 或其他 harness 使用。SciRel 专属适配只能作为
可选 skill、命令或 UI extension 提供，不能进入 CodeFusion 的通用 Agent kernel。

## Plugin release 输入

CodeFusion 对 SciRel 的安装/更新只需要理解以下中性引用：

- 固定的 `plugin_id=scirel` 和 registration `release` 中的不可变 `plugin_release_ref`；
- `release.artifacts` 中的 skill bundle ArtifactReference，media type 为
  `application/vnd.agent-skills.bundle+zip`；
- 与运行时版本一致的本地 catalog ArtifactReference，media type 为
  `application/vnd.scirel.catalog-snapshot+zip`；
- `release.skill_entrypoints` 中绑定到 skill bundle artifact 的可移植相对路径；
- 可选 `release.connectors` descriptor，仅声明协议族、通用 capability refs 和 endpoint ref；
- 版本锁定的 opaque `release.runtime_dependency_refs`。

运行开始时固定这一组引用；插件更新或卸载只影响新运行，不改变进行中的 turn。宿主不解析 bundle
内的科学正文，也不从 catalog HTML 页面抓取机器合同。开发期登记样例见
[`contracts/examples/scirel-plugin-registration.dev.json`](../../contracts/examples/scirel-plugin-registration.dev.json)。

初始消费容量按 skill bundle 32 MiB、压缩 catalog snapshot 512 MiB 预留。它们是宿主安装策略，
不进入 registration wire contract，也不是永久科学规则；有真实 release 证据后可以调整。SciRel release
声明的三个主入口是 `scientific-computation-asset-extraction`、`scirel-integration` 和 `scirel-solving`。
registration 不携带 `implicit` 标志；是否自动选择入口由宿主的 application intent、skill owner policy 和
kernel grant 决定。其余 specialist skills 由入口按需加载，避免把全部科学方法和资产合同送入基础上下文。

开发样例中的 `cf://artifact/...` 与 digest 是 wire-shape 占位。真实登记必须先由 CodeFusion ArtifactOwner
接收 release 产物，再替换为 owner 签发且与正文一致的 ref/digest；样例本身不是发布或上传证据。

## 确定性门禁

门禁可以验证已经稳定且无需科学推理的事实，例如：

- 资产文档 schema 和必需字段；
- 公共 callable 是否存在；
- 直接测试映射和受影响 TaskGraph 反向依赖；
- 普通 TaskGraph 是否为 DAG；
- 测试、构建、catalog/wheel/release digest 是否一致；
- 审核状态是否合法，未解决 gap 是否阻断 release。

门禁失败只说明可验证条件未满足。它不能自行发明单位、坐标、科学关系或修复内容。模型在
SciRel worktree 中完成实际修复后重新运行门禁；自动检查结果不得通过 `asset_updates` 或其他
通用 patch 字段修改 candidate。

`scripts/build_l1_inventory.py` 等工具可以作为模型的参考探针使用，不是调用前置条件，也不是
CodeFusion 需要实现或理解的协议。

## 专家审核插件

模型在冻结基线外形成专家可审查的候选文档、候选代码、候选测试和逐项关系说明后，SciRel 可以通过
CodeFusion 通用 UI extension、artifact store 和身份能力承载专家审核：

- SciRel 定义 draft、gap、审核动作和 release 的领域含义；
- CodeFusion 提供页面壳、身份、通用 artifact 存储、动作投递和平台审计；
- SciRel workflow snapshot 作为插件 artifact 保存，不拆成 CodeFusion 专属科学表；
- 只有专家批准且 release 门禁通过的资产进入 catalog/runtime。

候选进入工作台队列不等于专家已经观测。`review_pending` 内容仍可由后续模型运行合并、替换或撤回；队列列表不得因此自动冻结候选。专家首次打开完整三件套时，CodeFusion 必须先把 `start_review` 动作原子地交给 SciRel，并只展示该动作返回的同一 `review_in_progress` 快照。不得先展示详情再改变状态。此后所有实质修改走返工或新候选，避免专家看到的内容在背后变化。

候选提交后，原 Agent run 即结束；CodeFusion 不需要为人工审核保持 Claude Code 或其他 harness 会话。工作台还应展示 SciRel 插件投影出的“已批准待固化”和最近一次固化冲突证据。批准后的固化是新的通用 Agent run：它对照候选记录的 Git base 与当前 SciRel HEAD，由 SciRel skill 决定是否原样应用或生成需要重新审核的新候选。CodeFusion 只负责调度、artifact 和页面承载，不实现科学冲突规则。

审核 extension 可以返回状态驱动的展示数据，但 CodeFusion 只把它视为插件不透明内容，不把
字段提升为通用平台协议。旧的第二阶段人工准入页面和状态不再位于主链；确认无消费者后可以
删除，不需要兼容开发期记录。

## 版本

开发期接口可以继续使用 `.dev` 标识。首条真实 L1 到专家审核闭环稳定后统一冻结为 `v1`，
上线前不保留旧开发接口的兼容分支。
