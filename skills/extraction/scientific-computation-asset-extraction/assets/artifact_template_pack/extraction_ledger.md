---
language: zh-CN
---

# <项目名称> 拆解台账

## 源码范围清单

| 项目 | 值 |
|---|---|
| 项目/范围 | <名称> |
| 源快照 | <不可变标识或摘要> |
| 纳入根目录 | <相对源码根路径> |
| 排除根目录 | <路径和原因> |
| 证据根目录 | <外部路径或标识> |

## 源码保全与修改审计

- 是否修改原始源码：`<yes/no>`。
- 是否使用探针工作副本：`<yes/no；外部位置>`。
- 运行时捕获位置：`<外部证据位置或 none>`。

## 状态词汇

- 处理：`candidate_pending_deep_extraction`、`processed`。
- 决策：`ACCEPT_OPERATOR`、`ACCEPT_TASK_GRAPH`、`SUPPORT_KERNEL`、`SOLVER_WORKFLOW_REWORK`、`REJECT`。
- 缺口：`extraction_gap`、`configuration_or_schema_need`、`ai_completable_glue`、`validation_oracle_gap`、`cannot_complete`。

## 资产台账

| 资产 ID | 框架节点/切片 | 源码锚点 | 目标关系 | 处理状态 | 决策 | 包路径 | 证据/测试 | 原因 |
|---|---|---|---|---|---|---|---|---|
| `<asset_id>` | `<node_id>` | `<path:line-line::symbol>` | <映射> | <状态> | <决策> | <相对路径或 none> | <结果/blocker> | <受限说明> |

## 缺口台账

| 缺口 ID | 框架边/能力 | 缺口类型 | 缺失合同/状态/oracle | 证据 | 影响 | 闭合条件 | 状态 |
|---|---|---|---|---|---|---|---|
| `<gap_id>` | `<edge_id>` | <规范缺口类型> | <缺失项> | <锚点> | <通俗影响说明> | <可验证条件> | <open/terminal/closed> |

## 受控补全记录

| 包/位置 | 新增 glue/修复 | 证据边界 | 已解决或避免的缺口 | 是否虚构科学逻辑 |
|---|---|---|---|---|
| `<package:file>` | <变更或 none> | <受限原因> | <缺口 id/kind 或 none> | `no` |

## 验证矩阵

| 需求 | 资产路径 | Oracle | 指标/容差 | 结果 | 外部证据 |
|---|---|---|---|---|---|
| <标准或自定义需求> | <包和 glue> | <独立或源码派生 oracle> | <指标> | <pass/fail/blocked> | <路径> |

## 格式偏离

| 路径 | 偏离 | 用户需求或原因 | 审核影响 |
|---|---|---|---|
| none | none | none | none |

## 最终清理与收尾

- 已删除生成产物：`<yes/no>`。
- 最终包摘要：`<digest or deferred>`。
- 剩余值得拆解的内容：`<none 或资产 ID>`。
