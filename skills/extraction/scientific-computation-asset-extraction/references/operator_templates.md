# Operator Writing Guidance

`references/artifact_template_pack.md` and `assets/artifact_template_pack/` are the only canonical sources for package layout, single-language heading order, and field placement. Do not copy a second `operator.md` or `task_graph.md` template into this file.

本文件只解释如何填写正式模板，不再定义另一套格式。

## 服务对象与目标

算子和任务图文档服务于物理领域的审核专家，帮助其判断科学含义、合理性与适用范围。
算子首先说明研究对象、所求物理量、关系依据、假设、单位与归一化、适用边界和证据限制。
任务图首先说明为何需要组合这些关系、物理状态如何传递、耦合与闭合依据、反馈或收敛条件，
以及最终结果能够支持什么结论。不能用接口列表、调用流程或代码案例代替这些解释。
科学场景仅用于帮助理解；签名是辅助实现定位，调用方法不是文档的中心或审核通过条件。
本文档只服务当前拆解产物；外部工作流如何保存、审核或改写其他材料不属于本说明。

## 内容规则

- 算子文档固定为 `language: zh-CN`；不写中英混排、双语标题、审查者注释或逐行翻译。
- 算子说明独立科学关系与输入输出物理量之间的映射。PFM 节点、父任务图、推荐编排和来源项目关系属于项目级框架图或目录索引，不是算子定义。
- 每个输入和输出都给出含义、shape/轴序、单位（或明确的单位约定）和有效性约束；每个公式、离散规则或算法都定义对调用者有意义的符号和约定。
- 正文先用独立的物理对象和数值约定说明端口；源码变量别名、源码调用顺序、项目节点和源码文件只可出现在 `验证与溯源`，不能承担用户理解合同的职责。
- `验证与溯源` 至少包含一个具体文件行号锚点，以及可执行的 oracle、指标和阈值。
- 受控补全与语言改写放在 `行为与边界`，并同步记录到项目级 `extraction_ledger.md`；不得增加 `Implementation Notes` 顶层章节。
- 同一科学关系只保留一份完整的内部科学审核页，不在提取阶段生成面向用户的第二份页面。正文以科学问题、关系与假设、输入输出物理含义、适用边界和证据为主，不要求单独的调用或应用案例章节。资产站文档由人类专家独立编写，不复用算子或任务图审核文档；本流程不设计其内容或写作方式。

### 字段语义闭合（提取冻结条件）

在填写模板前，先为每个输入和输出建立字段语义记录：物理量或数值量、在方程/更新中的作用、单位与归一化、shape/轴序/索引、生产者和消费者、生命周期、适用域、边界/退化行为、失败行为、证据锚点。字段名和 Python 类型只能定位源码，不能证明这些内容。

以下内容属于提取失败，不能留在正式算子中，也不能靠审核页面翻译掩盖：

- 为多个字段重复同一段模板说明，却没有分别解释它们的物理或数值含义与关系角色；
- 只写有限性、同形状、类型或 `source-unit`，却没有说明该量是什么、代表什么或怎样参与计算；
- “最小调用”加签名转发，或只链接 `test_scientific_operator.py` 而没有具体物理场景、适用条件和可核对结果；
- `Advance ...` 等未翻译的说明，以及把“以实现/测试为准”当作科学定义或行为边界。

当字段含义、单位、归属、来源状态或适用边界无法由证据确定时，保留候选并登记具体的
`extraction_gap`、`configuration_or_schema_need` 或 `validation_oracle_gap`。不要猜测，也不要把未知
转嫁为调用者自行理解。拆解文档直接说明适用条件和预期行为，不要求安装、导入、调用代码或应用案例；可执行调用和断言保留在绑定的测试证据中。
只有所有端口都闭合，且场景能够从明确输入条件说明一个可观察输出或不变量时，
才可以把候选投影为正式 operator；否则应进入修复或缺口流程。

正式算子只使用现有语言 profile：

- Python：`scientific_operator.py` + `test_scientific_operator.py`
- C：`scientific_operator.h` + `scientific_operator.c` + `test_scientific_operator.c`

不得生成 C++、Fortran、MATLAB/Octave、notebook 或混合语言正式产物。源码来自其他语言时，可以忠实改写为 Python 或 C，但必须验证数组布局、索引、精度、单位和边界行为。

## 测试证据头

每个包单独测试后，在测试文件头部记录：

```python
# 测试结果：
# 工作目录：<operator or task-graph package directory>
# 命令：<relative command>
# 环境变量：<none | NAME=meaning>
# 结果：<N passed / failed summary>
# 对照依据：<direct source parity | golden fixture | independent formula | invariant | boundary failure>
# 源码对照状态：<direct_source_runnable | source_unavailable: reason>
# 证据来源：<source-root-relative/path.ext:start-end::symbol>
# 数值差异：<per-output metrics and tolerances>
# 运行环境：<interpreter/compiler and key dependency versions>
```

C profile 使用同字段的块注释。编译成功或可导入不等于数值验证通过。

每个测试函数或测试段前保留一条中文 reviewer 注释：

```python
# 验证：<这个测试证明的行为、边界或 oracle 关系。>
def test_<behavior_name>():
    ...
```

## 审查信号

高质量算子文档应让审核者或任意 Agent 不打开实现文件、不知道来源项目也能回答：计算什么、显式调用合同是什么、物理或数值定义是什么、哪些边界与失败行为被保留、怎样独立调用、怎样判定正确。更长不等于更完整；缺少这些答案时，通用占位文字也不能通过严格单语合同校验。
