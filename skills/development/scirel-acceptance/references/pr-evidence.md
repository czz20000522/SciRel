# 把验收 receipt 变成 PR 证据

PR 上现在只有作者手贴的一段 `ALL GREEN`，而真正的证据是 `.git/scirel-acceptance/receipts/` 里的一份
receipt——评审者看不到，也没法核对。这一页规定怎么把 receipt 渲染成一条可直接粘贴、可逐字核对的 PR 评论块。

## 一条命令

在最终提交上跑过 `python3 scripts/dev_container.py check` 之后：

```sh
python3 scripts/acceptance_evidence.py
```

它会拿当前 `HEAD^{tree}` 和本机 `architecture` 去共享 receipt 缓存里找匹配的一项，打印下面这段模板。
找不到、过期、或工作区不干净时，脚本退出非零并说明原因，**不会**打印任何通过文案。

需要声明填表人时用 `--actor "名字 <邮箱>"`，否则取本机 `git config user.name` / `user.email`。

## 模板原文

脚本逐字输出下面这段（尖括号是实际值），改动模板必须同时改这里：

```markdown
### 本地容器验收证据

- 结论：本 clone 上某个 checkout 在该 tree 上跑过完整检查，`check_all.py` 以 `ALL GREEN` 结束，退出码 0
- 依据：`scripts/dev_container.py:867-873`，`run_check()` 只在检查退出码为 0 时调用 `record_check_receipt()`；因此存在匹配的 receipt 即等价于退出码 0
- 最终 tree：`<tree>`（HEAD 提交 `<短 sha>` <提交标题>）
- 架构（architecture）：`<arch>`
- 检查完成时间：`<本地时间带时区>`（UTC `<UTC 时间>`）
- receipt：`.git/scirel-acceptance/receipts/<文件名>`，schema 3，字段：schema/tree/architecture/checked_at_unix/command/image_id/image_ref/docker_context
- 匹配范围：receipt 存在本 clone 的共享 Git 元数据里，只按 tree + architecture 匹配，不记录执行者、机器名，也不记录由哪个 checkout 写入；`docker_context` 记的是解析值
- 填表人：<名字 <邮箱>>（填表人自行声明；receipt 不记录执行者，真正跑检查的人未知）
- 复核：`git rev-parse HEAD^{tree}` 应得到同一个 tree；`python3 scripts/dev_container.py check` 可复跑

> 该证据只覆盖本机 `<arch>` 引擎。跨设备抽查另行手动触发 `Cross-device check`；receipt 里的 `docker_context` 是解析值，不是机器名。
```

粘到 PR 的 `Checks` 段，保留原样的可复核命令，不要改写成叙述。

## 每个字段从哪来

| 片段 | 来源 |
| --- | --- |
| tree | `git rev-parse HEAD^{tree}`，与 receipt 里的 `tree` 完全相同才可用 |
| 提交短 sha 和标题 | 在 `git log` 里查使用该 tree 的提交，优先取当前历史中的那个 |
| architecture | `platform.machine()`，与 receipt 里的 `architecture` 相同才可用 |
| 检查完成时间 | receipt 的 `checked_at_unix`，同时给本地时间和 UTC |
| receipt 文件名与 schema | 缓存文件名由 `sha256(schema + tree + architecture)` 派生（`scripts/dev_container.py:632-635`） |
| 退出码 0 | 反推，依据 `scripts/dev_container.py:867-873`：只有 `check_all.py` 退出码为 0 时才写 receipt |
| 填表人 | 命令行或本机 Git 身份，**不是** receipt 字段 |

## 哪句话不许写

写错就等于造证据，评审会退回：

- 不写"某某跑了这次检查"。receipt 里没有执行者字段，也没有机器名字段（schema 3 的字段是
  `schema`/`tree`/`architecture`/`checked_at_unix`/`command`/`image_id`/`image_ref`/`docker_context`）。
- 不写"在这个 worktree 里跑的"。receipt 存在共享 Git 元数据里，同一 clone 的所有 worktree 共用一份缓存，
  只按 tree + architecture 匹配；正确说法是"本 clone 上某个 checkout 在该 tree 上跑过完整检查"。
- 不写"用了哪台机器"。机器名没有被记录；`docker_context` 虽然记了，但只能原样引用 receipt 里的值，
  不能凭印象写另一个；解析它的命令是 `python3 scripts/dev_container.py doctor`。
- 不写"退出码 0"却不给依据。结论后面必须带 `dev_container.py:867-873` 这条反推链条。
- 不写"全部通过"以外的结论（例如物理正确性）。检查只确认结构、回归和绑定，科学结论见
  `catalog/review/`。

## 什么时候 receipt 会作废

任何一条成立，就必须重跑 `dev_container.py check`，旧 receipt 不能再用：

- **tree 变了**：rebase、amend、新提交、改索引都会换 tree。这是最常见的一条，PR 合并前 rebase 到最新
  `origin/main` 之后一定要重跑。
- **换了架构**：receipt 按 tree + architecture 分开存放，Apple Silicon 的 `arm64` 和 CI 的 `amd64` 互不通用。
- **超过 30 天**：`CHECK_RECEIPT_MAX_AGE_SECONDS`（`scripts/dev_container.py:32`），过期条目会被裁剪。
- **被裁到 16 份之外**：缓存上限 `CHECK_RECEIPT_MAX_ENTRIES`（`scripts/dev_container.py:31`），按时间保留最近的。
- **schema 变了**：`CHECK_RECEIPT_SCHEMA`（`scripts/dev_container.py:30`）不一致的条目不再是命中；
  它们留在缓存里只作历史（prune 不删旧 schema），不作放行依据，靠一次完整检查重建。
- **工作区不干净时压根没写过**：`candidate_tree()`（`scripts/dev_container.py:646-658`）在有未暂存改动或
  未跟踪文件时返回 `None`，`record_check_receipt()` 直接放弃写入。主 checkout 里未跟踪的 `.worktrees/`
  会让它长期处于这一状态，见 #120。

## 核对别人的证据

拿到一条 PR 证据评论时，按下面三条核对，任一条不成立就不能当作通过依据：

1. 评论里的 tree 等于 `git rev-parse <PR head 提交>^{tree}`；
2. tree 对应的提交就是 PR 的最终提交，不是 rebase 前的旧提交；
3. architecture 是本机或本批次实际使用的那台引擎。

跨设备抽查由维护者手动触发 `Cross-device check`，那是另一条证据，不能和本机 receipt 混用。
