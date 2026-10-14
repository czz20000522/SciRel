# 当前科学包与中文手册

当前累积技术选择为 `0.2.0.dev11+scientific.core`，对应
`provenance/selections/scientific-core-20261014-r5.json` 与
`provenance/selections/scientific-core-documents-20261014-r5.json`。
它用同一安装包提供 234 份精确合同；科学 API 按领域组织，函数和复合任务入口均可从中文 API 目录检索。
正式合同的原实现版本和历史证据保留，不能将它们批量改写成新包版本来制造新科学资格。

## 安装已接收的确切包

根接收记录会给出确切 wheel 的 SHA-256；先核对摘要，再在独立环境安装该文件：

```bash
python -m pip install 'scirel-0.2.0.dev11+scientific.core-py3-none-any.whl'
```

Python 使用 3.14（本次验证 3.14.7）。本选择实际声明 NumPy 2.5.4、SciPy 1.18.1、Matplotlib 3.11.2、netCDF4 1.7.4、mpmath 1.4.1。
这些是本选择实现的运行依赖；无需安装 Git、PowerShell、pytest、原来源 checkout 或 SciRel 开发工具。
`mpmath` 用于运行期高精度有理系数构造，不只是测试参考工具。

磁化色散的随包原语言计算入口还需要 Octave 8.4.0。本次技术证据绑定 Linux ARM64；
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

## 按问题查找入口

- 坐标、网格、线圈和磁场响应：`scirel.geometry`、`scirel.field`、`scirel.electromagnetism`。
- 压力闭合、平衡反馈与场线诊断：`scirel.closures`、`scirel.equilibrium`、`scirel.fieldline`。
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

手册目录入口是 `tools/docs/handbooks/scientific-core-r5.json`，中文阅读层是
`tools/docs/zh/selections/scientific-core-r5.json`。每份阅读层以正式文档 SHA-256 绑定，不从函数名猜补参数或适用域。
构建新快照时，先按 `scientific-core-documents-20261014-r5.json` 的清单复制并逐字核对正式合同，再运行：

```bash
python scripts/scirel_docs.py build --documents /path/to/exact-documents \
  --outline tools/docs/handbooks/scientific-core-r5.json \
  --translations tools/docs/zh/selections/scientific-core-r5.json \
  --output /path/to/new-snapshot
```

旧快照不可覆盖。人类 Sphinx 页面与 Agent 的只读查询使用同一快照；新增资产须同步正式合同、代码签名、安装选择、中文字段和目录，
并在确切 wheel 上验证新增或失效绑定。当前技术接收不代替人工科学认可或公开发行；上游材料、WHAMP 表及部分旧提取的再分发权仍按各 NOTICE 限制。
