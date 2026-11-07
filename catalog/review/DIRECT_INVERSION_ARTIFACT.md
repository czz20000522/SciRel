# 直接各向异性反演的准入图产物判定说明

`scirel.inference.direct-anisotropic-inversion` 仍处于 hold。本文记录该资产
被卡住的确切原因、字节核验证据、流程漏洞与修法，供人工审查接手。

结论先行：**缺失的不是"忘了提交一次产物"，而是准入环节本身允许提交不带图产物。**
仓库内现存的三份图文件都不是准入原件，本机无法恢复；放行要么拿到 Pleiades 准入原件，
要么由维护者显式记录"用现存快照替代"。

## 一、admitted graph artifact 是什么

它是 Pleiades 分解项目提交、经 `contracts/admission/` 准入的那份任务图**原始字节**，
成对文件：

```text
graph.py
task_graph.yaml
```

审查记录在案的身份是三段摘要标识：

```text
graph.py         6d1c3b52…
task_graph.yaml  997b3335…
vcommit          d196…
```

这三段标识最早写在本文的完整版里（提交 `602348c5`），后来本文被压缩为 11 行摘要，
标识只留在 Git 历史中。

它在仓库内的落地形态经历过两次改名：

```text
tests/graph_contracts/direct_anisotropic_inversion/task_graph.yaml
  → 15c26699（refactor: organize tests by functional domain）
tests/cross_domain/direct_anisotropic_inversion/composition.yaml
```

合同的 `composition` 块是这张图的投影：合同的节点、端口与边必须能对应到图文件，
`scripts/validate_asset_documents.py` 只校验这份投影自身的结构闭合。

## 二、由什么生成

```text
Pleiades 分解（模板 skills/extraction/.../artifact_template_pack/task_graphs/）
  → graph.py + task_graph.yaml
  → scripts/prepare_admission.py 生成 FINAL.json / FILES.json / PATH_MAP.json / ROOT.sha256
  → scripts/validate_admission.py 准入校验
  → SciRel 侧落成 tests/cross_domain/<资产>/composition.yaml
  → scripts/validate_asset_documents.py 校验合同 composition 投影
```

准入的绑定是三层互指的：`FILES.json` 列出全部 payload 成员，`ROOT.sha256` 绑定三个控制文件，
`FINAL.json` 以固定文件名绑定前两者。`FINAL.json` 的 `compositions[]` 用
`directory` + `name` 指向图产物所在目录。

## 三、为什么这份产物会缺

主因写在审查提交 `58bcf017` 的信息原文里：

> keep only direct anisotropic inversion held because Pleiades FINAL lacks the
> exact admitted graph artifact.

即 **Pleiades 的 FINAL payload 本身就没有携带这份图产物**，只留下准入摘要标识和一个
后的快照（later snapshot）。仓库里从来没有过准入原件，所以这不是"git 删了还能找回"的情形。

### 字节核验（可重跑）

| 候选来源 | SHA-256 |
| --- | --- |
| 当前 `tests/cross_domain/direct_anisotropic_inversion/composition.yaml` | `563d23f8d3d5812555dcac044c4f322d139094a5589c7562dc3345a05145956d` |
| 历史 `tests/graph_contracts/direct_anisotropic_inversion/task_graph.yaml`（`cd576478`、`15c26699^`、4 个 `refs/tags/archive/pleiades-*`） | `1b086c7ffe8df78bbc10dfa56f063887936a5e455d6e88eacac662af07be8912` |
| 悬空 blob（`composition_fixture.py::_run_composition` 版） | `2495099e8f1845a85a7667677fd4ff4b9eea032c017ecb0a670b5074aea1e422` |
| 记录中的准入原件 | `997b3335…`（**仓库内不存在**） |

核验范围：全部 Git 历史、4 个 `refs/tags/archive/pleiades-*` 归档标签、76 个 dangling blob
（`git fsck --lost-found` 逐个取字节算 SHA-256）。`997b3335…` 与 `graph.py` 的 `6d1c3b52…`
均无命中；仓库内唯一的 `graph.py` 是模板包里的
`skills/extraction/.../TASK_GRAPH_NAME/graph.py`，SHA-256 为
`dedc26baeb4b1d285d9fd95c8ef76cc3171c9bd04444205414da6cba9c2b1619`，不是准入原件。

### 现存快照与合同的图不是同一版

- 现存 `composition.yaml`：6 个节点 —— `latin_hypercube_initial_design`、
  `equilibrium_solver_port`、`diagnostic_evaluator_port`、`residual_reducer_port`、
  `trial_evaluator_port`、`direct_optimizer`。
- 合同 `composition.nodes`：8 个节点 —— 另有 `observation_layout`、`status_annotation`，
  并带 `search_state` 反馈边（`bounded_parameter_search`）。

两者的节点集合不同，说明现存快照既不是准入原件，也不足以充当合同的绑定依据。
现行 `tests/cross_domain/direct_anisotropic_inversion/test_composition_direct_anisotropic_inversion.py`
中的 `test_yaml_declares_explicit_cross_node_ports` 只断言若干子串，不比对节点集合，因此没有拦住这个偏差。

## 四、流程根因

1. **准入侧允许不带图产物。** `scripts/validate_admission.py` 对
   `FINAL.json.compositions[].directory` 只做路径安全检查，既不校验该目录下有 graph 文件，
   也不要求该文件成为 `FILES.json` 成员。提交方漏带图产物时，准入仍然通过。
2. **仓库侧没有任何门禁看护图产物。** `scripts/review_gate.py` 与
   `scripts/review_harness.py` 中不含 "composition" 字样；图文件既没有被记录身份，
   也没有被校验字节。图文件可以被静默替换成任意后来的快照。

两条合起来的效果：准入能合法地不带图产物，仓库即使发现也拦不住，只能靠人工在 hold 说明里留一句话。

## 五、修法

准入侧与仓库侧各补一处，缺一不可：

1. **准入侧（已落地）**：`scripts/validate_admission.py` 现在要求
   `compositions[].directory` 必须真实存在于包内，且该目录下的
   `graph.py`、`task_graph.yaml`、`test_task_graph.py` 三件套都必须是 `FILES.json` 成员
   （常量 `GRAPH_REQUIRED_MEMBERS`，取自
   [intake 目录约定](../../skills/extraction/scientific-computation-asset-extraction/references/intake_directory_contract.md)）。
   没有图产物的提交在准入环节就失败，不再留到 SciRel 审查时才发现。
2. **仓库侧（已落地，只覆盖本资产）**：图文件字节被测试钉住，
   见 `test_composition_direct_anisotropic_inversion.py` 里的
   `test_composition_yaml_bytes_are_locked` 与
   `test_composition_yaml_is_not_the_admitted_artifact`。任何改动现存
   `composition.yaml` 的尝试都会先撞上这两条测试，必须回头面对"这是不是 substitution"。
3. **仍未做（需单独立项）**：把上一条泛化成覆盖全部 `composition.yaml` 的清单
   `contracts/composition-artifacts.json`，由 `scripts/review_gate.py` 校验清单与实际字节一致。
   清单的绑定状态可分三种，都不构成科学结论：

| 状态 | 含义 | 门禁要求 |
| --- | --- | --- |
| `admitted` | 文件字节即准入原件 | 记录的 `admitted_sha256` 必须等于实际字节；该资产不得被 hold |
| `unverified-snapshot` | 只有快照，无准入记录可比 | 必须写明原因，不得空口通过 |
| `blocked` | 准入原件标识已知但字节缺失 | 该资产必须在 `HOLD.json` 中被 hold |

   本次没有做泛化清单，因为它要动 `review_gate.py` 的注册表结构并连带改
   `tests/tooling/test_review_gate.py` 的夹具，超出本 PR 的改动面；本 PR 只把
   `direct-anisotropic-inversion` 这一份钉死。

## 六、放行条件（本资产）

按上节修法落地后，本资产还需要在一件事上作出决定，才能解除 hold：

**要么**取得 Pleiades 准入原件（`task_graph.yaml 997b3335…` / `graph.py 6d1c3b52…`）
并原样入库，清单标 `admitted`；**要么**维护者显式批准用现存快照替代，并在本文件与清单里记录
substitution。后一种做法按 `catalog/AUDIT.md` 的 "no source / missing artifact" 条款属于审查判定，
不能由实现者自行决定。

决定之后，按既有规则重跑：

```text
tests/cross_domain/direct_anisotropic_inversion/test_composition_direct_anisotropic_inversion.py
tests/cross_domain/test_inference_physical_closure.py
tests/cross_domain/test_anisotropic_inference_independent.py
```

三项全绿，且图产物字节与合同 `composition` 节点集合一致，才满足
`HOLD.json` 里 "restore the exact admitted graph artifact and rerun composition and
physical-closure tests" 的要求。

## 七、需要 Pleiades 侧提供什么

解除 hold 只差外部原件，需要 Pleiades 侧提交以下五项：

1. `graph.py` 的准入字节，**完整 SHA-256 为 `6d1c3b52…` 的那个版本**——现有记录只留 8 位十六进制，
   请一并给出完整 64 位摘要，否则拿到文件也无法比对。
2. `task_graph.yaml` 的准入字节，对应完整 SHA-256 `997b3335…` 的版本，同样需要完整摘要。
3. 该产物所在的 Pleiades FINAL 提交标识（记录里写作 `vcommit_d196…`，请给完整提交 SHA）。
4. 承载这两份文件的 FINAL payload 原样归档（含 `FINAL.json` / `FILES.json` / `PATH_MAP.json` /
   `ROOT.sha256`），以便 SciRel 侧用 `scripts/validate_admission.py` 复验准入本身成立。
5. 若原件已不可得，请明确回复"不可得"，并说明当时 FINAL 为何未携带 `compositions[]` 产物；
   是否接受 snapshot 替代由 SciRel 维护者按 `catalog/AUDIT.md` 判定，不在 Pleiades 侧决定。

本文不判断任何模型或精度是否可接受。
