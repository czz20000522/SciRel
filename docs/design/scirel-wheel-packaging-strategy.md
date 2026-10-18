# SciRel wheel 跨平台打包策略

版本和文档的 Git 单一来源规则见 [scirel-git-release-model.md](scirel-git-release-model.md)。历史候选由 Git、短发行说明和相关 provenance 摘要保留；当前候选只由仓库根目录的 `release/CURRENT.json` 协调，不新增平行版本目录。

本文把 SciRel 的产品目标落到可执行的打包和验收边界上。下述完整绑定和平台门禁属于
`release_freeze`/public release；development 只做影响匹配的源码、合同和必要安装 smoke。
SciRel 应像标准科学库一样能够通过
`pip install scirel` 安装并被 Agent 复用；科学正确性由 SciRel 的 Operator 和 TaskGraph 负责，
Agent 只组合已声明合同并编写胶水代码。安装成功、某个平台的函数返回，或一次教程通过，都不能
替代逐能力、逐平台的科学验收。

## Wheel 标签与平台边界

当前纯 Python 构建的 `WHEEL` 元数据应为 `Root-Is-Purelib: true` 和 `Tag: py3-none-any`，
其中只包含 Python 实现和随包声明的运行资源，不包含 `.so`、`.pyd`、`.dll` 或 `.dylib`。
这表示 SciRel 自身没有按操作系统或 CPU 编译的扩展，同一构建产物可以被不同平台的 Python
安装器选择；它不替代传递依赖和外部运行时的逐平台验收。

`py3-none-any` 的含义仅限于 wheel 自身：

- `py3` 表示 wheel 没有声明 CPython 小版本专属的二进制 ABI；它不等于所有 Python 版本都受支持。
- `none` 表示没有 CPython ABI 标签；当前项目仍由 `requires-python = ">=3.14,<3.15"`
  约束到 CPython 3.14 线。
- `any` 表示 wheel 内没有平台专属扩展；它不证明 NumPy、SciPy、Matplotlib、netCDF4、
  Octave 或其他传递依赖在每个系统都有可安装的 wheel，也不证明随包的 native `.m` 能力可运行。

核心依赖、可选依赖和开发依赖分别由 `pyproject.toml` 的对应字段声明。`uv.lock` 是项目开发和
重建解析的锁文件，不是 pip 用户端的跨平台证明；每个平台仍须用实际解析结果和 clean venv 验收。

当前已绑定候选版本只由 `release/CURRENT.json` 的 tuple 确定，候选切出时其值来自确切 Git
提交的 `pyproject.toml`。构建产物、文档和平台回执必须来自同一 Git 提交；文档编辑修订可以
保持相同 wheel 字节，但仅在 `release_freeze` 时从包含该修订的确切提交重新构建并重新绑定。单个
函数修复或性能优化先作为 Git 提交积累，不触发新的外部产物；只有 owner 明确进入
`release_freeze` 后才统一更新版本和闭包。旧候选字节和原回执保持不变，不能覆盖。

实现改进可以在同一 `major.minor` 主线上累计为维护批次，切出时推进 wheel 的 patch 或 dev 版本；
`post` 只用于同一版本的打包/元数据修正。此时 `compatible_wheel` 和 exact document 的
`implementation_version` 必须一起切换到新的 wheel；
只有纯编辑修订才允许复用相同 wheel 字节。

当前 development 的默认安装 smoke 是 **Linux x86_64（amd64）+ CPython 3.14**。Windows、macOS
和其他架构只有在 named consumer 或 `release_freeze` 声明时追加；平台状态必须保留在对应回执中，
不能由 `py3-none-any` 自动扩大为全平台支持。

## 依赖分层

依赖按实际消费者和能力边界分层。版本可来自同一基线，但开发环境、用户运行环境和外部来源
环境不因为版本相同而合并成一个安装清单。

| 层次 | 初始成员 | 进入用户 wheel 的条件 | 验收边界 |
| --- | --- | --- | --- |
| Core Python | NumPy、SciPy、mpmath | 被 universal core 的实现直接或传递调用，并在声明平台有可安装闭包 | 无 checkout、无来源项目、无网络的 clean venv 中完成 import、简单任务、跨域任务和结果检查 |
| Optional Python | Matplotlib | 只由明确的绘图能力使用，并且不阻断 core import | 安装 `plot` extra 后运行绘图 API smoke、科学回归和失败行为；未安装 extra 时 core 仍可导入 |
| Native capability | GNU Octave 及随包 `.m` 资源 | 外部程序版本、平台和调用合同均有独立证明 | 在 capability matrix 声明的 OS/架构/Octave 版本中执行；不计入 universal core 的跨平台结论 |
| Development | pytest、setuptools、wheel、文档工具、Git、PowerShell、独立参考库 | 仅构建、测试、文档、来源对照或发布流程需要 | 只在项目开发环境验收，不写入用户运行闭包；测试/构建包由 `pyproject.toml` 的 `dependency-groups` 管理 |

这张表是目标拆分，改变 `Requires-Dist` 前必须先冻结受影响 API、导入路径、测试分母和失败证据。
历史 wheel 与冻结记录不能通过事后删依赖来取得新资格；依赖精简应生成后继版本并重新构建、
重新绑定文档和平台回执。

### Core Python

NumPy 和 SciPy 是当前大量数值 Operator 的直接运行依赖，mpmath 在有理 Padé 和高精度辅助
计算中被实现调用。它们先作为 core 保留，直到逐项确认某一能力不再需要。Core 的定义是
“不含绘图和外部 native 程序也能完成的已声明科学能力”，不是把当前源树每个模块都自动纳入
通用正确性范围。

### Optional Python

当前源码中没有 `netCDF4` 的 `src/scirel` 导入，搜索结果只在测试中使用它。`get_deltapsi`
消费 NetCDF-like protocol，不要求用户安装 `netCDF4`；该包仅在测试 dependency group 中保留，
不再作为 public wheel extra。运行时导入扫描、公共 API smoke 和涉及 NetCDF 的测试必须继续保持通过。

Matplotlib 出现在绘图模块和 PDRF/PDRK presentation 路径中，部分模块按函数调用时才导入。
`geometry.plotting` 现在只在调用绘图变换时导入 Matplotlib；因此没有 Matplotlib 时，
`import scirel.geometry` 及数值 API 可以继续使用，绘图函数在调用边界给出明确的缺依赖错误。
这解决了核心导入与绘图依赖的边界问题，但还不等于 Matplotlib 已从发行元数据移除。把它放入
`plot` extra 前仍需在 Linux amd64 + CPython 3.14 的 clean venv 中验证绘图 API、失败语义和
所有受影响的公共测试。

### Native capability

fluidBW 当前在运行时明确要求 Linux amd64 和 GNU Octave 7.3.0；PDRK 的 `NativeTransport`
默认执行外部 `octave`，当前记录的 ARM64 验收使用 GNU Octave 8.4.0。pip 安装不会安装这些
系统程序，且 wheel 标签无法表达 Octave 版本。随包 `.m` 文件是运行资源，不是 Python ABI
扩展，也不代表它们在 Windows 或 macOS 可以执行。

因此 native 能力必须在 capability support matrix 中单独记录平台、Python、Octave 版本、资源
摘要、命令、退出状态和结果检查。短期内继续随 wheel 分发资源并在无 Octave 时保持清晰失败，
将其排除在 universal core 兼容性声明之外。长期方案只有两类：把实现迁移到已逐平台证明的
可移植 Python/编译扩展，或拆成带平台标签和独立系统运行时合同的能力包；不能用额外 pip extra
伪装系统 Octave 已被安装。

当前随包资源的精确来源闭包记录在
[`release/wheel/native-resource-closure.json`](../../release/wheel/native-resource-closure.json)。
它把 117 个 `.m`、输入和数据文件按 fluidBW、PDRK current、场景 fixture、legacy、examples、
finite-N 及共享绘图 helper 分组，并把组绑定到 catalog capability。
`scripts/validate_native_resource_closure.py` 同时检查源码资源全集、组间重复、`package-data`
覆盖和可选 wheel 成员；通过这一步只说明资源进入了实际 wheel，不提升外部 Octave 或科学发布
状态。后续拆包应以这些组作为候选边界，先补每组独立的运行时和平台收据，再改变
`pyproject.toml` 的分发边界。

## 构建产物与锁定

在不改变科学源码的阶段，继续构建一个 `py3-none-any` SciRel wheel。构建输入必须绑定确切
Git 提交、包版本、`pyproject.toml`、`uv.lock` 摘要、选定文档和许可证；wheel 记录同时保存
artifact SHA-256、字节数、直接依赖、Python 线和外部 runtime 要求。历史 wheel 的具体身份由
对应 Git 提交、短 release note 和外部构建 manifest 恢复；设计文档不重复复制文件名、摘要或
动态版本字段。

`py3-none-any` 描述的是 wheel 中没有平台专属 Python ABI 扩展，不保证不同操作系统、构建
前端或文件权限环境生成的 ZIP 字节完全相同。`scripts/build_scirel_from_ref.py` 从确切 Git
提交归档构建，并固定 `SOURCE_DATE_EPOCH`、`PYTHONHASHSEED=0` 与 POSIX `umask 022`；解包后
还把普通文件规范化为 `0644`、可执行文件保留为 `0755`、目录规范化为 `0755`，避免 tar
解包器的 umask 把同一份 package data 变成不同的 ZIP external attributes。manifest 同时记录
构建前端、Python 选择器和宿主身份。发行摘要只绑定实际目标平台生成并验收的 wheel，
Windows/macOS 后续各自生成和验收自己的 artifact，不复用 Linux 的摘要或回执。

`uv.lock` 用于开发环境和可复现解析：

1. 修改 `pyproject.toml` 后在同一 checkout 执行 `uv lock`。
2. 必须通过 `uv lock --check`，并核对 `scirel` 版本、Python 约束和直接依赖没有隐式漂移。
3. 对每个目标平台生成实际使用的 wheelhouse 或下载清单；锁文件中的候选 wheel 列表不能替代
   目标平台安装回执。
4. 离线验收使用锁定的 wheelhouse，保留每个文件的 SHA-256、平台 tag、Python tag 和失败原因。
   `scripts/validate_offline_wheelhouse.py` 只消费已经构建的 wheel 和 wheelhouse，使用
   `--no-index --only-binary=:all:` 在临时 clean venv 中完成安装，再调用安装包验收器；它不会
   重建 wheel、修改 `release/CURRENT.json` 或把网络解析结果伪装成离线证据。未提供
   `--source-revision` 的回执只是独立技术证据；带有确切 Git 提交的 PASS 回执才可以在
   后续候选中作为 `platform_receipts` 绑定，并继续接受 `CURRENT` 的 wheel 摘要和版本校验。
   目标平台验收应同时传入 `--lockfile uv.lock`。此模式会解析 wheel 的 PEP 508
   `Requires-Dist`，确认锁文件顶层 `requires-python` 接受目标 CPython 线，逐项与锁文件根包的
   `package.metadata.requires-dist` 对照，再按请求的
   optional extra 遍历锁定的传递闭包；每个 wheel 的规范化名称、版本和 PEP 425 tag 也会与
   目标平台比对。回执中的 `dependency_closure` 若不是 `PASS`，或仍有缺失、版本漂移、重复、
   未知包或不兼容 tag，发行对齐验证会拒绝该平台回执。这样 `pip check` 的运行结果与锁文件
   的静态闭包各自保留，不能互相替代。

如果某平台没有 CPython 3.14 的依赖 wheel，或者只能从源码构建而构建工具链未被声明和验证，
该平台必须保持 `NOT_RUN` 或 `BLOCKED`，不能偷偷使用开发机已有包或把源码构建成功写成 wheel
兼容性通过。

## 每个平台的最小验收包

候选矩阵由 `release_freeze` 针对本次声明的平台生成；它不是 development 的固定门禁。当前默认
开发 smoke 如下，其他平台按需追加：

| 平台 ID | 当前状态 | 立即需要的证据 |
| --- | --- | --- |
| `linux-x86_64-cp314` | `development baseline` | clean venv core 闭包、公共 import、简单和跨域任务；Octave 7.3.0 native 单列 |

Linux aarch64、Windows amd64、macOS arm64 和 macOS x86_64 等平台在候选
manifest 中声明后，按同一顺序建立各自的 clean-venv receipt；没有声明的
平台不产生默认的 `NOT_RUN` 发布门禁。

每个平台的验收顺序如下：

1. 用目标平台的 CPython 3.14 创建不继承系统 site-packages 的 clean venv，记录 `sys.executable`、
   `sys.version`、OS、架构、ABI、pip/uv 版本和环境变量。
2. 从该平台 wheelhouse 安装当前 wheel 及 core 依赖，运行 `pip check`；安装路径必须位于 venv，
   不能来自 checkout、`.pth` 或开发环境。
3. 运行 `import scirel` 和声明的 domain package 公共导入，确认导入路径和版本来自安装包。
   安装包验收器还必须遍历根命名空间、每个 domain 以及 nested public packages（例如 `kinetic.pdrk`）
   的 `__all__`，逐项解析公开导出并记录 `public_surface` 计数；常量和异常类只要求可解析，
   不强制要求 callable。
4. 运行至少一个 simple Operator、一个跨域 TaskGraph 和对应结果级检查；保留输入摘要、命令、
   退出码、输出摘要、检查结果和环境身份。
5. 安装并验证每个 optional extra 的独立路径。没有 extra 时验证 core 不受影响；有 extra 时
   验证额外能力的成功、无效输入和缺依赖失败行为。
6. 若平台声明了 native capability，再检查外部程序确切版本、资源路径、临时目录隔离、超时和
   receipt；未声明或缺程序时保留 `NOT_RUN`/`BLOCKED`，不转成科学数值失败。
7. 重新核对 wheel SHA-256、锁摘要、文档/catalog 绑定和 capability matrix；任一绑定不一致时
   停止该候选的 release closeout。

测试覆盖不完整的平台或能力必须保留完整分母、阈值、原失败和未运行项。`PASS` 只覆盖当前 receipt
明确执行的范围；`PARTIAL`、`NOT_RUN`、`FAIL` 和 `BLOCKED` 不得被摘要成“跨平台支持”。

## 最小实施顺序

跨平台重构按影响最小的顺序推进：

1. 固定当前 Linux amd64 + CPython 3.14 基线，重新生成并校验 wheel、`uv.lock`、文档和平台矩阵，
   确认源码安装路径与 wheel 内容一致。
2. 运行 `scripts/validate_runtime_imports.py` 对 `src/scirel` 做运行时依赖导入审计，验证
   core/optional 声明、动态可选导入和 netCDF4 的测试专用事实；用户 wheel metadata 不声明
   不属于运行闭包的 NetCDF extra。
3. 基于已完成的 geometry 绘图惰性导入，试验 Matplotlib optional 化；保持绘图能力的独立测试和
   缺依赖错误，不让 core import 通过隐式安装 Matplotlib。
4. 为 wheel/release record 增加平台、Python/ABI、锁摘要、直接依赖、外部 runtime 和 capability
   receipt 的绑定字段；所有字段均来自实际验收，不从 wheel tag 推断。
5. 在 Windows amd64、macOS arm64、macOS x86_64 分别建立 clean-venv 和锁定 wheelhouse 验收。
   每完成一个平台，只把对应行从 `NOT_RUN` 改为证据支持的状态。
6. 最后评估 native 能力的可移植实现或独立能力包。只有完成逐平台 scientific parity 后，才把
   相应能力从 native capability 矩阵移入 universal core 声明。

该顺序先保证 Agent 可以可靠复用已验证的 SciRel core，再逐步降低安装负担和平台差异；不会把
未完成的平台或外部运行时能力塞进一个“通用”标签中。
