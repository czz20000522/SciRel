# 外部 Agent 整合方法

Codex、Claude Code、CodeFusion 等 harness 承载模型；SciRel 方法与科学结论不由宿主拥有。
阶段职责和验证边界见 [开发流程](../development-process.md)，D2 入口为
[scirel-integration](../../skills/integration/scirel-integration/SKILL.md)。按入口路由加载专业方法，不全量加载 skill。

## 输入与执行

读取确切的只读 L1、当前开发 Git base、上一可信版本（若有）和相关未发布候选。
在隔离工作树中比较、去重、修正、组装和测试，可构建内部开发 wheel/catalog。
不要修改上游交付；重复吸收、来源参考和实现说明写在本阶段派生代码的注释/docstring 或接续记录中。
正式审查文档面向人，在代码稳定后生成；结构完整不替代 D1 源实现/数值对照。

从相关源码、测试、图和文档渐进发现已有能力，catalog 缺项不证明库里不存在。
按科学关系、单位、约定、适用域、状态和数值方法比较；名称和相似结果只用于筛选。
工具只保护可确定的结构/安全/依赖，不替代科学理解，也不规定固定探针或反复重算。
证据失效时按影响补验；可归属的未变结果直接复用。

## 输出与最终审核

提交可运行开发版本、逐输入处置、保留变化、实际验证及证据上限。
完全复用或重复项保留目标绑定和依据，不重复写正式文档或生成审核项。
只为最终保留的新/变资产生成唯一 exact document，审查说明引用它并解释差异。
最终待审相对上一可信版本汇总累积科学变化；人类最终拍板，开发不逐次等待。

```powershell
python scripts/submit_standardization.py <candidate.json> <submission.json> <candidate-pool.json> <new-workflow.json>
```

命令校验绑定、完整输入记账和内容结构，不执行 AI 或证明科学等价。
review_units 与 input_dispositions 合并覆盖全输入；有增量生成 review_pending，纯无变化生成 no_changes。
上传固定确切版本，后续 AI 返工另起关联 successor；原 Agent 无须等人工继续存活。
Agent 审查、工程验证、人类认可和公开发行分别记录；可信发行仍必须符合批准内容与发布门禁。

## Harness 对照

给不同 harness 相同的 L1、SciRel 基线、候选视图、skill 和目标。
比较科学判断、真实库改动、重复/变体识别、验证质量和耗时，不比较是否机械地产生更多文档。
记录真实命令/结果/版本和执行时间；不要把历史样本数量、固定调用次数作为通过阈值。
