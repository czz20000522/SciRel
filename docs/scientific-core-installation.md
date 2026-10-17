# 当前科学包与中文手册

当前候选的文档选择、匹配 wheel、精确文档清单与手册目录统一由 `release/CURRENT.json` 绑定；`release/docs/CURRENT.json` 仅为旧消费者保留的兼容指针。
科学 API 按领域组织，函数和复合任务入口均可从中文 API 目录检索。
正式合同的原实现版本和历史证据保留，不能将它们批量改写成新包版本来制造新科学资格。

## 安装已接收的确切包

根接收记录会给出确切 wheel 的 SHA-256；先核对摘要，再在独立环境安装该文件：

```bash
python -m pip install <selected-scirel-wheel>
```

Python 及依赖的确切约束以 wheel 元数据和对应安装收据为准；可复用交付应附带运行依赖锁和文件摘要。
这些是本选择实现的运行依赖；无需安装 Git、PowerShell、pytest、原来源 checkout 或 SciRel 开发工具。
`mpmath` 用于运行期高精度有理系数构造，不只是测试参考工具。

## Linux amd64 + CPython 3.14 clean-venv 验收

验收必须从不继承系统 `site-packages` 的虚拟环境开始。将目标 wheel 和已锁定的运行依赖放在同一个
wheelhouse 后，可按下面的命令执行；`--no-index` 确保缺失依赖不会被网络或开发机环境静默补上：

```bash
python3.14 -m venv /tmp/scirel-linux-x86_64-cp314
/tmp/scirel-linux-x86_64-cp314/bin/python -m pip install \
  --disable-pip-version-check --no-index --find-links /path/to/wheelhouse \
  /path/to/wheelhouse/scirel-<project.version>-py3-none-any.whl
/tmp/scirel-linux-x86_64-cp314/bin/python -I scripts/validate_installed_wheel.py \
  --expected-platform linux-x86_64-cp314 \
  --wheel /path/to/wheelhouse/scirel-<project.version>-py3-none-any.whl \
  --output /path/to/receipt.json
```

验收脚本会记录虚拟环境前缀、外部 `site-packages` 路径和每个声明依赖的实际导入位置；若解释器不是
虚拟环境，或依赖从环境前缀之外导入，收据为 `FAIL`。这只是运行闭包和代表性任务的技术回执，不能
单独提升 `release/platform-support-matrix.json` 的状态。

可选能力必须在同一个 clean venv 中单独安装并验收。验证绘图和 NetCDF 能力时，分别执行：

```bash
python -m pip install --no-index --only-binary=:all: --find-links /path/to/wheelhouse 'scirel[plot]'
python -I scripts/validate_installed_wheel.py \
  --expected-platform linux-x86_64-cp314 \
  --wheel /path/to/wheelhouse/scirel-<project.version>-py3-none-any.whl \
  --extra plot \
  --output /path/to/plot-extra-validation.json

python -m pip install --no-index --only-binary=:all: --find-links /path/to/wheelhouse 'scirel[netcdf]'
python -I scripts/validate_installed_wheel.py \
  --expected-platform linux-x86_64-cp314 \
  --wheel /path/to/wheelhouse/scirel-<project.version>-py3-none-any.whl \
  --extra netcdf \
  --output /path/to/netcdf-extra-validation.json
```

离线 wheelhouse 验收器也接受重复的 `--extra` 参数；它会先用同一 wheelhouse 安装每个额外依赖，
再把额外能力交给安装包验证器。缺少对应依赖 wheel、extra 未声明、依赖从环境外导入或能力 smoke
失败时，extra 收据保持 `FAIL`，不会被 core 的通过结果覆盖。
发行验收还应传入与该 wheel 版本绑定的 `--lockfile uv.lock`；验收器会将 wheel 的 PEP 508
依赖、锁文件顶层 `requires-python` 与目标 CPython 线，以及目标平台的传递 wheel 闭包逐项核对。
不能用另一条 Python 线的锁文件替代；若锁文件不接受目标解释器，验收会直接失败。core 与 optional extra
共用的 wheelhouse
可以保留未被当前选择使用的锁定 wheel，收据会记录这些可复用成员而不会把它们误判为闭包失败。

磁化色散的随包原语言入口还需要相应系统运行时：PDRK 的既有安装证据使用 Linux ARM64 的 Octave 8.4.0；
fluidBW 的完整算例、特殊函数、响应、矩阵、搜索、谱和材料入口使用 Linux amd64 的 Octave 7.3.0，固定单线程。
两类入口的运行条件分别核对，不能把一个平台的证据当作另一个平台的通过。
Python wheel 不会替用户安装这个系统运行时，缺少时该类入口按合同报错，不静默替换数值实现。
只调用纯 Python 的磁场、平衡、有限体积、色散函数等入口时无需先安装 Octave。
带可选绘图的入口及其依赖不代表绘图已成为项目核心物理验收要求。
来源对照环境、科学包运行环境和 SciRel 项目开发环境分别选依赖，版本统一不等于三类清单合并。

此前新增的 46 项覆盖中性粒子输运归约、碰撞平均、网格与材料支撑、诊断及采样等有界科学关系。
它们复用逐项独立证据并完成当前安装闭包；不据此宣称任一旧来源项目的全部核心能力已完成。
带符号功率相消、热速度极值和椭圆积分端点采用已证反例的后继修正；原交付仍保留。

新增的 19 个入口补全复误差函数、一般速度分布响应、静电根扫描和线性 Vlasov–Poisson 初值计算；连同已有 4 个入口构成此次完整的动理学功能组。它们只需 NumPy 与 SciPy，不要求 MATLAB、Octave 或来源绘图库。

本次增加 6 个已独立核验入口：表格压力、逐点火蛇裕度、单步 Picard 更新、完整压力反馈、可重建压力状态和固定十六丝磁环几何。完整压力求解复用同一闭合感知迭代，磁镜及火蛇裕度保留危险相消后的有限残量；不新增 Python 运行依赖。

同时纳入经过独立核验的冷等离子体介电张量。最终笛卡尔投影可恢复大分量相消中的小响应，精确共振及不可表示算术仍按合同拒绝；它不包含温等离子体或动力学修正，也不增加 Python 运行依赖。

新增非负三矩守恒的柱坐标分布重映射：默认分支保持密度、轴向动量和速度平方能量，并区分有限网格不可行与数值迭代耗尽。空间插值作用于广延矩；不以负值截断或放松目标制造守恒结果。该数学关系不构成完整中性输运来源项目的资格。

新增各向异性参数推断的诊断采样、单次试探、有界优化与复合反演入口，并修正已有观测残差的固定维数及单位检查。前向收敛、优化停止、拟合质量和可辨识性分别记录；制造模型与有限网格的恢复证据不外推为任意物理闭合或实验装置资格。

新增原子/分子氢碰撞矩阵、局部碰撞矩与频率，以及修正 10 eV 分支的质子—氢弹性截面，以及六个底层经验截面，共十一个公开入口。全部 13 个实际传递实现随包；六个底层拟合已按原始定义完成全部公开分支的独立实现核对；不扩大实验物理有效性。BGK 矩近似、H/D 缩放、有限网格 Maxwell 残差、未定义频率和经验拟合能域均按合同保留。

## 按问题查找入口

- 坐标、网格、线圈和磁场响应：`scirel.geometry`、`scirel.field`、`scirel.electromagnetism`。
- 压力闭合、平衡反馈与场线诊断：`scirel.closures`、`scirel.equilibrium`、`scirel.geometry.fieldline`。
- 守恒输运与源项：`scirel.fvm`、`scirel.source`。
- 碰撞尺度、自举电流、动理学和多流体波：对应领域参考页列出函数和复合入口；不按来源项目分章。

例如，两个独立归一化定义通过显式单位换算可用于同一计算：

```python
from scirel.collisions import normalized_momentum, thermal_electron_momentum

p_thermal = thermal_electron_momentum(temperature_kev=0.25, restmkev=511.0)
c_cm_s = 2.99792458e10
p_grid = normalized_momentum(x=[0.0, 1.0, 2.0],
                             vnorm=p_thermal * c_cm_s, clight=c_cm_s)
print(p_grid)
```

`p_thermal` 是无量纲比值，不能直接当成 `vnorm` 的速度。所得数组对应 `[0, p_thermal, 2*p_thermal]`；
此例验证定义及量纲连接，不证明任意碰撞模型的物理适用性。

## 维护相同的可查询内容

手册目录入口及正式文档选择从当前文档发布记录读取，中文阅读层按同一集合提供。每份阅读层以正式文档 SHA-256 绑定，不从函数名猜补参数或适用域。
构建新快照时，先按所选清单复制并逐字核对正式合同，再运行：

```bash
python scripts/scirel_docs.py build --documents /path/to/exact-documents \
  --outline <selected-handbook.json> \
  --translations <selected-reader-bundle.json> \
  --output /path/to/new-snapshot
```

旧快照不可覆盖。人类 Sphinx 页面与 Agent 的只读查询使用同一快照；新增资产须同步正式合同、代码签名、安装选择、中文字段和目录，
并在确切 wheel 上验证新增或失效绑定。当前技术接收不代替人工科学认可或公开发行；上游材料、WHAMP 表及部分旧提取的再分发权仍按各 NOTICE 限制。
