# 磁化物种平衡尺度开发整合记录

状态：隔离开发候选；不是合格 whole-source D1 接纳、专家批准或公开发行。
本批以主仓 `cf78403` 为基线，逐项对照 intake `647d5db` 的
`scirel.kinetic.species-equilibrium-scales`。公共科学合同在
[exact document](../../catalog/examples/scirel.kinetic.species-equilibrium-scales.json)。
该算子没有直接资产依赖，不重绑 TaskGraph。

## 科学关系与边界

输入是共同物种轴上的质量、电荷、参考密度和温度因子，以及有符号
磁场 `B0`、参考数密度 `n00` 和以 eV 表示的参考温度 `T00`。
输出 SI 热速度、回旋频率、等离子体频率平方、回旋半径、德拜长度
及扫描归一化尺度。热速度使用 `sqrt(2*kB*T/m)`，带符号回旋半径
使用 `sqrt(kB*T/m)/wc`；常数和计算顺序保留来源约定。

这是新的平衡尺度关系，不等同于冷等离子体张量、解析色散函数或
有限谐波张量。后者接受绝对 SI 密度与开尔文温度；本关系的
`ns0` 和 `Ts0` 可供调用方显式传入，但本批不新增组合图，也不
声称自动判断物理模型或谐波截断。

## 来源与验证边界

归档 fluidBW 源文件
`D1待重审历史产物/fluidBW-e39cf9e7/operators/species_equilibrium_scales/scientific_operator.py`
的 SHA-256 是
`17d06f1520d5d703a30d2493ae85086ecd6a271b1d9fe56dc16b58f8dc4b5397`，
与 intake 锁定值一致。只读 `python -B` 回放先断言 `scirel` 从隔离
工作树 `src/` 导入，再对一组电子和电子/氘离子两个保存算例逐项
比较：每个算例的 19 个输出字段与归档源实现精确相等。没有修改
来源树，也没有让维护测试依赖来源 checkout。

intake 的直接测试先在缺少新模块的基线上于收集阶段失败；移入
实现后，在显式 `PYTHONPATH=src` 下 **20 passed**。初次独立回放
的导入路径断言发现环境中另有已安装 `scirel`，因此那次运行没有
产生数值结论；设置隔离源码路径后才执行上述来源对照。

来源实现不拒绝 `n00/T00<=0` 或所有不可表示派生量，SciRel
候选明确收紧这些失败条件；两个正常保存算例的公式和旧断言未改。
fluidBW r6 位于待重审历史归档，来源点值只能支持有界开发比较，
不能恢复项目级 D1 冻结资格。合格 D1 交付根为空；许可证、科学
身份和更大组合的适用性仍待专家审查。

复核发现 README 的 catalog 构建示例和 release 脚本仍分别使用
旧的 `63` 与 `14/62` 覆盖数。本批将当前值统一为 `20/67`，并使
release 环境测试从实际 exact documents 和资产索引计算期望计数。
这只修正开发目录投影，不构成批准 workflow 或发行验收。

## 本批验证

- 直接科学测试：显式隔离源码路径下 **20 passed**。
- 两个保存算例各 19 个字段与摘要锁定的归档实现精确相等。
- 隔离工作树 `pwsh ./scripts/check.ps1 -Mode affected`：选择 7 个
  测试文件，**115 passed**，无全套回退。
- 20 份 dev5 exact documents 的签名与示例通过 runtime 校验。
- 最终 affected、exact document 和差异检查以主仓本批提交结果为准。
