---
language: zh-CN
---

# <项目名称> 科学计算资产拆解报告

## 执行状态

- 交付状态：`<complete | discovery_only | incomplete>`
- 拆解阶段：`<candidate_map_only | partial_extraction | final_extraction>`
- 完整性声明：`<not_claimed | confident_no_remaining_valuable_candidates>`
- 主要资产：<算子/任务图摘要>
- 工程细节：`extraction_ledger.md`
- 框架图：`program_framework_map.md`

<说明本次交付内容及最重要的边界。>

## 范围摘要

- 源快照：<不可变标识或摘要>
- 纳入范围：<源码根目录/模块族>
- 排除范围：<范围和原因>
- 源码修改：`<none 或说明>`
- 项目源码运行时：<可移植标识>
- 可复用资产运行时：<可移植标识>

## 已交付资产

- 算子：<摘要>
- 任务图：<摘要>
- 配置 schema：<摘要或 none>
- 包质量：<有证据支撑的简短说明>

## 验证摘要

- 改动包测试：<摘要>
- 最终包测试：<摘要>
- 源码对比：<direct/fallback/blocker 摘要>
- 脱离源码组合验证：<摘要>
- 最终格式门禁：<摘要>
- 清理：<摘要>

## 覆盖与风险

| 优先级 | 能力/框架切片 | 状态 | 影响 | 工程细节 |
|---|---|---|---|---|
| <high/medium/low> | <切片> | <closed/open/terminal> | <通俗影响说明> | `<ledger section/id>` |

## 完整性声明

<准确说明哪些内容可脱离源码运行，哪些输入仍由调用者提供，以及是否仍有值得继续拆解的源码工作。不得超出已执行证据。>
