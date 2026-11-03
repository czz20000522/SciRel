# 求解样例

| 目录 | 内容 | 状态 |
| --- | --- | --- |
| [coil-offset](coil-offset/REPORT.md) | 圆环线圈上移 2 cm 对中心区磁场的影响 | 参考演示，展示按流程应该得到什么样的结果 |
| [negative-demo-20261029](negative-demo-20261029/README.md) | 十道旧题面 | 只作为物理需求来源，整理计划见 [PLAN.md](PLAN.md) |

这些样例用来检验流程，不随 skill 包分发，也不从 README 链接（README 会进入 wheel 元数据）。真正引导外部 agent 的是 `skills/development/usage/` 下的 skills。每个样例都走[求解流程](../skills/development/usage/scirel-solving/references/workflow.md)，报告遵循[报告格式](../skills/development/usage/scirel-solving/references/report-format.md)，并由 `tests/tooling/test_solved_examples.py` 校验。
