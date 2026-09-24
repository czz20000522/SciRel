# SciRel 首次整版待审 successor r11

状态：**开发期待审材料，不是科学认可或公开发行**。r10 保持原样；本轮不修改科学 callable 或 TaskGraph 运行代码，只补镜端准中性关系族的 exact documents、领域草稿及返回键回归，并把开发包绑定到 `0.1.0.dev13`。

## 首次审核范围

目前没有上一可信版本。专家首次审核仍覆盖 **68 个公共资产（56 Operator、12 TaskGraph）** 及组合合同，不只是 r10 到 r11 的文档差异。开发 catalog 为 `partial: 57/68`（48 Operator、9 TaskGraph），尚缺 **11** 份 exact documents。原有 53 份文档仅机械更新 `implementation_version`；这不产生新的科学证据，也不把旧的来源审查标签变为本版本批准。

## 本轮材料

- [准中性电势二分](../../catalog/examples/scirel.closures.quasineutral-potential.json)：明确调用方残差回调、有限括根、共同迭代上限、非活跃面行为和失败语义；求根器不证明残差模型或根的物理唯一性。
- [双温镜约束速度矩](../../catalog/examples/scirel.kinetic.mirror-constrained-moments.json)：记录无镜塞解析极限、两端损失锥、有限求积和剖面端口；`psi` 的历史 `Wb` 标签不能直接接到真空场链的 `Wb/rad` 约定。
- [镜端总压强状态](../../catalog/examples/scirel.kinetic.mirror-total-pressure.json)：记录已实现的压强相加及字段透传。历史来源描述要求更强的密度/残差检查，当前 SciRel 函数只校验三个压强输入；此差异待专家判断，不以旧描述扩写现有能力。
- [镜端准中性 TaskGraph](../../catalog/examples/scirel.closures.mirror-quasineutral-closure.json)：绑定五个 exact 依赖，显式标注局部二分反馈、状态、停止条件和迭代上限；21 个文档输出与实际返回键相符，并新增精确返回键回归。
- [领域草稿](../domains/mirror-kinetics-and-quasineutrality.md)汇集问题、可用关系、接线条件、证据与待决项，供专家改组，不代替专家结论。

新增四份文档和领域草稿经独立复核，无剩余科学合同阻塞。文档源码态及 wheel 安装态的 57 份签名/示例验证通过；全套测试 **862 passed、43 skipped**。确切 wheel、catalog 和无源码验证见快照的 `test-evidence.md`。开发版执行成功不等于物理适用性或可信晋级。

本轮未消费新的合格 L1，第一阶段合格 D1 交付根仍为空。保存的 Pleiades 及其他项目材料仅按确切身份作为历史开发对照；合格冻结原料到来后仍需重新比较开发基线、未发布候选、来源和关系族，而非按项目名称直接导入。

## 专家与跨线待决

- 首次 68 资产及反向依赖的模型、单位、边界、适用域和科学证据审查；剩余 11 份 exact documents。
- 镜端 `psi` 的 `Wb` 与真空场 `psi = R A_phi` 的 `Wb/rad` 约定、可能的 `2*pi` 或其他适配；未经核对不能把两条链直接接线。
- 历史总压强描述与现实现差异、两端损失锥模型和求积误差适用域、来源许可证及后续合格 D1 对照。
- 版本级专家认可与可信晋级尚未实现；公开发行和 `scripts/check.ps1 -Mode release` 继续阻断。

专家只认可部分内容时须在隔离开发版剔除或返工，重新验证并冻结 successor，不改写本快照。
