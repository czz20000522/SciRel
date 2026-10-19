# SciRel 定位与发行硬合同

SciRel 的版本和文档遵循 Git 单一来源：源码、`pyproject.toml`、exact documents、API 文档和发行说明在同一仓库演进；每个候选的 wheel、渲染文档和回执绑定同一确切提交，历史版本由 Git commit/tag 和外部归档恢复，不复制平行版本目录。文档可在同一 `major.minor` 主线上推进独立编辑修订号，但 exact document 的实现版本仍精确绑定 compatible wheel。

SciRel 按科学标准库维护。它提供可安装、可复用、可发现的 Operator 和
TaskGraph；每项公开能力都绑定 exact contract、实现版本、运行依赖、适用域、失败语义和验证边界。
`pip install scirel` 后，在没有 SciRel 源码、来源项目、审核数据库、宿主服务或网络的环境中，
调用已安装的 core 能力是一级消费路径；SciPy-backed 能力通过 `scirel[scipy]` 进入，绘图能力通过
`scirel[plot]` 进入。宿主预装 wheel 只是减少启动成本的优化，不能成为唯一可用路径。

SciRel 的第二项职责是保证公开能力本身的正确性。进入可发现 release 的能力必须有科学实现、
输入输出和单位合同、适用域与失败回归、独立参考或边界证据、结果级检查以及声明平台的安装运行回执。
测试只覆盖部分输入、平台或物理性质时，release 必须保留证据上限、原失败和 `NOT_RUN`，不能把
函数成功返回、静态文档或某个平台的通过扩大为任意输入和任意平台的正确性。

Agent 是编排者，不是科学内核作者。每次请求遵循：

```text
normalize → discover → exact contract → typed composition
          → execute → result checks → deliver
```

Agent 和胶水代码可以负责需求澄清、能力检索、输入输出组织、字段适配、调用顺序、有限迭代控制、
文件读写和结果交付。科学公式、闭合、离散、科学单位换算、新插值、模型替换和数值修正必须进入
SciRel 能力或经过独立验证的候选；不能藏在某次任务的胶水里。检索未完成、合同不兼容、运行失败和
结果检查失败都不是能力缺失，不能通过重写内核或放宽门禁掩盖。

## 发现与复用

能力发现使用与 wheel、文档和 catalog 同一 release 绑定的快照。候选摘要只负责召回，exact contract
才决定是否可用；查询结果必须保留快照身份、候选 ID、选择理由和未采用近似项。Agent 应优先复用
现有 Operator/TaskGraph，只有在已证明具体能力缺口后才编写新的科学代码。发现接口、Python 公共 API
和宿主适配器必须指向同一安装版本与能力身份，不能各自维护一套科学实现。

## 平台与运行时

“像 SciPy 一样可 pip 安装”是产品目标；每个 release 仍必须逐平台证明。`py3-none-any` 只描述
SciRel 自身 wheel 字节没有本地扩展，不能证明 NumPy、SciPy、netCDF4、Octave 或其他传递依赖在所有
系统可用。release manifest 必须列出 Python/OS/架构/ABI、依赖锁摘要、外部运行时和每项能力回执。

当前开发验收绑定 **Linux amd64 + CPython 3.14**。Windows amd64、macOS arm64 和 macOS x86_64
是目标平台，尚无兼容性结论；未完成 clean-venv 安装、`pip check`、公共 import、代表性简单与跨域
案例、以及平台相关科学 parity 的平台只能标为 `NOT_RUN`。

需要 GNU Octave 或其他外部/native 运行时的能力必须在 capability support matrix 中单独列出，不能
计入 universal core。只有迁移到可移植实现并完成逐平台科学 parity，或明确拆成平台能力包后，才能
扩大 universal core 的声明。

## `release_freeze` / public release 门禁

以下门禁只适用于明确的候选冻结或公开发行。普通 development 使用 affected
checks；named consumer checkpoint 只运行该消费者需要的安装 smoke，不把试点
结果升级成 release 资格。

1. 在每个声明平台的 clean venv 中离线或按锁文件安装，确认实际 import 路径不来自 checkout，运行
   `pip check` 和公共 API smoke。
2. 对每个公开能力保留科学测试、独立参考/边界/失败回归和结果检查；完整能力分母、阈值、原失败和
   未运行项必须可追溯。
3. 对 simple、cross-domain 和需要外部运行时的代表性任务分别保存输入、命令、退出状态、结果摘要、
   检查状态和环境身份；不能用一个案例替代能力分母。
4. wheel、catalog、exact documents、runtime lock 和平台回执必须是同一 release tuple。任一平台或
   能力的状态为 `NOT_RUN`、`PARTIAL`、`FAIL` 或 `BLOCKED` 时，发布说明必须保留该状态。
5. 只有上述证据完整且人工 release approval 明确授予后，才可称为公开发行；开发候选和消费试点不
   自动获得跨平台或完整正确性资格。
