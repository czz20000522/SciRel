# SciRel 科学使用指南

从物理问题开始选择计算功能，再查看相应的 Python 调用。本指南面向使用 SciRel 的研究者和 Agent。

当前指南绑定测试材料中的 **`0.2.0.dev2+review20261008`**。它介绍该 wheel 实际提供的磁约束聚变兼容功能；
后续版本的新增能力在新的版本绑定中维护，不能凭本页推断已经进入当前包。详见 [本版范围与安装](version-and-installation.md)。

## 磁约束聚变 · 托卡马克约化模型

| 我想做什么 | 物理功能 | 实现入口的例子 |
| --- | --- | --- |
| 表示温度或密度的径向分布，求径向变化率 | [径向剖面、坐标与边界](tokamak/radial-profiles.md) | `make_grid`、`radial_gradient` |
| 建立等离子体初态，更新状态与物理时间 | [状态初始化与时间演化](tokamak/state-and-evolution.md) | `initial_state`、`zero_d_step_with_dt` |
| 选择磁几何，计算模型的热和粒子扩散系数 | [平衡几何与输运闭合](tokamak/equilibrium-and-transport.md) | `solve_fixed_boundary_equilibrium`、新经典输运入口 |
| 查看加热、电流组成及模型诊断量 | [加热、电流与诊断](tokamak/heating-current-diagnostics.md) | `total_heating_sources`、`compute_diagnostics` |
| 改变电流和加热随时间的输入，计算目标函数梯度 | [时变驱动与优化](tokamak/control-and-optimization.md) | `Waveform`、`optimize_controls_optax` |

这些是物理功能主题，函数是各主题的实现入口。比如“径向温度剖面”需要坐标、温度输入、边界约定、导数和结果解释，
不等于一个名为“梯度算子”的资产。

## 开始使用

1. 安装指定 wheel 及所选功能的依赖，核对版本。
2. 阅读所需物理功能的单位、近似和边界条件。
3. 从 [可复现小例子](examples.md) 开始，再查看 [公共调用参考](api-reference.md)。
4. 解释结果时保留该功能的证据范围；正常返回不等于模型已经经过独立科学或实验验证。

测试包中的 `queries.md` 是自然语言任务；`expected/` 的实际参考输出仅供测试负责者验收，不能作为 Agent 的输入目录。
指南说明这些问题的物理含义和接口选择，不代替平台完成依赖下载、文件访问、计算、显示与下载。

## 阅读方式

- **网页**：`SciRel-使用指南.html` 可直接打开，也可作为静态页面托管；含物理主题导航、搜索和函数参考。
- **Markdown**：同一份源文档可分段阅读、检索和版本审阅。
- **Agent**：先读 `agent/route.json`，选择物理主题，再读相应主题或 API 文件；无需加载所有函数合同。

这套查询文件是使用说明的渐进读取入口。出库执行方法由单独提供的 skills 指导；实际能力选择以同版本
catalog 的 route、summary 和 canonical exact record 为准。调用参考里存在、但尚无 exact record 的兼容入口，
不因此成为 skills 可自动选入计划的合格能力。当前开发 catalog 只收录 7/32 个入口，覆盖状态为 partial。

本版共有 **32 个公共入口，分布在 9 个模块**；其中 **7 个入口有已绑定的详细资产合同**。
其他入口保留兼容调用说明，其完整科学有效性、独立运行范围和部分依赖仍有限定。详细列表放在调用参考，而非一级导航。
