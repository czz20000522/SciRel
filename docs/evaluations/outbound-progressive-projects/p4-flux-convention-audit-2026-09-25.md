# P4 真空场到平衡映射的磁通约定审计 (2026-09-25)

状态：开发期出库边界审计，不是科学裁决、实现修复、专家批准或发布说明。本记录只回答：在当前 SciRel 开发基线下，普通出库 Agent 能否把 P4 真空场 `psi_vac` 直接接到平衡/材料支撑链路。结论是：**不能直接接线**，必须先由 SciRel science owner 决定规范磁通约定并同步 exact documents、实现和回归测试。

## 背景

2026-09-24 的 P4 渐进出库模拟中，用户只有线圈几何和电流，希望“先算出等离子体长什么样，再看看加热效果”。求解者最终交付了有边界的真空场预览和下一步材料清单，没有伪造平衡或加热结果；但过程暴露两个真实问题：

1. 首版把每线圈总电流错误施加到每根离散丝，导致场量级高四倍。这个问题已经通过项目修复和测试覆盖。
2. 首版把公共合同里的 `psi_vac: Wb` 擅自重标为 `Wb/rad`，试图接到平衡侧需要的磁通输入。这个问题没有科学裁决，仍是当前出库链路必须阻断的边界。

## 当前合同证据

真空场链路：

- `catalog/examples/scirel.field.circular-filament-green.json`
  - `gpsi` 输出单位标为 `Wb/A`。
  - `gBR` / `gBZ` 输出单位标为 `T/A`。
- `catalog/examples/scirel.field.current-green-superposition.json`
  - `gpsi` 输入单位标为 `Wb/A`。
  - `psi` 输出单位标为 `Wb`。
- `catalog/examples/scirel.field.multi-coil-vacuum-field.json`
  - `psi_vac` 输出单位标为 `Wb`。
  - `b_r_vac` / `b_z_vac` 输出单位标为 `T`。

平衡/网格链路：

- `catalog/examples/scirel.geometry.axisymmetric-equilibrium-grid-mapping.json`
  - `equilibrium.psi_wb_per_rad` 是必需输入字段。
  - `poloidal_flux_wb_per_rad` 输出单位为 `Wb/rad`。
- `src/scirel/field/poloidal_field_from_flux.py`
  - 模块文档写明 “Recover axisymmetric poloidal magnetic field from `psi = R A_phi`”。
  - 函数使用 `B_R = -dpsi/dZ/R`、`B_Z = dpsi/dR/R` 的约定。

因此，当前 public documents 里至少存在一个未裁决差异：真空场输出写成 `Wb`，而平衡映射和材料支撑消费的是 `Wb/rad` / `R A_phi` 约定。只做轴序转置或名称重映射不足以证明二者可接。

## 数值探针

为避免只看文字标签，本轮做了一个只读数值审计。它使用本仓库 `src/` 当前源码（不是开发 wheel），解释器为 `C:/Users/26569/AppData/Local/Python/pythoncore-3.14-64/python.exe`；设置 `PYTHONPATH=src` 后，从 `scirel.field.circular_filament_green` 导入 `circular_filament_green_response`，从 `scirel.field.poloidal_field_from_flux` 导入 `poloidal_field_from_flux`。精确参数与比较步骤如下，`pts` 按 `[R,Z]` 排列：

```python
r = np.linspace(0.2, 0.6, 41)
z = np.linspace(-0.2, 0.2, 41)
R, Z = np.meshgrid(r, z)
pts = np.column_stack((R.ravel(), Z.ravel()))
resp = circular_filament_green_response([[0.8, 0.0, 1.0]], pts)
psi = resp["gpsi"].reshape(R.shape)
br = resp["gBR"].reshape(R.shape)
bz = resp["gBZ"].reshape(R.shape)
from_flux = poloidal_field_from_flux(R, Z, psi)
full = poloidal_field_from_flux(R, Z, 2 * np.pi * psi)
sl = (slice(4, -4), slice(4, -4))
```

比较 `from_flux["B_R"][sl]` / `from_flux["B_Z"][sl]` 与 `br[sl]` / `bz[sl]`；`full` 同理。表中的 `max_rel_diff` 是内部区域最大绝对差除以对应 Green 分量的最大绝对值（`scale`），不是逐点相对误差；避免零场附近误导。
主负责人按这些参数从当前源码独立复跑，得到相同的四个差异值；这仍未替代科学 owner 对公共单位合同的裁决。

输出：

```text
BR max_abs_diff 4.0545823399055186e-10 max_rel_diff 0.0010282357987423869 scale 3.943241759200167e-07
BZ max_abs_diff 7.380486215724753e-10 max_rel_diff 0.0005553080886148687 scale 1.3290795446783874e-06
full_flux_as_input BR max_rel_diff 5.278253998544794
full_flux_as_input BZ max_rel_diff 5.286674410802923
```

解释：

- 直接把 `gpsi` 作为 `psi = R A_phi` 输入时，反推场与 Green 场在内部区域相对差约 `1e-3` / `5e-4`，属于当前有限差分网格上的数值差异量级。
- 若把 full linked flux `Phi = 2π psi` 直接输入同一反推公式，相对差约 `5.28`，接近 `2π - 1` 的错误尺度。

这说明当前实现行为更像返回 `R A_phi` / 每弧度磁通，而不是 full linked flux；但这仍然只是审计证据，不是规范裁决。规范需要同步 public exact documents、实现命名、测试和消费者合同。

## 当前出库规则

在 science owner 明确裁决前，出库 Agent 应遵守：

1. 可以使用 `scirel.field.multi-coil-vacuum-field` 交付真空场预览、线圈配置比较、轴心场量级检查和后续材料清单。
2. 不得把 `psi_vac` 直接喂给 `axisymmetric-equilibrium-grid-mapping` 或材料支撑链路，除非显式提供已裁决的单位转换、轴序转换、平衡语义和所需边界/分类参数。
3. 不得把真空场图称为含等离子体平衡；不得从真空 `psi_vac` 自动推断 separatrix、closed flux side、密度、材料支撑、RF 吸收或加热。
4. 对用户应解释为：“当前能做真空线圈场预览；要继续到平衡和加热，需要经过审核的磁通约定与额外物理输入。”

## Science owner 待裁决项

请决定以下规范问题：

1. `scirel.field.circular-filament-green` 的 `gpsi` 是否规范定义为 `R A_phi` / `Wb/rad/A`，还是 full linked flux `Phi` / `Wb/A`？
2. `current-green-superposition.psi` 与 `multi-coil-vacuum-field.psi_vac` 应随之标为 `Wb/rad` 还是继续标为 `Wb` 并修改实现/消费者转换？
3. 若选择 `Wb/rad`，是否将字段名保留为 `psi_vac`，还是迁移到更明确的 `psi_vac_wb_per_rad`？
4. 哪些 equilibrium graph 的 `psi_vac`、`g_psi`、`psi` 当前测试只验证线性/形状，缺少独立物理归一化回归？

建议裁决后增加一个独立数值/解析回归：对圆电流丝或简单解析磁通，验证 `B_R = -(1/R) dpsi/dZ`、`B_Z = (1/R) dpsi/dR` 与直接 Green 场在受控网格上的一致性，并明确是否需要 `2π` 因子。

## 证据文件快照

| 路径 | SHA-256 |
| --- | --- |
| `catalog/examples/scirel.field.circular-filament-green.json` | `e89cc0daab45bb68841b7202a901689c0fd589e4d0f0af289db56dfbbb5ae319` |
| `catalog/examples/scirel.field.current-green-superposition.json` | `9a1b151a55729589af862fbb74014668a3575d30063b280a228fc772d214579c` |
| `catalog/examples/scirel.field.multi-coil-vacuum-field.json` | `5d1e69a512931b412328c9f5a0fed04bfd29e8ee89c6a175a68630c117f5e65d` |
| `catalog/examples/scirel.geometry.axisymmetric-equilibrium-grid-mapping.json` | `121ddb28f9334c85d5738c4f42ab0029bddca4825bd2a63add671b2e712f9a6e` |
| `src/scirel/field/circular_filament_green.py` | `8ce7e8352364dfb40a60dc5b7aa3824bbcd84e2bdb10c22fd6cdefedc4a0348f` |
| `src/scirel/field/current_green_superposition.py` | `31055d1b47ab0134ec4d9c5f3ae3f2b083d92e391ecbc557ae1e89460096ad4a` |
| `src/scirel/field/multi_coil_vacuum_field.py` | `a82ebf7ac7dcd4a40fd985e5398291b1c54b84f4527a010fd4bbbcbf01f4789a` |
| `src/scirel/field/poloidal_field_from_flux.py` | `e78ab3bac343761e6dc47cfb8e8df8c6131c3fa1350011cbbb4e2b6ec14d32ba` |
| `src/scirel/geometry/axisymmetric_grid_mapping.py` | `7efafc12724b2f7c3c4f52b9328f23d85a6111ab94f0084bef4e616bfbed9992` |
| `tests/graph_contracts/multi_coil_vacuum_field/test_graph_multi_coil_vacuum_field.py` | `a9facaf6a87d5598b3d8de7f5cde7d16172845420a4612ea99b181f33f27ec81` |
| `tests/operator_contracts/test_poloidal_field_from_flux.py` | `c01bcb8459075f70a04fe91c485d4cdaef2e37c6876c7d32bd6036c256135c45` |
