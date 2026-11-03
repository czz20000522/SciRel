---
language: zh-CN
---

# <任务图名称>

## 概述

<面向物理审核专家说明整体科学问题、参与的物理状态、预期求得的量及结果解释；不要仅罗列函数调用顺序。>

## 框架映射

| 字段 | 值 |
|---|---|
| 主框架节点 | `N1` — <名称> |
| 覆盖方式 | `full` / `slice` / `support` |
| 相关框架依赖 | `N1` 或 `none` |
| 嵌套任务图 | `task_graphs/<name>` 或 `none` |

## 科学目的

<说明各关系为何需要组合、物理量如何传递、耦合与闭合依据、不可交换的顺序、反馈或收敛条件，以及失败时哪些物理结论不再成立。给出必要方程、假设和证据限制；不能用编排节点列表代替科学解释。>

## 输入

- ascii_input_a: 含义：<meaning>；shape/轴序：<shape/axes>；单位：<units or convention>；约束：<rules>；所有权：<caller/node>。

## 输出

- ascii_output_a: 含义：<meaning>；shape/轴序：<shape/axes>；单位：<units or convention>；约束：<rules>；消费者：<caller/node>。

## 组成

### 节点

- `node_id`: kind=<scientific_operator/nested_task_graph/support_action>; asset/callable=<relative reference>; role=<scientific role>.

### 边

- `producer.output -> consumer.input`: <why ordering or binding is required>.

## 行为与边界

<源码支持的状态、坐标、归一化、分支或模型假设；支持与排除的框架切片；非法状态、缺失端口、空域、分支、反馈或收敛行为。>

## 验证与溯源

- `<source-root-relative/path.ext:1-10>` (`<symbol>`): <节点、边、顺序、状态传递或分支语义>。
- <端到端 oracle、嵌套节点/反馈/边界检查和阈值；不把运行日志复制到这里。>
