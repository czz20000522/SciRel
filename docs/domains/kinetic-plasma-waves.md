# 动理学等离子体波领域草稿

状态：**开发期领域索引草稿，待领域专家组织和确认**。本页不批准资产；精确端口、模型和证据范围以链接的 asset document 为准。

## 问题与可用关系

- [组分平衡尺度](../../catalog/examples/scirel.kinetic.species-equilibrium-scales.json)：从 SI 质量、电荷、参考密度/温度和背景磁场得到逐组分热速度、回旋频率、等离子体频率、回旋半径与德拜尺度。输入温度参考值为 eV，输出 `Ts0` 为 K；热速度与回旋半径分别使用 `sqrt(2 kB T/m)` 和 `sqrt(kB T/m)/omega_c`。
- [Bessel-Gamma 函数](../../catalog/examples/scirel.kinetic.bessel-gamma.json)：给定整数谐波阶数与无量纲宗量，计算 `Gamma_n` 和其导数。按保存来源的指数缩放 Bessel 约定，支持广播。
- [解析等离子体色散函数](../../catalog/examples/scirel.kinetic.plasma-dispersion-function.json)：计算已无量纲化的复相位宗量的 `w(z)` 和 `Z(z)`。采用 SciPy 解析 Faddeeva 实现；调用者负责选定频率、热速度及波数归一化。
- [有限谐波动理学色散张量](../../catalog/examples/scirel.kinetic.kinetic-dispersion-sum.json)：对均匀磁化 Maxwell 组分的实频率、x-z 平面非零波矢点求 `K`、`D` 和 `det(D)`，复用上述 Bessel-Gamma 与解析 `Z`。当前是点值计算，不是零点、模态或分支求解。

平衡尺度可为同一算例的多个波点复用。色散张量调用接收已经转换为 K 的 `Ts0` 和 SI 绝对密度 `ns0`，不能把组分尺度函数的原始 eV/相对密度参数直接接线。已有[冷等离子体张量](../../catalog/examples/scirel.dielectric.cold-plasma-tensor.json)属于另一模型，不因都有介电张量输出就与有限温度动理学张量去重。

## 证据与能力边界

保存的 fluidBW 直接来源数值为平衡尺度、Bessel 值、谐波求和的有限点值提供有界对照；SciRel 的独立合同测试还检查失败语义、张量对称性和 Maxwell 旋度项。SciRel `Z` 与来源的 N=64 Weideman 近似只在已列输入上比较，不能宣称所有输入位级相同。fluidBW r6 因源 `fDtensor.m` 的张量终端输出未由任务图/收据全部闭合而撤出合格 L1 根；这里的点值对照是历史开发证据，不恢复第一阶段完成声明。

尚未形成公共 `kinetic_dispersion_relation` TaskGraph：保存来源另有 Ronnmark 极点路径，当前开发库没有证据支持其完整组装或两路切换。谐波截断是否充分、`kx=0`/`kz=0` 极限、复频率根搜索、模态身份、漂移/损失锥或任意分布函数均不属于当前点值合同。专家需决定这些能力的科学身份、适用域与关系族组织；来源许可证和整个开发版本的科学认可也仍待决。
