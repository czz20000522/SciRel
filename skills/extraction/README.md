# 拆解与出题

两个入口彼此独立：

| 入口 | 做什么 | 产物 |
| --- | --- | --- |
| [`scientific-computation-asset-extraction`](scientific-computation-asset-extraction/SKILL.md) | 从来源中找出骨架，与冻结版 SciReL 比对取补集，按最终形态实现 | 拆解包（补丁加说明材料），交给合并线 |
| [`scientific-requirements-extraction`](scientific-requirements-extraction/SKILL.md) | 从来源、论文和案例出题 | 能力题（题面加隐藏测试），进入题库 |

题库和拆解互不依赖：有题库时，拆解可以优先拆有题的能力；没有题库时，拆解照常进行。
设计理由见 [`docs/maintainer/supply-pipeline.md`](../../docs/maintainer/supply-pipeline.md)。
