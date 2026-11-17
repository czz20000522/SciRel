# 求解样例

| 目录 | 内容 | 状态 |
| --- | --- | --- |
| [negative-demo-20261029](negative-demo-20261029/README.md) | 十道旧题面 | 只作为物理需求来源，整理计划见 [PLAN.md](PLAN.md) |
| [c4-usage-acceptance](c4-usage-acceptance/README.md) | 交付包使用验收的冻结任务清单与消费协议 | 清单已固定并通过结构校验，尚未消费 |
| [c5-delivery-acceptance](c5-delivery-acceptance/README.md) | 真实交付包的打包与隔离环境校验回执、三个消费者任务、分级缺口清单 | 第二轮消费者实测已完成；缺口见 [GAPS.md](c5-delivery-acceptance/GAPS.md) |

这些样例用来检验流程。带参考答案的样例不放在公开仓库，以免成为验收题的答案来源。这里的内容不随 skill 包分发，也不从 README 链接（README 会进入 wheel 元数据）。真正引导外部 agent 的是 `skills/development/usage/` 下的 skills。每个已完成的样例都走[求解流程](../skills/development/usage/scirel-solving/references/workflow.md)，报告遵循[报告格式](../skills/development/usage/scirel-solving/references/report-format.md)，并由 `tests/tooling/test_solved_examples.py` 校验。
