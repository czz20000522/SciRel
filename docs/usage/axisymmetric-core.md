# 轴对称磁场、压力平衡与科学数据

本页介绍 SciRel 的领域入口。这里的磁通是 `ψ=R Aφ`，单位 Wb/rad；完整环绕磁通为 `2πψ`。坐标 R、Z 使用 m，电流使用 A，压力使用 Pa。圆电流丝代表轴对称源，不解析有限导体内部自场；矩阵入口的离散零自点不能解释成真实导线自场。

## 几何与可变电流源

`scirel.geometry` 提供点云、矩形网格、径向/轴向/球坐标弦和旋转。极角从 +Z 向 +R 测量，返回弧度；弦的角度输入使用度。原点没有定义极角。`Mesh.to_points` 按行优先展开结构网格，Green 矩阵、电流向量和结果必须使用同一顺序。

`scirel.electromagnetism` 的 `ArbitraryPoints`、`RectangularCoil` 和 `MagnetRing` 共同使用每源电流乘无量纲权重。`total_current` 是电流乘权重之和；永磁环的正负权重可使这个和为零，但磁场不必为零。磁环入口是一组等效表面电流丝，不独立确定材料磁化强度。

```python
import numpy as np
from scirel.geometry import PointsMesh
from scirel.electromagnetism import ArbitraryPoints, Device

mesh = PointsMesh([.2, .4], [.3, -.2])
device = Device(mesh=mesh)
device.north = ArbitraryPoints([[1., 0.]], current=2., weights=[-1.5])
device.south = ArbitraryPoints([[.8, .1]], current=-3., weights=[.7])
psi = device.psi()
np.testing.assert_allclose(psi, device.current @ device.gpsi())
np.testing.assert_allclose(device.psi(current=-device.current), -psi)
print(psi)
```

该安装例得到 `ψ=[−6.39891932e−8, −2.60200764e−7] Wb/rad`。两个响应行分别对应注册的源集合，电流与有符号权重各乘一次；共同反转电流使磁通反号。

注册顺序决定 `Device` 的电流向量和源集合响应行。替换或删除源、改变网格、直接改变子源坐标/权重后，下一次计算使用当前状态；返回的 Green 数组可由调用者修改而不污染缓存。未配置网格的场计算拒绝执行。

改变矩形线圈的源数时，应构造新对象并明确给定新权重，再设置共同电流或总安匝。已有对象的 `nr`/`nz` 改动不能留下与源数不一致的权重。保持总安匝本身不证明连续线圈的分辨率收敛；间距、截面几何和积分权重都须由实际模型定义。

## Green 响应与组合

`green_response_matrices(targets, sources)` 返回 ψ、BR、BZ 三个矩阵，每个都是**目标行、源列**。两列源坐标默认单位权重；第三列为有符号权重，乘一次。没有 `sources` 时，目标也作为单位源。源顺序和目标顺序均保留。

```python
import numpy as np
from scirel.electromagnetism import green_response_matrices

targets = np.array([[0., .1], [.2, .3], [.4, -.2]])
sources = np.array([[1., 0., -1.5], [.8, .1, .7]])
current_A = np.array([2., -3.])
Gpsi, GBR, GBZ = green_response_matrices(targets, sources)
psi, BR, BZ = (G @ current_A for G in (Gpsi, GBR, GBZ))
assert Gpsi.shape == GBR.shape == GBZ.shape == (3, 2)
assert psi[0] == BR[0] == 0. and BZ[0] != 0.
print(psi, BR, BZ)
```

该例得到 `ψ=[0, −6.39891932e−8, −2.60200764e−7] Wb/rad`，`BR=[0, −2.91057773e−7, 7.18199501e−7] T`，`BZ=[−3.50636675e−6, −3.23681213e−6, −3.36622882e−6] T`。轴上 BZ 非零。这里矩阵轴为目标行/单丝源列，与 `Device.gpsi()` 的源集合行/目标列不同。

轴上 ψ=BR=0，BZ 保留解析轴限。内核使用实际坐标，不把非对称网格反射成另一组坐标。`compute_greens` 是每源集合求和入口，活动丝的精确自点会拒绝；`get_gpsi(R,Z)` 和上述矩阵组合入口声明离散零自点。它们不是同一个奇异点合同。

`scirel.field` 还保留独立变体：逐源集合求和、严格形状的 dense 响应、限定镜像网格的 ψ 矩阵，以及沿径向梯形积分 BZ 的真空场。最后一个入口使用首径向位置为零的积分规范，并拒绝活动源自点；它的 ψ 不可直接替代 `R Aφ` 内核磁通。`solve_multi_coil_vacuum_field` 按明确的矩形线圈记录、权重和独立驱动电流组合已有入口，普通组合保持 DAG。

## 压力平衡与真实终态

`scirel.equilibrium.compute_equilibrium` 使用给定真空磁通和 Green 矩阵迭代压力电流关系 `Jφ=R dP/dψ`。中平面压力从物理半径向外遇到的第一个精确零点界定拟合边界；该范围内 ψ 必须严格增加。下降的存储坐标仅在中平面拟合时排序，矩阵、电流和返回数组保持原顺序。

迭代依次更新压力拟合、导数、电流、Green 收缩、磁通和终态拟合，带明确状态、容差和最大步数。`status == "converged"` 要求磁通更新和终态压力电流闭合都满足容差；`maxiter` 不代表收敛。各向异性反馈的其他入口还分别检查其声明的完整状态、场域、压力导数和稳定性条件，不用很小的松弛更新冒充固定点。

原尺寸安装计算保留了以下结果，门槛均为 `1e-10`，上限 400 步：

|任务|R–Z 网格|终态步数|磁通更新残差|独立电流闭合残差|总等离子体电流|
|---|---:|---:|---:|---:|---:|
|BRB 压力平衡|201×201|9|1.0621×10⁻¹¹|8.6567×10⁻¹⁴|−1316.3663 A|
|WHAM 压力平衡|201×76|7|8.5600×10⁻¹²|1.8826×10⁻¹³|−60579.3094 A|

BRB 使用 HH 每丝 200 A，LTRX 每丝 1 A，保留全部 36 个磁环。原示例的复数属性 `LTRX.currents=100000` 没有改变实际共同电流，不能称为 100 kA 物理验证。需要 100 kA 时必须明确使用每丝共同电流或总安匝这两种不同定义。WHAM 使用 HTS 每丝 160 kA、中央线圈每丝 60 kA；其网格最大 R=.75 m，原 R=1.25 m 查询实际消费最近点 .75 m，不能解释成域外 1.25 m 的边界数据。

BRB 的单个 dense 矩阵占 13,057,926,408 字节，实际进程峰值约 13.88 GiB；矩阵大小不是总资源预算。两个任务串行运行，未缩小网格、改成真空场或制造收敛。

这些结果证明声明的离散压力闭合与安装消费，不独立证明任意 Green、压力函数、实验装置或连续平衡的普遍正确性。

## 数据交换、场线与通量平均

`scirel.io.write_pressure_equilibrium_eqdsk` 只接收已收敛、网格一致且包含精确 Z=0 的压力结果。它将终态 ψ 和总电流写入 Pleiades 扩展方言，并沿明确的 ψ 轴保存压力和 `dP/dψ`；拟合域外两者为零。旧 raw 写入口保留五个零剖面的历史约定。读写不代表 EFIT、COCOS 或 GENRAY 兼容，也不重建 F、q，文件不存二维 Jφ/P。

两个终态文件读回后都真正构造了 401 点场线。按 `ds/B` 加权，常数平均均为 1；非恒定 R² 平均为 BRB 的 0.09761884 m² 和 WHAM 的 0.04811447 m²。独立验证重新计算压力、电流、文本字段、路径权重及平均，不把写出的答案当成计算依据。

`scirel.fieldline` 的 `FieldLine`、`HelperFieldLine`、`FieldLineSet` 和 `Boundary` 提供路径顺序、弧长、采样、曲率、沿线导数、磁通梯度和边界截取。开放路径的邻接不能按闭合环滚动。Helper 的既有入口保留有效 cubic 采样约定，与主入口的可选插值合同不同；有限差分和插值误差需按网格与场光滑性判断，不保证任意域上的固定绝对误差或单调加密改进。

`scirel.electromagnetism.get_deltapsi` 消费真实 netCDF 变量层、命名维度及 A/cm² 电流密度，转换为 SI 后按明确单元面积收缩。该入口按目标 R/Z 极值和 netCDF 的维度长度均匀重建原约定的源网格，不读取独立的任意 netCDF 坐标变量。所需的是格式与单位正确的输入，不是某个历史示例文件；独立生成符合格式的数据已实际计算并通过角积分比较。输入文件属于用户数据，不随科学 wheel 捕获答案。

## 基函数和采样

`scirel.basis` 提供多项式、自然/双端钳制/单端钳制和源限定的第二钳制样条，以及 `BasisMatrix` 组合。边界条件不是可互换的名字；第二钳制的原柱坐标 Robin 关系限定于其零原点值域。先核对 exact document 中的边界、外插和导数选择规则，再用于物理拟合。

`scirel.sampling` 提供矩形最近点、平面最近点、散点与样条插值、极坐标变换、反射、路径采样和通量平均。最近点的平局规则由各入口定义，域外最近点不是域外场解。`scirel.numerics.diff_12_central` 的原始入口要求严格递增坐标。处理下降坐标时同时反转坐标和数据，调用后反转内点导数顺序；导数相对于物理坐标，不额外改变符号。

```python
import numpy as np
from scirel.numerics import diff_12_central

x = np.array([1.7, 1.2, .9, .1, -.4, -.8])
y = 2*x*x - 3*x + 4
d1_ascending, d2_ascending = diff_12_central(x[::-1], y[::-1])
d1, d2 = d1_ascending[::-1], d2_ascending[::-1]
np.testing.assert_allclose(d1, 4*x[1:-1]-3, rtol=2e-12, atol=2e-12)
np.testing.assert_allclose(d2, 4., rtol=2e-12, atol=2e-12)
print(d1, d2)
```

实际返回的一阶内点导数为 `[1.8, .6, −2.6, −4.6]`，二阶导数为 `[4, 4, 4, 4]`，与原下降坐标内点的解析二次函数导数一致。

本页对应开发候选；科学计算证据、来源许可、人工认可和发行是不同事项。后续完整安装应用验收仍属于 D3。
