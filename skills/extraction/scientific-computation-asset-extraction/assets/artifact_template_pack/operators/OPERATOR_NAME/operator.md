---
language: zh-CN
---

# <算子名称>

## 语法

`actual_callable(ascii_input_a, ascii_input_b, ...) -> {ascii_output_a, ascii_output_b}`

## 说明

<面向物理审核专家说明：研究什么对象、解决什么物理问题、所求量代表什么、采用什么关系及为何适用。用物理量解释主要输入输出及其联系；不能用调用签名或案例替代。不要说明它来自哪个项目、PFM 节点或任务图。>

## 输入参数

- ascii_input_a: 含义：<必须填写该物理量或数值量及其在关系中的作用，不能只写“调用者提供”>；shape/轴序：<scalar or axes>；单位：<unit or source-not-declared convention>；约束：<range, finite, index, grid rule>。
- ascii_input_b: 含义：<必须填写证据支持的物理量或数值量>；shape/轴序：<...>；单位：<...>；约束：<...>。

## 输出参数

- ascii_output_a: 含义：<必须填写该结果表示的物理量或数值诊断及其用途>；shape/轴序：<scalar or axes>；单位：<unit or convention>；约束：<finite/conservation/index rule>。
- ascii_output_b: 含义：<必须填写证据支持的结果含义>；shape/轴序：<...>；单位：<...>；约束：<...>。

## 科学或数值定义

<给出必要的方程、离散规则、插值、矩阵/模板或伪代码，并定义对调用者有意义的符号、归一化、符号、索引和单位约定。不能用“以实现或测试为准”替代科学定义。>

## 行为与边界

<声明适用模型、参数域、端点/ghost/夹取/退化域、非法输入和失败行为；只陈述源码或测试支持的内容。有限性和 shape 检查不是完整的行为说明。>

## 验证与溯源

- `<source-root-relative/path.ext:1-10>` (`<symbol>`): <所保留的公式、循环、权重、分支或边界语义>。
- <已执行或计划的源码对照、方程 oracle、不变量、边界检查，以及指标/阈值；不把运行日志复制到这里。>
