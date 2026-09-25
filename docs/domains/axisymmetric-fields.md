# 轴对称场与边界关系族草稿

状态：**开发期关系索引，待领域专家组织和确认**。本页只连接已有科学合同；精确端口、失败行为与证据上限以链接的 exact document 为准，不构成认可或发布。

## 能力与区别

- [圆电流丝 Green 响应](../../catalog/examples/scirel.field.circular-filament-green.json)对带无量纲权重的多个圆丝求和，给出目标点的每安培 `psi = R A_phi` 与极向场响应。这里的磁通函数是 `Wb/rad` 约定，不是乘以 `2*pi` 的完整环连磁通。
- [稠密 Green 矩阵](../../catalog/examples/scirel.field.dense-axisymmetric-green.json)保留每个目标/源对的独立响应列，供调用方另行组合。它与上一关系共享理想轴对称圆丝模型，但输出维度与后续电流收缩责任不同，不能因公式相似直接判作可互换。
- [镜像等离子体 Green 矩阵](../../catalog/examples/scirel.field.mirror-plasma-green.json)在源与目标共用的反射对称 R-Z 网格上生成稠密磁通响应，矩阵两轴按 `[Z,R]` 的 C-order 展平。它有固定的网格/对称条件，不提供任意点集的 `BR` 或 `BZ`，也不隐含电流或网格面积因子。
- [网格真空场与径向积分](../../catalog/examples/scirel.field.filament-vacuum-field.json)直接接受每根圆丝的安培电流，在等间距径向网格上叠加场，并从首个径向点对 `R * B_Z` 做梯形积分。其磁通参考边界、网格约束与 Green 点响应不同。
- [矩形线圈电流丝](../../catalog/examples/scirel.field.rectangular-coil-filaments.json)和[固定 16 丝永磁环几何](../../catalog/examples/scirel.field.permanent-ring-filaments.json)只构造不同的源几何；后者返回相对权重，不能当作已指定实际电流的场求解。
- [多线圈真空场图](../../catalog/examples/scirel.field.multi-coil-vacuum-field.json)使用矩形线圈几何、点响应和电流叠加构造场。它不调用永磁环几何或稠密 Green 矩阵；这些能力可供未来经证据审查的组合使用，而非现有图已覆盖的路径。
- [理想导体边界磁通修正](../../catalog/examples/scirel.field.ideal-conductor-boundary.json)在调用方提供的采样与 Green 矩阵上进行截断 SVD 最小二乘校正。实现检查形状，不证明矩阵对应相同几何或 `S @ Gbf = Gbb`；有截断或不相容输入时剩余边界通量可非零。

## 适用条件与待决

这些关系采用柱坐标 R-Z 与 SI 量纲，但权重、实际电流、每安培响应和绝对场不能混接。奇点的拒绝或置零约定因关系而异；同一物理模型不意味着相同数值边界合同。现有直接测试验证有限样本、轴极限、线性叠加、形状和部分失败行为；历史 Pleiades 候选来源尚非当前合格 D1，不能以开发测试替代完整来源闭合或专家认可。

当前圆丝/稠密/镜像 Green、当前叠加、多线圈真空场、磁通导场及已逐项核对的 Picard 反馈端口采用 `psi = R A_phi`；有限差分与离源逐丝回归支持不乘 `2*pi` 的归一化。轴对称自由边界 Picard 的无墙分支已在一个单元电流制造输入上核对返回的 `psi/BR/BZ`；墙修正只改 `psi`，未同步修正 `BR/BZ`，不得据此声称墙分支磁场自洽或直接接入材料支撑链路。其他关系仍须逐项核对，不能从同名 `psi` 推断约定一致。

专家待决：其他 Green 与平衡关系的磁通约定、共同规范身份及保留变体的条件、参考边界约定、奇点的科学处理、永磁环权重到真实磁化/电流的映射、边界矩阵的几何一致性证据，以及来源许可证。无证据时维持分立合同，不在共享实现中擅自统一。
