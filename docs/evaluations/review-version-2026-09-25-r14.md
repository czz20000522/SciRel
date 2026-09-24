# SciRel 首次整版待审 successor r14

状态：**开发期待审材料，不是科学认可或公开发行**。r13 冻结快照不改写。本轮只增加一组真实嵌套 TaskGraph 的制造输入回归，并修正相应 exact document 和领域草稿的证据上限；未修改科学 callable、TaskGraph 运行代码或 `0.1.0.dev15` wheel。

## 审核范围与本轮证据

目前没有上一可信版本。专家首次审核仍覆盖 **68 个公共资产（56 Operator、12 TaskGraph）** 及反向依赖，不能把 r13 到 r14 的局部差异当作全部审核范围。开发 catalog 仍为 `complete: 68/68`，仅指当前公共资产的文档覆盖。r14 与 r13 的科学运行代码相同；变化是[动理学镜约化 Hall 图的回归](../../tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py)及其[精确文档](../../catalog/examples/scirel.equilibrium.kinetic-mirror-hall-equilibrium.json)中的验证描述。

制造输入采用 7x7 规则 R-Z 网格、`psi_vac=R^2/2`、同一质子质量/电荷、随 `psi` 线性下降的参考密度、给定双温离子与电子能量、两端 prescribed 电势及对角非零 Green 响应。公开组合函数使用**两个默认真实子图**，并由 Hall 子图在每轮以当前 `B,psi` 调用网格镜端闭合；没有注入假图。默认严格相容性与 firehose 门禁保持开启，仅将外层上限设为 25 次、`tol` 设为 `1e-12`。该案例在 20 次更新后收敛，磁通相对初值有约 `5.74e-8` 的非零变化，非轴线电流非零，最终局部电荷残差小于 `1e-9`，相容性消息为空。安装态从 dev15 wheel 的 `site-packages` 重跑同一测试通过。

这证实指定输入下的嵌套数值执行、反馈和所测门禁，不证明 Green 对真实装置的适用性、跨来源同输入数值复现、任意磁通/单位约定可接线、一般收敛或物理正确性。图的专家领域说明见[各向异性 Picard 平衡](../domains/anisotropic-picard-equilibrium.md)。

## 新发现的有界风险

另一组均匀压强制造输入使用 5x7 网格、`psi_vac=R^2/2`、零 Green 响应、规定端塞电势、`hall_multiplier=0`、关闭局部环向惯性及 firehose 阈值；计算出的绝对力和电场残差约为 `1e-12`，但相对平行动量和广义 Ohm 误差约为 `0.207` 与 `0.090`，超过默认 `0.05` 相容性门槛。两者的分母也接近数值消减尺度，因此默认严格模式拒绝；以 `strict_compatibility=False` 观察到该诊断，而没有改变正式门禁或容差。这只是**接近零力/零电场条件**的一个样本，尚不足以定义通用容差修正；需要专家决定绝对/相对残差的物理尺度和允许域，若改变行为则先补失败回归并保留旧数值断言。

## 验证与未决

`pwsh ./scripts/check.ps1 -Mode affected` 精确选择组合回归与文档检查，**18 passed**；68 份文档源码态签名/示例验证通过。原 dev15 wheel 不变；独立 venv 的 `python -I` 确认从该 wheel 的 `site-packages` 导入，安装态组合回归 **4 passed**。r13 的 **864 passed、43 skipped** 全套及 **52 passed** 安装态证据仍针对同一未改变的运行代码和 wheel，有效范围不扩大到本轮新测试。确切 artifact 摘要和环境限制见冻结快照 `test-evidence.md`。

合格 D1 交付根本轮仍为空，没有消费新合格原料。来源许可证、磁通 `Wb` 与 `Wb/rad` 约定、真实装置/源码同输入对照、首次专家认可、可信晋级和公开发行仍待完成。专家只认可部分资产时应在隔离开发版调整并重新冻结 successor；不得改写 r14 或自行把它标为可信。
