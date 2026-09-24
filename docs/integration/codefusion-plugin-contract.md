# SciRel 与 CodeFusion Plugin Contract

## 两个接面

SciRel 与 CodeFusion 只有两个需要长期维护的接面：

1. 中性 Agent 调用：CodeFusion 像 Codex、Claude Code 一样承载模型执行；
2. 专家审核 UI：CodeFusion 提供通用页面、身份、artifact 和动作投递，SciRel 提供领域内容。

CodeFusion 不实现 SciRel 的 L1 解析、去重、变体、合并、标准化或验证策略，也不新增
SciRel 专属 task、projection、finalize、receipt 或数据库状态。

## 中性 Agent 调用

调用输入为：

- `scirel-integration` skill snapshot，可带版本或内容摘要；
- 只读 L1 目录引用；
- 从确切 SciRel 开发 Git base 派生的可写隔离分支/worktree，以及只读的上一可信版引用（若存在）；
- 当前未发布候选池的只读比较视图或 artifact refs；
- 通用文件/终端/测试工具和权限；
- 自然语言任务目标与完成后的确定性验证命令。

模型可在隔离开发 worktree 整合 `src/scirel`、文档和测试，并构建内部 wheel；不修改 L1、可信版或已冻结待审版。输出是通用运行证据：候选三件套、开发改动、模型/skill/harness 身份、实际命令、
退出状态和需要保存的 artifact。CodeFusion 不解析逐项关系判定，也不要求固定的中间 manifest、
JSON patch 或目录布局。

SciRel 可提供 `scripts/build_l1_inventory.py`、affected-test selector 和资产文档 validator 作为
可选工具。它们不是 Agent 调用协议，CodeFusion 无需调用或理解其输出。

### Plugin registration

开发期示例为
[`contracts/examples/scirel-plugin-registration.dev.json`](../../contracts/examples/scirel-plugin-registration.dev.json)。
它直接使用 CodeFusion 中性的 `PluginRegistration` wire shape：`release` 包含 `plugin_release_ref`、
ArtifactReference、skill entrypoint、connector descriptor 与 runtime dependency refs；外层只声明通用
capability、scope 和 UI extension。CodeFusion 把完整 release 当作一次运行固定的 opaque snapshot。旧运行
继续使用已固定 snapshot；更新或卸载只阻止新运行选择旧 release。

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
模型按照 skill 在隔离开发分支整合代码和测试，再对实际变更运行检查。

CodeFusion 的 run/job/attempt/timeout/权限和 transport 结果属于平台事实，不能转换为科学成功、
拒绝或批准。SciRel 的检查失败也不能伪装成平台故障。

## 专家审核 UI

模型完成候选准备后，SciRel 向 UI extension 提供：

- 候选文档、候选代码 patch/worktree 和候选测试 artifact；
- 逐项复用、重复、变体、组合、新增、冲突或未决判定；
- 资产文档、测试和实验依据；
- 未解决 gap 及允许的审核动作。

专家身份由宿主提供，审核动作语义由 SciRel 定义。SciRel 可以把 workflow snapshot、review
decision 和 release manifest 作为普通 plugin artifact 保存；CodeFusion 只存 reference/digest
及平台审计，不把其中字段复制到通用表，也不根据 run 状态推导可用审核动作。

`review_pending` 只表示候选已进入队列，并不表示专家已看到完整内容，因此该候选仍可被模型更新。队列列表可以展示不构成科学审核的最小索引信息；第一次打开完整候选详情是观测边界。CodeFusion 必须在返回详情前原子地投递 `start_review`，持久化 SciRel 返回的 `review_in_progress` 状态，并把同一快照展示给专家。转换失败时不得展示旧详情。`review_in_progress` 之后不再接受 `update_draft`，实质变化必须形成返工 draft 或关联新候选。

通用宿主只调用两个 review wire operation：

- `scirel.review.list_items`：body-wire 每次输入一个宿主持有的 exact current-state artifact ref/digest/body，返回 0 或 1 项的 `scirel.review-item-index.dev`；CodeFusion 可以把多个单项结果作通用聚合。索引项只有 opaque `item_ref`、以输入 artifact digest 表示的 `revision`、两行显示索引和 opaque `detail_action_ref`。该操作不执行 `start_review`，也不返回 workflow、资产、证据或动作内容。
- `scirel.review.open_item`：输入同一个 exact current-state artifact ref/digest/body，并在严格 `operation_payload` 中原样携带 list 返回的 `item_ref` 和 `revision`。SciRel 要求 `revision == artifact_digest`，并校验三者属于同一 `review_pending` draft，执行 `start_review`，返回唯一的 `scirel.review-item-snapshot.dev` artifact body。该 artifact 内同时包含 `review_in_progress` next state 与专家看到的 exact view；相同 immutable 输入重放得到相同内容寻址 artifact。

actor、tenant/project、correlation 和 idempotency 留在通用宿主 envelope。CodeFusion 在同一事务中登记 open result artifact/lineage/receipt，并以输入 artifact ref/digest 为 expected current pointer 做 CAS；只有 CAS 成功后才展示返回快照。SciRel 不维护 current pointer，不从 run status 推导领域状态。CAS loser、result unknown、缺 artifact 或 digest 不匹配时均不得显示详情。

只有专家认可的确切版本通过 release 门禁后，其资产才进入面向用户的可信 catalog/runtime。隔离开发分支的内部 wheel 和开发 pilot catalog 仅供验证；candidate、临时报告、模型完成状态和测试通过都不能单独产生发布。版本认可属于 SciRel，不进入 CodeFusion 通用 kernel 状态。

候选提交工作台后，产生它的 Agent run 可以结束。当前逐项 workflow 的 approved 后固化 run 与“approved 且没有 release”投影仍是旧接口行为，不等于版本级可信认可；后续迁移只需由 SciRel 插件提供相应领域投影，不要求 CodeFusion 理解科学冲突。开发整合遇到同一科学身份、合同、依赖闭包、TaskGraph 或 patch hunk 冲突时，SciRel 在最新开发基线上重新比较，不覆盖旧审核事件。

## 当前代码定位

`src/scirel_workflow/` 和 `src/scirel_plugin/` 是审核状态、artifact 摘要和 release 绑定的开发期
实现。其 L1 body adapter、wire fixture 和本地 HTTP listener 只用于本仓库确定性合同测试，
不是 CodeFusion Agent kernel 的生产接入要求，也不能取代 skill 驱动的语义整合。

`FakeHost` 只证明 SciRel 领域代码不依赖 CodeFusion 数据库或网络。真实联合验收应使用同一
中性 invocation 分别运行 Claude Code 与 CodeFusion，再比较候选文档、候选 diff、证据和验证结果。

## 版本

当前开发期 artifact/schema 使用 `.dev`。首条真实闭环稳定后统一冻结为 `v1`；冻结前不为旧
开发协议保留兼容分支。
