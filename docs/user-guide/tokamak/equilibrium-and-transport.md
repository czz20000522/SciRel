# 平衡几何与输运闭合

## 物理问题

磁几何影响体积积分、安全因子和输运模型的几何参数。热与粒子扩散系数则给约化演化提供闭合。
当前接口保留来源模型，不能将“返回了系数或几何”解释为独立的磁平衡验证或实验输运预测。

## 磁几何的两种来源

`scirel.fusion.geometry.solve_fixed_boundary_equilibrium(state, machine, actuator, sim)` 按配置分派：

| 模型选择 | 实际功能 | 解释限制 |
| --- | --- | --- |
| `reduced_fixed_boundary` | 内部 Miller/moment 约化几何闭合 | 快速模型结果；不能仅凭函数名称声称完成通用 Grad–Shafranov 自洽求解 |
| `geqdsk_prescribed` | 消费输入 G-EQDSK 的几何及 `q/F` 剖面 | 输入给定几何；文件解析不等于重新求解平衡 |

`read_geqdsk(path)` 读取标准 EFIT G-EQDSK/g-file，返回几何标量、一维剖面及二维极向磁通网格的字典。
短数值输入沿来源行为抛出 `ValueError`；部分缺失边界/等值线重建路径依赖 Matplotlib。
最小 `fusion` 依赖不包含全部 G-EQDSK 运行路径，格式和具体返回字段应以本版实现为准。

## 热和粒子输运系数

输入 `rho, Te, Ti, ne20, q, machine, sim` 与所选几何，输出电子、离子热扩散与粒子扩散系数：

```python
from scirel.fusion.transport import chang_hinton_neoclassical_diffusivities
# 需要先准备相同网格上的实际状态和安全因子 q：
chi_e, chi_i, Dn = chang_hinton_neoclassical_diffusivities(
    rho, state.Te, state.Ti, state.ne20, q, machine, sim, eq=eq
)
```

这是调用结构说明，未给定 `q/eq` 的片段不构成可直接执行的验证例子。
温度使用 keV，`ne20` 使用 `1e20 m^-3` 的数值约定，扩散系数单位为 m²/s。

- `chang_hinton_neoclassical_diffusivities`：来源的约化 Chang–Hinton 离子热扩散与简化电子/粒子闭合，具有下限、上限和调节尺度。
- `angioni_neoclassical_diffusivities`：从来源 Angioni–Sauter 矩阵响应提取有效标量系数；其选择器还可能转到其他实现。
  当前接口不返回 Ware pinch 和对流密度 pinch，不能把三个扩散系数当作完整粒子通量关系。

上述两个入口在本版属于兼容参考，尚无独立完整资产合同与通用科学资格。
函数中的裁剪、近轴混合和调节系数是模型选择的一部分，不能掩盖为纯理论公式。

## 神经代理与后备模型

`scirel.fusion.surrogates.fusion_surrogates_effective_diffusivities(...)` 尝试通过外部 QLKNN_7_11 后端取得归一化通量，
然后按来源的梯度除法和比例因子转换为有效扩散系数。
原始代理输出不是直接的 m²/s 扩散系数，这种转换是约化闭合而不是完整通量—梯度反演。

需要实际后端与模型可取得。若 `fusion_surrogates_fail_mode='fallback'`，加载失败可走来源后备模型；
此时返回值不能记为神经模型推理结果。本 wheel 不附受限模型权重，本文的小任务不验证该后端。

相关功能：[径向剖面](radial-profiles.md)、[状态演化](state-and-evolution.md)、[诊断](heating-current-diagnostics.md)。
