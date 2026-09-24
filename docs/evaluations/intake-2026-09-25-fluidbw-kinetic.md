# fluidBW 动理学色散关系族开发整合

状态：开发分支关系比较与验证记录，**不是专家科学批准或公开发行**。本记录使用摘要固定的 fluidBW r6 保存产物。整合时它曾位于合格交付根；随后第一阶段的独立来源审查发现 `bonk/fDtensor.m` 的九个 `Kij` 和 `DD` 终端输出未由 r6 任务图及 canonical/holdout 收据完整覆盖，产物被移至历史待重审目录。因此这里不主张当前 D1 合格；原始源码的完整重组证据仍由第一阶段负责。

## 关系判断

来源身份：fluidBW r6 保存候选树 SHA-256 `e39cf9e7b9ef7ea55765e540100b4634cb2f662dfc82f550cb057fecccd96812`，第一阶段绑定源范围摘要 `d18db1421f503a92574f734209784248e4ae3951fc3d3b8fce543f1838bb3e33`。这些摘要用于历史比较，不是当前合格准入证明。

| L1 关系 | SciRel 判断 | 当前开发结果 |
| --- | --- | --- |
| `species_equilibrium_scales` | 新增平衡态 SI 尺度关系；不同于已有冷张量或解析 `Z` | `derive_species_equilibrium_scales`；保留来源常数和运算顺序，新增 `n00/T00>0` 与有限派生量失败合同 |
| `bessel_gamma_functions` | 新增指数缩放特殊函数关系 | `evaluate_bessel_gamma`；严格整数阶数和有限输出 |
| `kinetic_dispersion_sum_n` | 新增有限温度 Maxwellian 谐波求和点值；与来源 `dielectric_tensor_diagnostic` 部分重叠，暂不合并 | `evaluate_kinetic_dispersion_sum`；复用 SciRel 解析 `Z` 及 Bessel-Gamma；拒绝零 `kx`、非整数 `lmx` 和不可表示结果 |
| `plasma_dispersion_function` | 复用现有解析关系，不复制来源的 Weideman 近似为另一公共默认 | `evaluate_plasma_dispersion`；来源 N=64 与解析实现只在列出的有限点上对照 |

来源 `dielectric_tensor_diagnostic` 的默认 `lmx=15`、复 `kx` 与非有限传播约定不同于当前色散点值合同；在模型、数值域和输出需求进一步厘清前仅记录为有界重叠，不自动归并。已有冷等离子体张量属于不同模型。

## 数值与失败证据

- L1 保存测试和直接来源点值：两个平衡算例逐尺度一致；Bessel-Gamma 的 `n=-3..3`、`b=0..100` 有保存来源对照；谐波色散有一组分和两组分点值，以及 `lmx=15` 九个张量分量。
- SciRel 新增的保存数值回归、张量恒等式和非法输入检查共 56 项；另有 3 项 digest-bound 保存 L1 实现对照通过。该对照直接从固定摘要的历史文件载入，设置 `PYTHONDONTWRITEBYTECODE=1`，不修改来源树。
- 来源算子将 `lmx=1.5` 截断为 1，且 `kx=0` 进入除零；来源尺度代码对 `n00/T00<=0` 无对应防护。SciRel 的严格失败合同是开发标准化决策，不声称与这些错误输入行为相同。
- 解析 `Z` 替代来源 Weideman 近似后，上述有限点上的行列式与保存来源值在 `1e-13` 相对容差内，动态 L1 张量与行列式在 `1e-12` 容差内；这不证明任意波点、谐波截断收敛、根位置或物理模型正确。

三项 exact documents 和领域索引草稿已加入当前开发 catalog。来源资格、输入域、测试与证据上限以 exact documents 和当前待审版本 manifest 为准；首次专家审核应面对完整尚未可信的基线及其反向依赖，而非只看这三个新 callable。
