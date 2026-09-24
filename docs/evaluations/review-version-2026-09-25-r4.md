# SciRel 首次整版待审 successor r4

状态：**开发期冻结待审材料，不是科学认可或公开发行**。上一份 [r3](review-version-2026-09-25-r3.md) 对应 `841fccb` 开发快照，保持原样；它不是可信基线。本说明的确切 Git/tree、wheel、catalog 和测试证据由另存的 review manifest 绑定，不能从文档标题推断已批准。

## 首次审核范围

SciRel 仍没有上一可信版本。当前开发库共 **68 个公共资产（56 个 Operator、12 个 TaskGraph）**。专家首次整版审核不能只看从 r3 到本次的 Git diff；旧 `admitted` 标签和先前待审快照不构成可信认可。`catalog/examples` 有 **23** 份 exact documents，开发 catalog 是 `partial: 23/68`；剩余 **45** 份科学合同尚缺 exact document，因此当前快照不能晋级完整可信版。

相对 r3，本次新增 [fluidBW 动理学关系族](intake-2026-09-25-fluidbw-kinetic.md)：组分平衡尺度、Bessel-Gamma 与有限谐波色散张量/行列式三项普通 Python callable，复用现有解析等离子体色散函数。三份既有 Pleiades 开发资产补了 exact documents，但科学函数未变，不能把补文档解释为新科学批准。没有新增或重绑 TaskGraph；[领域草稿](../domains/kinetic-plasma-waves.md)只组织有依据的关系和待决边界。

第一阶段当前合格交付根暂为空。fluidBW r6 在本轮整合后被独立来源审查否决：保存的 `fDtensor.m` 有九个介电张量分量与 `DD` 终端输出，但 r6 图及 canonical/holdout 收据只闭合了行列式，未证明全部输出重组；确切产物已移至历史待重审目录。PDRF、KN1DPy、ASCOT5、TokaGrad、PDRK、aorsa3d 同样不在合格交付根。本库保留基于这些历史字节的开发关系，但来源主张必须待新合格 L1 或独立证据重新核实。既有科学测试和精确文档的版本机械更新，不等于这些项目重新获得 D1 资格。

## 专家材料与待决

- Review manifest 绑定确切代码树、内部开发 wheel、23 份 exact documents、partial catalog 和实际测试证据。内部 wheel 可运行不等于可信批准；该版本的 `-Mode release` 仍关闭。
- fluidBW 的有限点对照和错误输入失败语义见[关系族记录](intake-2026-09-25-fluidbw-kinetic.md)；专家需审阅其 Maxwellian 模型与张量符号、输入单位、谐波截断适用域、解析 `Z` 替代近似的证据上限，以及 `dielectric_tensor_diagnostic` 是否为保留变体。
- 从点值行列式到实际模态或频率/波数根求解尚有未形成的 TaskGraph；来源还包含 Ronnmark 极点路径，不应把当前三算子视为完整 fluidBW 科学流程。
- 首次审核仍需补齐 45 份 exact documents、现有 12 个 TaskGraph 的领域审阅、所有历史来源资格核对和许可证决定。专家只认可部分内容时，需在开发树剔除或返工后另冻 successor；不得修改本快照或自行标记可信。
