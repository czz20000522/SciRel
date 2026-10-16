# SciRel 的 Git 单一来源发行模型

SciRel 采用与 SciPy 同类的单一来源模型：源代码、`pyproject.toml` 中的版本、领域文档和发行说明都在同一个 Git 仓库中演进；Git 提交和 tag 定义版本身份，wheel 与文档是从被构建的提交生成的产物。工作树不为每个候选复制一套源码、文档或 wheel 内容。

## 版本身份

- `pyproject.toml` 的 `project.version` 是当前 checkout 的唯一版本来源。
- 一个候选必须绑定确切 commit；候选 wheel、文档快照和平台回执都引用这个 commit，而不是仅引用分支名或目录名。尚未提交的工作树只能标记为未绑定候选。
- 发布准备完成后，先提交版本和文档变更，再从同一提交构建 wheel、文档和验收材料；技术验收未完成时不能创建发布 tag。构建摘要可以在构建后作为 Git 记录回写，但必须保留被构建的 source revision。
- tag 只指向已经构建并验收的提交。后续开发从 tag 之后的新提交继续，版本号按下一开发序列递进。
- 历史版本通过 Git tag、commit 和外部归档恢复。不要新增 `release/wheel/versions/<version>.json` 或 `release/docs/versions/<version>.json` 作为平行复制品。

`0.1.0.dev8` 的历史身份由 Git 历史和短发行说明保留；工作树已进入 `0.1.0.dev9` 后继候选，后继证据必须绑定新的 commit 和新的 wheel 摘要。

## 文档与源码绑定

文档正文、API 参考、领域导航和发行说明与源码同仓库维护。文档构建读取当前 checkout 的 API 和 exact document，不从历史版本目录复制一份“当前文档”。`tools/docs/handbook.json` 是唯一手册源；当发行选择只覆盖其中一部分资产时，构建器在内存中裁剪导航，不提交第二份按版本命名的 handbook。每个公开能力的合同、失败语义和验证边界仍由 exact document 表达；当前文档选择用 `selection_id`、Git commit 和构建 receipt 标识，不把它伪装成第二个包版本。发行历史只保留短小的 `docs/release/<version>-notes.md`（或等价的索引条目），不复制完整手册或 API 树。

同一 source revision 产生：

1. Python 源码和 `pyproject.toml`；
2. `scirel` wheel；
3. API/领域文档；
4. 当前发行 tuple 与平台矩阵；
5. 可复核的测试和安装回执。

wheel 和文档快照分别由 `scripts/build_scirel_from_ref.py` 与
`scripts/build_scirel_docs_from_ref.py` 从同一个确切 Git ref 归档构建；两者的
生成物和 manifest 位于 checkout 外。文档构建器在归档源码中接收显式
`source_revision`/`source_dirty=false`，不通过当前工作树或不存在的 `.git` 推断来源。

构建 catalog 时必须把这个 source revision 写入 `release.json`；当构建器绑定
source checkout 时，`release_version` 只能来自该 checkout 的 `pyproject.toml`。
synthetic fixture 可以省略 Git 绑定，但不能冒充生产发行 catalog。

这些记录必须相互引用同一 `source_revision`、版本和能力计数。`release/CURRENT.json` 是当前候选的唯一协调记录；`release/wheel/CURRENT.json` 和 `release/docs/CURRENT.json` 只保留兼容指针，不再承载另一份版本元数据。任何文档变更若超出已安装 wheel 的能力闭包，必须先改变源码/API并重新构建后继候选，不能只改文档记录扩大声明。

## 依赖分层

SciPy 的仓库把核心运行依赖、可选运行依赖和测试/开发依赖分别表达在 `pyproject.toml` 的不同字段中。SciRel 采用相同边界：

- `[project].dependencies` 只放无 extra 即可运行的核心科学闭包；
- `[project.optional-dependencies]` 放用户主动选择的能力，例如 `plot` 和暂定的 `netcdf`；
- `[dependency-groups]` 放测试、构建和开发环境，不进入 wheel 的 `Requires-Dist`；当前 `test` 组通过 `build` 组复用构建工具。

`uv.lock` 是该 Git 提交的开发解析锁，不是第二份发行元数据。发布和 clean-venv 验收仍需记录目标平台实际解析到的 wheel 与摘要。

## 当前迁移边界

本轮先执行不改变科学 API 的迁移：

1. 核心依赖收敛为 NumPy、SciPy、mpmath；Matplotlib 和 netCDF4 进入可选/测试闭包；
2. `uv.lock` 与 `pyproject.toml` 同步到 `0.1.0.dev9`；运行 extra 只保留用户主动选择的能力，测试/构建依赖使用 `dependency-groups`；
3. 从安装包验证脚本生成 core、`plot` extra 和测试闭包的独立 receipt；
4. 旧的每版本 release JSON 不属于工作树活动资产；历史身份从 Git 历史和短发行说明恢复，不再扩展平行版本目录；
5. 发行指针收敛为一个当前 Git 绑定的 `release/CURRENT.json` tuple，旧 dev8 记录不改写。

这套模型保留完整历史证据，同时让“当前版本是什么、由哪个提交生成、文档和 wheel 是否同源”都能从 Git 和一个当前 receipt 直接回答。

## 对标依据与采用边界

本模型参考 SciPy 当前仓库的实际布局，而不是复制其编译工具链。SciPy 的
`pyproject.toml` 同时声明当前包版本、核心依赖、optional runtime extras 和
development dependency groups；源码仓库中的 `doc/source/release/` 只保存按版本
命名的短发行说明，完整 API 文档仍由当前源码生成；顶层 `scipy` 命名空间保持很小，
用显式 `__all__` 和惰性子模块导入提供发现入口。SciRel 对应的 Git 内容是：

| SciPy 机制 | SciRel 采用方式 | 有意差异 |
| --- | --- | --- |
| `pyproject.toml` 的单一 `project.version` | `pyproject.toml` 是唯一人工版本源，`release/CURRENT.json` 只做当前候选的派生绑定 | 不把 wheel 文件或完整文档快照提交回源码树 |
| `doc/source/release/<version>-notes.*` | `docs/release/<version>-notes.md` 只保留短摘要，正文/API/合同继续在当前 `docs/` 与 `catalog/` | 不复制整套手册来表示历史版本；Git commit/tag 提供历史恢复 |
| `dependency-groups` 与 optional runtime extras | `[dependency-groups]` 管理 build/test，`[project.optional-dependencies]` 管理用户主动选择的能力 | SciRel 仍按实际 scientific closure 选择依赖，不照搬 SciPy 的编译依赖 |
| 发布工具显式构建某个 Git ref | 构建和验收记录确切 `source_revision`，wheel/rendered docs 作为该提交的生成物 | 当前不引入 SciPy 的 Meson/Cython/native build system |
| 小型顶层 namespace 与惰性 domain imports | `scirel` 根包只暴露版本和领域入口，领域 API 按 `__all__`/惰性 facade 整理 | 现有领域导出仍需按公共 API 审查逐步收敛，不能把未验证名称写进合同 |

因此，`0.1.0.dev8` 和后续 `0.1.0.dev9` 的身份由 Git 提交、tag（若有）和短
发行说明恢复；不会新增 `release/wheel/versions/`、`release/docs/versions/` 或完整
文档副本。`release/CURRENT.json` 可以随着当前候选更新，但它不产生新的版本线，也不
替代 `pyproject.toml`、Git 或当前文档树。

### 文档重新资格化

文档中的 `version.implementation_version` 是运行时兼容性约束，不是第二个版本源。
后继候选不能把旧文档目录复制一份再改版本；使用
`scripts/requalify_document_selection.py` 从旧版本的确切 Git ref 对当前选择逐条核对：

1. 当前文档必须仍由旧 selection 的摘要绑定，且只允许实现版本字段变化；
2. 文档声明的公共模块必须在基线 ref 与当前 checkout 中逐字节一致；
3. 任一合同或公共模块发生变化，都输出阻塞项并停止完整 requalification；
4. 只有完成针对性科学测试且没有任何阻塞项后，才可以用 `--apply` 在同一
   `catalog/examples` 文件上更新版本字段，并生成新的完整 selection/receipt；
   `--allow-partial` 只能用于 dry-run，不能缩小能力分母。旧 selection 和 Git 历史保持不变。

因此，版本迁移产生的是 Git diff、selection receipt 和外部 catalog 构建物，不是第二套
文档树。当前 dev9 候选以 `895bc40` 作为 dev8 源基线时，三个 plotting 合同因
`geometry/plotting.py` 已变化而保持阻塞；它们不能被静默批量改写。

发行验收可用 `scripts/validate_release_alignment.py --expected-source-revision <commit>`
把当前协调记录锁到确切 Git commit。未提供该参数时，工具仍允许审查历史或外部归档中的
候选；正式构建和回写 `release/CURRENT.json` 时必须提供构建 ref，避免旧 wheel 摘要在
新提交上继续通过结构校验。

SciPy 的 release tooling 还把“要构建哪个源码版本”显式表示为 Git ref；SciRel
采用同一事实边界：构建脚本必须从确切提交读取源码和 `pyproject.toml`，再在外部输出
wheel、文档快照和平台回执。生成物不能反向成为另一份源码或文档事实。
