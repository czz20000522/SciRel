# SciReL 接入 CodeFusion 的纵向链路方案

写给两边的人看。结论先行，细节在后。基线：SciReL `origin/main` = `e7fa1bba`，CodeFusion 只读参考，未改其代码。

## 结论先行

- **接入点在 CodeFusion 的 application 层**：`application/codefusion-application-product` 的 `POST /api/product/chat/submit`。不是 kernel，也不是 platform。
- **SciReL 侧提供的是"分发包 + 命令行"，不是库依赖，也不是 CodeFusion 的 tool schema。** 一次 SciReL 计算在 CodeFusion 眼里就是一条普通 `shell` 调用。
- **三件分离**：科学 wheel、不可变 catalog（带 `snapshot_sha256`）、文档与 `scirel-solving` skill 是三个独立输入，任何一个缺失都不能宣称整条链路走通。
- **最小切片不需要 adapter**：一次普通 chat submit → 选定 skill → shell 里跑 `tools/query.py describe` → 装 wheel → 调用一个公开函数 → 有界结果投影。

## 一、接入点在哪一层

### 三层的职责与为什么只选一层

| 层 | CodeFusion 具体位置 | 职责 | 能不能承载 SciReL |
| --- | --- | --- | --- |
| kernel | `kernel/codefusion-kernel-tools`（`SHELL_TOOL_NAME = "shell"`）、`kernel/codefusion-sandbox-runner`、`kernel/codefusion-kernel-protocol` | 冻结 Tool Plan、执行沙箱、记录 typed call/result timeline | **不能**。kernel 是 domain-neutral 的，一旦认识 SciReL 就把领域知识写进了中立层 |
| platform | `platform/codefusion-skill-owner`、`platform/codefusion-artifact-owner`、`platform/codefusion-resource-owner` | 身份、skill 版本解析、资源准入、交付回执 | **不能单独承载**。它只解决"谁被允许"和"产物归谁"，不发起计算 |
| application | `application/codefusion-application-product`（`/api/product/chat/submit`）、`application/codefusion-application-session` | 把一次用户请求组成一次 Agent run：解析会话/项目、冻结 skill、装配工具、推进 turn | **是这里**。只有这一层同时握有"用户意图 + 选定 skill + shell 授权"三样东西 |

结论：**SciReL 是 application 层发起的一次外部能力交付，执行面借用 kernel 的 `shell` 工具和 sandbox runner，产物登记在 platform 的 artifact owner 下。** CodeFusion 不解析 SciReL 的请求或结果字段，不建 SciReL 专用的 model-tool schema，也不从 skill 文本里推权威。

### SciReL 侧对外提供什么

| 交付物 | 位置 | 形态 | 说明 |
| --- | --- | --- | --- |
| 科学 wheel | 分发包 `wheel/` | `.whl` | 只含 `scirel` 科学 API，**不含** `scirel_adapter` |
| catalog 快照 | 分发包 `catalog/` | 每个资产一份完整 JSON 合同 | 不可变，带 `snapshot_sha256` |
| 发现索引 | 分发包 `index/` | 由合同元数据派生 | 不是第二份分类表 |
| 查询 CLI | `tools/query.py` | `describe` / `browse` / `search` / `get` | 标准库实现，错误是 JSON envelope + 非零退出码；**不跑科学** |
| 可选 MCP | `tools/server.py` | stdio 或 loopback Streamable HTTP | 只是传输适配层 |
| 方法 skill | `skills/development/usage/scirel-solving/` | SKILL.md + references | 外部 agent 按它组织求解步骤 |

**明确不提供**：`scirel_adapter` 分发。当前 wheel 里没有它。

**已裁定：adapter 从验收口径移除，不单独立项。** 理由是它和"不建议给 CodeFusion 单做一套 SciReL 专用接口"是同一件事的两面——最小切片走的是普通 shell + wheel + CLI，本来就没有 adapter 的位置；为了一个验收条目去补一份分发物，等于把"中立层不认识领域"这个前提再破一次。将来真需要"SciReL 作为一等工具"时按新需求立项，不按今天的口径补。

## 二、数据怎么过去

### 字段级对应

| SciReL 侧 | 形态 | 进 CodeFusion 的哪一环 | 落在哪 |
| --- | --- | --- | --- |
| wheel 文件 | `.whl` | `resource_ref` 准入 → sandbox 内可见 | 项目私有环境（`python -m pip install <wheel>`），或预置镜像 |
| catalog 目录 | 目录树 | 同上，作为项目资源 | 项目工作区，或镜像内 `CODEFUSION_RUNTIME_ASSETS_ROOT` |
| `describe` 结果 | JSON：`runtime.wheel`、`snapshot_sha256`、`wheel_sha256` | shell tool result | typed timeline 里的一条 tool result |
| 科学调用返回值 | Python mapping（命名结果，例如 `distribution`、`density_m3`） | **不进 CodeFusion schema** | 用户交付物：项目工作区里的文件 |
| 失败信息 | 非零退出码 + JSON envelope，或 `ValueError` | shell tool result 的失败分支 | 同上，`execution_failed` |

### 关键约束：结果不回流

SciReL 的计算结果是**用户的交付物**，落在项目文件里，不变成 CodeFusion 的字段、状态或节点。CodeFusion 侧只记录三件事：这次 shell 调用发生了、它的有界输出是什么、产物登记在哪。

这条是硬边界。一旦把 `density_m3` 之类塞进 CodeFusion 的 schema，就等于让中立层承载领域语义，后面所有跨项目复用都要付代价。

### 身份与 pin

- `snapshot_sha256` 和 `wheel_sha256` 从 `describe` 取，之后 `search`/`get` 都要带上作为 `--expected-*`，漂移即失败。
- catalog 的 root digest 由 `scripts/build_catalog.py` 生成，`ThinMcpAdapter` 在服务任何操作前校验它——但当前没有 adapter，所以这条只在 adapter 路径上成立。

## 三、失败怎么暴露

原则只有一条：**不许静默跳过。要么明确失败，要么明确"结果未知，不要盲目重试"。**

| 情形 | SciReL 侧表现 | CodeFusion 侧应表现成 | 不许做的事 |
| --- | --- | --- | --- |
| 输入不合法 | `ValueError`（合同 `failure_semantics.invalid_input` 已声明） | shell 结果 `execution_failed`，stderr 原样保留 | 不许 catch 掉换成默认值；不许"重试一次" |
| 计算产生非有限值 | `ValueError`（`runtime_failure`，合同要求 fail-closed） | `execution_failed` | 不许放宽容差重算 |
| 环境缺失（wheel 版本不符、依赖缺、catalog digest 不符） | 安装或导入失败，非零退出 | `validation_failed` 或 `execution_failed` | 不许绕过 sandbox 在控制机装依赖；不许改包依赖声明迁就 |
| 超时 | 进程被杀 | `result_unknown`（原因 `request_cancelled` / `lease_expired`） | **不许自动重放**；恢复语义要单独取证 |
| 结果不可信 | SciReL 自己的校验判定不过（例如残差超标） | **不是 CodeFusion 的状态**。交付物里如实写 limitation，投影照转 | 不许把它翻译成"成功"；也不许翻译成 CodeFusion 的失败状态 |
| 进程崩溃 / 交付未确认 | — | `result_unknown` | 不许把未知当成功 |

现有状态词（CodeFusion 侧，只读核对）：`validation_failed`、`execution_failed`、`denied`、`result_unknown` 见 `kernel/codefusion-kernel-protocol/src/lib.rs:597`；失败原因 `request_cancelled`、`result_unknown`、`lost_ownership`、`lease_expired` 见 `src/trace.rs:1076`；产物可用性 `Unavailable` 见 `platform/codefusion-artifact-owner/src/artifact_record.rs:42`。

**"结果不可信"这一行要特别说清**：那是科学判断，归 SciReL；CodeFusion 只负责把 SciReL 说的 limitation 原样转述。两边都不许把它折叠成自己的状态词，否则"跑通了"和"结果对"会被混成同一件事。

## 四、今晚能验证的最小纵向切片

### 最小切片（一次容器内跑完）

1. 普通 chat submit，`selected_skill_names=["scirel-solving"]`，不带 adapter。
2. sandbox 内执行 `python tools/query.py --root <pkg> describe`，从结果里取 `snapshot_sha256` 和 `wheel_sha256`。
3. `python -m pip install <pkg>/wheel/<wheel>`，然后跑一个**纯计算、不依赖外部数据**的公开函数——建议 `scirel.kinetic.neutral-total-collision-frequency`（合同已绑定测试，输入全是数组，无文件依赖）。
4. 把结果写进项目工作区的文件，作为交付物。
5. 断言：shell 退出码 0、typed timeline 里有一条 `shell` 调用与结果、交付物文件存在、投影里能看到 limitation 段。

**不需要**：adapter 三件套、prepared image、reviewer workbench、重启恢复。

### 要等主链路闭合的

- 生命周期验收：Product 重启后读回真实结果、再在新 turn 消费。这条依赖 CodeFusion 的恢复语义先落地。
- Linux/amd64 跨设备抽查。

**adapter 路径已移出验收口径**，不算"待闭合"，也不再是阻塞项（见第一节）。

### 入场券：30 行参考程序（已写好）

`examples/consumer/minimal_scirel_call.py` 是最小切片的第一行代码，不是示意。CodeFusion 侧可以直接把它粘进 sandbox：

```sh
python <分发包根>/tools/query.py --root <分发包根> describe   # 取 snapshot/wheel 的 pin
python -m pip install <分发包根>/wheel/<wheel>
python minimal_scirel_call.py --out result.json
```

程序本身只做四件事：解析 `--out`、调 `assemble_neutral_total_collision_frequency`、把结果写成 JSON 交付物、退出码 0。失败就让它抛出去，不 catch、不重试、不填默认值——那正是 SciReL 合同里 `failure_semantics` 要求的 fail-closed。

选这个函数当切片对象的理由：输入全是数组、不依赖任何外部数据文件、合同已绑定测试（`tests/kinetic/test_neutral_frequency_assembly.py`），而且它的零直径语义是显式声明的哨兵值（见 `#117`），不会在边界上给出模棱两可的答案。

**它还没有被任何测试覆盖**——写这份规格时没有开容器。接进最小切片时应当顺手补一条断言它退出码和输出文件形状的测试。

## 五、SciReL 侧最少要改哪几处

先把话说清楚：**接入本身几乎不需要改 SciReL**。现有分发包已经能支撑最小切片。真正要动的只有下面三条，按必要性排序：

1. **什么都不用改就能跑最小切片。** wheel、catalog、`tools/query.py`、`scirel-solving` 都在，`build_pure_delivery.py` 能产出完整分发包。这是这一轮最重要的结论。
2. **参考程序已补**：`examples/consumer/minimal_scirel_call.py`。现在 CodeFusion 侧不用再摸一遍公开 API 才写得出第一行。它还缺一条测试，接进切片时补。
3. **`describe` 的 runtime 声明需要一次核对**：确认它输出的 `runtime.wheel` 与分发包里的实际文件名一致，且 `runtime-requirements.txt` 与 wheel 的 `Requires-Dist` 不矛盾。这条我没在容器里验过，只读了文档，属于待验证项。

**不建议做的**：为 CodeFusion 单独做一套 SciReL 专用接口。一旦有了专用接口，最小切片就不再走"普通 shell"这条路，也就失去了"中立层不认识领域"这个前提。

**已解除的阻塞**：adapter 路径不再阻塞任何事，它已从验收口径移除（见第一节）。

## 六、待验证 / 没做的事

- 没有在容器里跑过任何东西（按指示不占容器）。上面关于 `describe` 字段的描述来自 `tools/docs/PURE_CONSUMPTION.md`，不是运行结果。
- CodeFusion 侧只做了只读核对：路由名、工具名、状态词都给了文件行号；没有跑他们的主链路，也没有改他们任何文件。
- CodeFusion 的 `docs/implementation/scirel-outbound-consumer.md` 与本文口径一致；本文只补了"哪一层、字段怎么对应、失败怎么落"这三件它没展开的部分。
