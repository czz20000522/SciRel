# SciRel reduced-Hall 图磁通合同待审 successor r17

状态：**开发期待审，不是科学认可或公开发行**。r16 原样保留；目前没有上一可信版本，首次专家审核仍覆盖 68 个公共资产。本轮没有新合格 L1，不改科学运行代码或 dev15 wheel。

## 图级增量

[约化 Hall 各向异性 Picard 图](../../catalog/examples/scirel.equilibrium.reduced-hall-anisotropic-picard.json)把 `psi_vac` 和返回的 `psi` 交给同一磁通到场、Green 单步叶算子。叶算子及圆丝/镜像 Green 的已验证约定为 `psi=R A_phi`、`Wb/rad`。本轮据此把图的当前 exact document 和维护的 TaskGraph YAML 中 `psi_vac`/返回 `psi` 标为 `Wb/rad`、`g_psi` 标为 `Wb/rad/A`，要求调用方 `pressure_closure(B,psi)` 按该 `psi` 坐标解释剖面。签名、数值、默认值及物理门禁未改变；冻结历史来源不回写。按完整 `Wb` 理解旧标签的消费者有科学语义兼容影响，不能只换算一个端口。

新增真实图级制造回归：17x17 对称 R-Z 网格、外部圆丝 `psi_vac`、镜像 Green、单个 active plasma cell 和 `hall_multiplier=0`。线性 `psi` 压强律产生非零电流，经一轮 Green 反馈后的目标点通量增量与独立逐丝计算一致，返回 `B_R/B_Z` 与直接圆丝场在 2% 内一致。使用图默认严格相容门禁，不要求一轮收敛。该测试检查无隐含 `2*pi`，但不验证非零 Hall、局部惯性、真实装置或任意压强律。

实际受影响测试、安装态图回归、68 份文档校验、开发 catalog 与冻结摘要记录在本版快照 `test-evidence.md`。此前 r15/r16 的未变叶算子与轴对称图证据可按确切版本复用，不能冒充本轮重新运行。free-boundary、kinetic-mirror 及镜端闭合的旧磁通端口、近零分母相容性、来源许可证、专家认可、可信晋级和公开发行继续待处理。
