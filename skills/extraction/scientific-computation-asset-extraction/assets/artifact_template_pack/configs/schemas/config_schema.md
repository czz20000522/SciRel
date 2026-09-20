---
language: zh-CN
---

# <schema_name> 配置 schema

## 适用范围

<消费此可复用 schema 的算子或任务图。它声明语义，不是一次运行的具体 payload。>

## 字段

| 字段 ID | 类型 | 形状/轴 | 单位 | 有效范围 | 默认策略 | 所有者/生产者 |
|---|---|---|---|---|---|---|
| `<field_id>` | <scalar/array/string/enum> | <形状和轴顺序> | <单位> | <范围/选项> | <显式默认值或 required> | <caller/package output> |

## 跨字段约束

- <归一化、符号、索引、边界或兼容规则。>

## 变体

| 选择器 | 含义 | 必填字段 | 禁止字段 |
|---|---|---|---|
| `<variant_id>` | <分支含义> | `<field_ids>` | `<field_ids or none>` |
