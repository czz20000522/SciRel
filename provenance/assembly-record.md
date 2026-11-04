---
document_stage: scirel_assembly
assembly_revision: scirel-admitted-52-9013128
---

# SciRel 组装记录

本记录绑定 `0.1.0.dev5` 的完整准入待发行候选。它是入库后的工程证据，不创建、替代或修改
CodeFusion 的 admission、人工决定或公开发布事实。

## 准入输入绑定

- 科学资产身份：本批次的 52 条逐项资产身份由
  `provenance/admitted-assets.json` 的 `integrations` 唯一定义，不以一个批次 ID 冒充单项资产。
- 已准入内容版本：每条记录中的 `admitted_input.version_tree_ref`、`version_tree_root_digest` 与
  `admission.version_commit_ref`；组装基线为 `9013128`。
- 科学合同摘要：每条记录的 `admitted_input.files` 内容摘要和
  `library_source_lf_sha256`，由同一 ledger 保留。
- AI 审核记录、最终人工决定与准入记录：逐项使用 ledger 中的 `case_ref`、`decision_ref` 与
  `admission_ref`；本记录不聚合或新造这些引用。
- 依赖闭包：52 条中有 41 条 operator 和 11 条 TaskGraph；每个 TaskGraph 的
  `dependency_admission_refs` 都指向这 52 条中的精确 admission，缺失或账本外依赖 fail closed。
- support modules：`scirel._composition`（LF SHA-256
  `6367cc40b7f91c0dd5d45f342646151cce5347587737416ab9b84a0ba0d96f77`）和
  `scirel._validation`（LF SHA-256
  `08d251465f9e03ea5e9e26066dd08fa5bbc70ec7deed2b6009dc2719345b94ee`）。二者只满足内部导入闭包，
  不作为资产或公共导出计入 52 条。

## 组装决策

- 候选 SciRel 版本：`0.1.0.dev5`，`integration_baseline_commit=9013128`。
- 处理方式：按每条 ledger 的 `integration_action` 实施 `add_admitted_implementation`、
  `maintain_compatible_library_implementation` 或 `normalize_task_graph_wrapper`；不复制语义资产。
- 决策依据：逐项保留科学身份、准入输入、公共 callable 和精确依赖绑定；维护代码与输入正文不声明
  一律字节相同，而由已记录的合同回放、回归和公共接口验证约束。
- 科学语义变化：本次组装未以工程记录授予或声称新的科学批准。需要改变公式、合同、单位、轴序、
  失败行为或 TaskGraph 实现绑定时，必须生成新的候选并重新审核。

## 实现与 SciRel 接口映射

- 组装源码版本：`integration_baseline_commit=9013128`；逐项 SciRel 源码 LF 摘要由 ledger 绑定。
- SciRel 资产身份、模块与入口：每条为 ledger 中唯一的 `public_callable`；共 52 条，且没有重复模块入口。
- 输入输出映射：public callable 保持其被准入记录绑定的模块、symbol、合同和依赖；TaskGraph wrapper
  只处理已声明的组合接口，不把 support module 暴露为用户 API。
- 依赖版本映射：TaskGraph 的 `dependency_admission_refs` 保留在同一条 ledger 记录中，并只解析到本批次
  已选择的 operator 或 TaskGraph；构建器同时检查 Python 内部导入仅落到选中模块或两个 support modules。

## 内部使用验证

- 接口调用与组装验证：完成记录为 337 项通过，覆盖 ledger 映射、公开接口、TaskGraph、回归、
  admitted-only staging、确定性 wheel 和无源码安装路径。
- 自然语言任务验证：无源码 wheel 的用户验收由本批次验证覆盖；该验证不要求用户了解 SciRel 包名，
  也不替代平台运行时的独立发布验收。
- 资产站文档：不属于本组装流程，由人类专家独立编写。

## 发行验证

- SciRel 版本与内容锁：`0.1.0.dev5` admitted-only staging 生成 `scirel-content-lock.json`；内置 manifest
  digest 为 `sha256:81a66405b369e179d38d1b71926e6101b264268b3cd2b41aab7adf14f4763cb9`。
- wheel 摘要：正式 52 条候选 wheel SHA-256 为
  `9f2b37e34a23f4252b6cae3915a4c2444c1a4a08a32e163e83db24d068d3914f`。
- 干净环境安装/import：在无源码、无网络的环境只安装该 wheel，并验证公共导入和用户验收路径；
  不通过 editable 安装或 `PYTHONPATH` 引入开发树。
- 算子、TaskGraph、兼容与回归验证：纳入上述 337 项通过证据；账本源码摘要和依赖闭包在构建时再次核验。
- 增量隔离演示：52 到 53 条的演示 wheel SHA-256 为
  `cd3487c9c572b188d82dda0e74c0cd0bd48a2fb5f9e0bc0fe2743fa0c5bf7ea3`。该演示只证明增量输入可隔离，
  不改变最终 52 条主候选、其 wheel 摘要或 manifest digest。
- 结论与未验证边界：52 条候选的准入输入、内部依赖和发行工程验证已绑定；它仍不是公开发布，
  也不把测试结果扩张为未声明模型、边界、数值条件或运行环境下的科学结论。
