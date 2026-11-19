# T-2026-1203：哪些映射键需要公开承诺？

给两位 `api-reviewer`：请分别回答末尾两问，在[原工单](../../../tickets/scope/T-2026-1203.md)的审核平台记录选择和理由。此页是证据，不是签字。工单解释整个映射约定；下面四项只是目前[输出通道基线](../../../tools/docs/output-channel-baseline.json)里剩余的单输出合同，不是全库受影响资产清单。

## 消费者到底读了什么？

| 资产 | 本次任务实际取值 | 不构成承诺的部分 |
| --- | --- | --- |
| `scirel.io.eqdsk-class` | 从新写出的文件构造 `EQDSK(fname)`，用 `title` 和二维 `psi` 识别文件及磁通网格。 | 首读与重读比较 22 个夹具字段是防止丢数据，不代表下游逐个需要。无文件构造是空映射；加载后可修改。 |
| `scirel.kinetic.rational-jpole-evaluate` | 用 `result['ZJ']` 取复数响应，并与手算的单极点值比较。 | 未以运行时键清单推定诊断量都是公共字段。 |
| `scirel.neutrals.elastic-frequency-channels` | 用 `result['elastic_frequency_m_inv']` 取各位置的总系数，与逐位置通道和比较。 | 未要求返回所有内部通道，也未以一组输入外推所有物理工况。 |
| `scirel.kinetic.relativistic-codrift-generalized-spectrum` | 空输入例取 `result['spectra']` 作空批次处理。 | **未观测非空谱。** 空列表不证明非空列表内各谱的结构、排序或物理正确性。 |

复核：[EQDSK 单任务回放](README.md)、[其余三项可执行断言](../closeout/mapping_consumer.py)。后三项的顶层返回是映射；合同所写的数据类型描述的是载荷而不是顶层容器。不要用改算法、改返回类型或重写冻结判据来消除这项分歧。

更广的消费需求另有[多流体任务回执](../closeout/tasks/kinetic-multifluid-frequency.json)。`w1` 与 `componentwise_backward_errors` 服务于任务，两者不等价于“把扫描与求解记录中的每个诊断键都公开”。上游对照也不能代替决定：SciPy 1.18.1 对同一目标分别调用 `minimize`，BFGS 返回 `jac`、`hess_inv`，Nelder–Mead 返回 `final_simplex`，两者均是 `OptimizeResult`。这说明键可以有条件；不能据此直接推定 SciRel 的稳定键。

## 如何复跑三项取值

先按[复现说明](README.md)准备包与隔离解释器（`p` 为该运行目录），再运行：

```sh
python3 scripts/dev.py run "$p/consumer/bin/python" -IB examples/c4-usage-acceptance/closeout/mapping_consumer.py
```

本次冻结包源为 `c8faa8e7afd1b8b733cc908799ecbe0918779920`，与 [EQDSK 回执](c8faa8e7.json) 使用同一份 wheel（SHA-256 `2ea25bbd8d8050b11772c6f87b16b115f2b7690439424685fe036145b7c5db1d`）。三个实际结果分别是 `(-0.2+0.4j)`、`[1.75, 3.5] m⁻¹`、`[]`；三个断言均执行。它们是本轮新写的小任务，不是历史 C4 整轮复验。

## 需要分别裁决的两问

1. **选 A 还是 B？** A 用现有 `outputs[]` 机器可读地声明要承诺的业务字段，并说明它们来自映射，不把一个映射解释成多个 Python 返回值。B 保留单个映射输出，靠说明描述可用键，消费检查区分返回容器与键名。倾向 A 不等于已决定；两种方案都不需要先新增 schema 字段。
2. **承诺边界在哪？** 哪些键必有、哪些依输入才有、哪些纯诊断不保证？尤其请区分 `EQDSK()` 和从文件构造的对象；对非空 `spectra` 若需承诺元素结构，请先给一个可复现的非空消费场景。在两位审核人作出决定前，不改这些返回值、不删基线、不把现有字段判据改绿。
