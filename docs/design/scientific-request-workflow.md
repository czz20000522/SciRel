# SciRel 科学请求工作流设计

## 设计边界

本设计实现 [`scientific-request-workflow.md`](../requirements/scientific-request-workflow.md) 的最小
闭环。语义理解由加载 `scirel-solving` skill 的模型完成；SciRel package、catalog 和 adapter 只承担
已经稳定且可确定验证的合同。设计不新增通用 orchestration 脚本、治理数据库或与某个 harness 绑定的
运行协议。

```text
自然语言请求与用户数据
  -> 问题规范化与必要澄清
  -> catalog 渐进发现与 exact document 匹配
  -> 本次 TaskGraph 运行实例
  -> 执行前科学合同校验
  -> SciRel callable 执行
  -> 结果级科学检查
  -> 用户结果与审计说明
```

只有可见 release 中的资产参与发现和执行。候选池、审核记录和 L1 来源不进入本流程。release 标识可由
运行环境自动附在执行记录上，但流程不增加“证明该资产已获批准”的步骤。

## 四个逻辑产物

### Normalized Problem

它是模型对用户问题的可核对解释，不是数据库实体。内容按问题取舍，通常包括目标、输出、模型、关系
方向、未知量、几何、坐标、单位、归一化、输入、边界、闭合、容差、假设和未决问题。

模型先判断未决问题是否会改变科学身份、适用域或结果。会改变时停止并澄清；不会改变时可以采用明确
记录的默认值继续。

### Solution Plan

计划保存本次能力选择和动态组合。每个科学节点指向 exact asset ID；每条边说明端口含义以及必要的
无损表示适配。计划记录选择理由、适用域匹配、输入绑定、DAG 或反馈合同、执行前检查和结果级检查。

已有 TaskGraph 能完整解决问题时直接使用它。多个资产需要临时组合时，生成的只是运行实例；若组合
后来具有独立复用价值，应另走标准资产候选和专家审核流程。

### Execution Evidence

执行证据保存实际调用、已规范化参数、返回或异常、运行环境自动附加的 release 上下文，以及每项结果级
检查的输入和结论。大数组可以保存 artifact 引用和摘要，不要求复制到文本报告中。

检查由问题和 exact document 决定，不设置适用于所有科学领域的固定清单。资产自己的单元测试是发布
证据；本次请求的检查面向实际输入和组合，不重复运行整套资产测试。

### Result Explanation

结果解释从前三类产物投影面向用户的内容：问题理解、必要假设、求解方法、关键数值或文件、检查结果、
证据上限和剩余限制。它不得用“运行成功”替代物理解释，也不得输出模型隐藏思维链。

## Harness 与 SciRel 的职责

| 责任 | SciRel plugin | Harness |
| --- | --- | --- |
| 科学身份、适用域、端口和证据上限 | 定义 exact document | 读取，不改写 |
| 有界能力发现 | catalog 与 connector | 提供工具调用和上下文预算 |
| 自然语言问题规范化 | 定义方法 | 模型执行并与用户澄清 |
| 科学运行实例 | 定义 Operator/TaskGraph 语义 | 调度通用步骤和工具 |
| 科学计算 | 普通 Python callable | 准备环境、调用和收集结果 |
| 结果级科学检查 | 定义选择方法和可复用关系 | 根据计划执行 |
| 会话、身份、权限、资源、存储和 UI | 不拥有 | 拥有 |

CodeFusion 的通用执行图和 SciRel TaskGraph 是不同对象。前者可以承载后者一次运行的投影，但不能解释、
改写或复制其科学身份。Claude Code、Codex 和 CodeFusion 应能在相同请求、可见 catalog 和 skill 下完成
同一科学任务；比较重点是问题规范化、能力选择、连接、检查和限制，而不是措辞完全一致。

## 渐进发现与文档站

发布构建从 canonical exact documents 生成 route、summary、exact-record catalog 和人类文档站。模型先用
领域、关系方向、输出和模型等 route facet 获得有界 shortlist，再读取入围 exact documents。文档站展示
同一内容的可读投影，并提供相应机器记录链接；它不维护第二份科学事实。

`coverage.status=partial` 或分页未完成时，找不到候选只能产生有边界的搜索结论；完整 release 中不存在
适用资产时才形成 release 级 capability gap。

## 计划校验、执行和解释

计划校验分为结构、语义、组合和科学四层：callable/端口/shape；单位/坐标/轴序/归一化；模型/边界/
闭合/顺序/状态；适用域/残差/终止条件/证据上限。glue 只允许字段选择、容器整理和已声明的无损表示变化。

执行只发生在计划校验通过后。一次运行不触发全仓测试，只执行计划 callable 和本问题声明的结果级检查。
检查结果使用“通过、失败、不适用、未检查”表达。审计保存规范化问题、选择依据、端口绑定、实际执行、
检查和结果；release 上下文只是复现记录，不是用户请求中的独立证明任务。

## 轴对称平衡首轮样例

当前开发 catalog 中的 `scirel.geometry.axisymmetric-equilibrium-grid-support` 明确声明“不执行 field
solve”。因此首轮验证包含两个相邻但不同的请求：

- 完整平衡请求：若可见 catalog 没有覆盖所需模型、边界、闭合与求解关系的 TaskGraph，返回有边界的
  capability gap；网格映射不能冒充平衡求解。
- 已给定平衡的网格支持请求：选择现有 TaskGraph，执行后检查场/磁通/mask 的 shape 与有限性、材料支撑
  非空、PML 边界排除、PEC 排除和 coverage/clamping 诊断，并明确结果不是新的平衡解。

首轮由 skill 和任务证据承载四个逻辑产物。只有多个 harness 的真实运行出现稳定、重复的机器消费需求时，
才增加 schema 或确定性辅助代码。
