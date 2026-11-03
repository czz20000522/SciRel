# 独立案例包约定

一题一个自洽根目录，落在项目材料根的 `projects/<project-id>/case/<中文题目>`。根目录名与 `case.json.title` 一致；搬移整个题目录后仍可从该根定位全部题目材料。旧布局直接迁移，不增加旧路径解析或第二套规格。校验器不绑定盘符或搬移后的父目录。

根下只有 `题面/`、`参考/` 两个目录，以及 `case.json`、`replay.py` 等小入口文件（可选 `README.md`）。来源、运行配方和历史记录均在 `参考/` 内，不另设会话或跨题材料目录：

```text
<中文题目>/
  case.json
  replay.py
  题面/
    problem.md
    inputs.json
    output-spec.json
    acceptance.md
  参考/
    provenance.json
    compare.py
    reference-run.json
    replay-contract.json
    replay-run.json
    reference-output/result.json
    source/source.tar.gz
    source/LICENSE
    runtime/runtime.json
    runtime/README.md
    runtime/Dockerfile
    runtime/requirements.lock
```

## 两侧材料与离散语义

`题面/` 是做题者所需的完整公开材料：自然语言物理需求、适用模型和约定、全部输入数据/参数范围、输出量/单位/形状/坐标及公开验收规则。输入不能藏在参考侧、另一个题或外部会话路径。可以公开样例，但隐藏测试值与参考答案不因此必须公开。解题者仅凭题面即可理解和完成要求。

当要求的离散数组或积分结果依赖插值、重采样、路径闭合或求积约定时，公开规格须明确数学算子、必要的端点条件与运算顺序（如先求范数再插值），或明确允许的实现差异及其有依据的验收预算。连续物理公式不能隐含决定离散答案；缺少会改变答案的约定时保留 `HOLD`。

`参考/` 包含冻结来源身份、科学能力映射、源码/许可、依据、参考结果、比较器、误差依据和可重建运行环境。来源输出到公开物理量的单位/轴序等转换可复核。需要重放的源码/数据必须实际包含在本题内，不能把另一题、项目源码工作副本或历史机器路径当作输入。公开语义只保留一个精确规格，多个字段可指向同一题面文件。

源码置于 `参考/source/`：完整冻结归档，或足够重放且保留许可/署名的合法 source slice。大包可用同卷普通文件硬链接节省空间；硬链接必须只读，且不会因删除原名字而失效。不得用符号链接、junction 或失效链接冒充材料。切片须在来源记录中说明范围与省略，不得悄悄改科学行为。

环境可声明外部 OCI 镜像、工具与系统库，不必把数 GB 镜像复制进每题。题内仍需 Dockerfile、依赖锁、明确环境身份及可移植重放入口；镜像存在不替代可复建配方。外部依赖声明不能包含题目所需源码、科学数据或另一题。`replay.py` 从题根解析本题相对路径，不能写死原宿主盘符、项目工作路径或另一题路径；容器内部路径与显式环境工具身份不等同于外部题目输入。

## case.json

JSON 的 `public`、`private` 是语义键，路径分别使用 `题面/...` 与 `参考/...`，统一使用 `/` 分隔。材料引用不得含绝对路径、盘符、`..`、反斜杠或链接。以下为材料齐全、已实际重放后的结构示意，身份与执行结果必须换成实测事实：

```json
{
  "id": "neutral-problem-id",
  "title": "中文题目",
  "status": "reference-reproduced",
  "coverage": ["physical-capability-id"],
  "replay": "replay.py",
  "public": {
    "statement": "题面/problem.md",
    "inputs": ["题面/inputs.json"],
    "output_spec": "题面/output-spec.json",
    "acceptance": "题面/acceptance.md"
  },
  "private": {
    "provenance": "参考/provenance.json",
    "source_kind": "archive",
    "source_bundle": "参考/source/source.tar.gz",
    "source_licenses": ["参考/source/LICENSE"],
    "runtime_manifest": "参考/runtime/runtime.json",
    "replay_contract": "参考/replay-contract.json",
    "reference_run": "参考/reference-run.json",
    "replay_run": "参考/replay-run.json",
    "comparator": "参考/compare.py"
  },
  "open_issues": [],
  "scientific_review": "pending"
}
```

`source_kind` 为 `archive`（`source_bundle` 指非空归档文件）或 `slice`（指非空源码目录）。`source_licenses` 指向该题实际包含的许可文件。`provenance` JSON 至少含非空 `source_revision` 和非空字符串数组 `anchors`；其余论文/锚点和切片说明按实记录。

`status` 仅有 `candidate`、`reference-reproduced`、`frozen`，没有额外的“reference-ready”状态。`scientific_review` 为 `pending`、`accepted` 或 `not-requested`。候选可缺源码封装、配方、比较器或运行证据，但 `open_issues` 必须用 `HOLD: ...` 明确缺口；已填写的路径/材料依然必须有效，不能用坏路径表示待补。候选必须有来源身份；计入需求交付的候选必须题面完整，缺少科学定义的内部草案继续保留待审说明，不能计入完整题目。

用户允许来源失败后先交题目时，题面完整的 `candidate` 可作为需求交付，参考复现仍单列缺口。`参考/` 保留已有来源信息、真实失败命令/日志/退出状态及适用环境，不要求伪造结果、比较器或成功重放入口；未取得的材料不填成已存在路径。普通包校验检查这些现有声明；它不证明题意科学完整，仍需逐题审阅。缺少会改变答案的模型、单位、边界或必需输入时，题面尚未完成，不能仅因保留了题目目录就记作需求已交付。

## 运行配方与重放闭包

`private.runtime_manifest` 的 JSON：

```json
{
  "recipe": "参考/runtime/README.md",
  "dockerfile": "参考/runtime/Dockerfile",
  "dependency_locks": ["参考/runtime/requirements.lock"],
  "external_dependencies": [
    {"kind": "oci-image", "identity": "actual-image-reference-and-digest", "purpose": "runtime base"},
    {"kind": "tool", "identity": "actual-container-tool-and-version", "purpose": "build and run"}
  ]
}
```

外部依赖 `kind` 可为 `oci-image`、`tool`、`system-library`，每项写实际身份和用途；锁文件固定本题所需包/系统依赖，配方说明构建、运行、挂载、输出和停止核验。不把几 GB 镜像复制入题，也不在配方执行中重新下载隐含源码/科学输入来填补缺包。

依赖锁必须实际保存依赖身份，不能以非零文件长度代替内容检查；空白、仅注释或整份只有 `==` 等标点的捕获失败不是锁。校验器会拒绝这些空内容，但不会因此证明任意格式的锁完整，或证明配方实际消费了锁；后两项仍需工程审阅/重建证据。

`private.replay_contract` 的 JSON：

```json
{
  "entrypoint": "replay.py",
  "cwd": ".",
  "command": ["python", "replay.py"],
  "inputs": ["题面/inputs.json", "参考/source/source.tar.gz"],
  "outputs": ["参考/reference-output/result.json"],
  "runtime": "参考/runtime/runtime.json"
}
```

`command` 采用 `[工具名, "replay.py", ...参数]`，工具身份在环境中声明，参数不能指向宿主外部材料。`inputs` 包含全部 `public.inputs`、`source_bundle` 及其他实际读取的题内输入；`outputs` 是本题重放保存的参考结果。配方、Dockerfile 和锁通过 runtime manifest 闭合，不能依赖其它会话目录。公开题意、来源脚本、比较器、运行入口和历史记录一并随题目录移动。封装后实际从题根执行重放，保存真实 `replay_run`，不能仅复制旧 source-run 并改成新路径后宣称已重放。

## 原始运行与封装重放记录

`private.reference_run` 保存来源真实运行记录，其 `command` 是当时实际 argv，绝不为美化或迁移改写；历史容器 `recipe` 原文同理。历史宿主路径仅是证据，不充当新重放依赖。原始回执如需原样留存可放在 `参考/` 的历史子目录；当前引用的结果路径必须能在本题定位。

来源运行 JSON 至少为：

```json
{
  "status": "PASS",
  "command": ["actual-historical-executable", "actual-historical-entrypoint"],
  "exit_code": 0,
  "environment": {"identity": "actual-runtime-or-image-identity"},
  "outputs": ["参考/reference-output/result.json"],
  "container": {"used": false}
}
```

`private.replay_run` 同样记录 `status`、`exit_code`、`environment`、`outputs` 与 `container`，另需 `cwd: "."`，`command` 必须是实际从题根执行且与 replay contract 完全相同的可移植 argv，`outputs` 与 replay contract 一致。不要把解释器真实身份/版本藏起来，可在 `environment` 声明；`command` 使用实际调用的工具名，而非虚构一条没有运行的命令。

使用容器时记录 `used: true`、实际 `identity` 和 `state_after`，最终状态仅可为 `exited`、`stopped` 或 `removed`。来源运行的 `container.recipe` 保留实际历史值，新重放由题内 runtime manifest 提供配方。

`reference-reproduced` / `frozen`，或校验器 `--require-reference`，同时要求：题内来源/许可、runtime recipe/Dockerfile/锁、相对重放合同/输入/输出、比较器，以及来源运行和封装重放均为真实 `PASS`、整数退出码 0、环境已记录、容器已停止。缺少新重放时状态保持 `candidate` 并保留历史运行事实。`frozen` 还需要 `scientific_review=accepted` 与题内 `private.review_record`，不能由自动校验升级。

人工科学接受 pending 本身不阻止已经满足上述工程条件的包记录为 `reference-reproduced`。源码失败后的题面交付不产生参考 PASS，不增加有效参考验证覆盖；实际失败和未运行应按各自事实记录。

校验器只检查所声明材料的封装闭包、路径边界和基本执行记录，不执行源码、比较器或容器，也不证明任意脚本没有未申报的动态依赖。实际题根重放与独立语义审阅分别提供运行和题意证据；物理正确性、容差和覆盖结论仍交指定科学审阅者。
