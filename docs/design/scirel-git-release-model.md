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

文档正文、API 参考、领域导航和发行说明与源码同仓库维护。文档构建读取当前 checkout 的 API 和 exact document，不从历史版本目录复制一份“当前文档”。每个公开能力的合同、失败语义和验证边界仍由 exact document 表达；文档快照的版本身份由 Git commit 和构建 receipt 给出。发行历史只保留短小的 `docs/release/<version>-notes.md`（或等价的索引条目），不复制完整手册或 API 树。

同一 source revision 产生：

1. Python 源码和 `pyproject.toml`；
2. `scirel` wheel；
3. API/领域文档；
4. 当前发行 tuple 与平台矩阵；
5. 可复核的测试和安装回执。

这些记录必须相互引用同一 `source_revision`、版本和能力计数。`release/CURRENT.json` 是当前候选的唯一协调记录；`release/wheel/CURRENT.json` 和 `release/docs/CURRENT.json` 只保留兼容指针，不再承载另一份版本元数据。任何文档变更若超出已安装 wheel 的能力闭包，必须先改变源码/API并重新构建后继候选，不能只改文档记录扩大声明。

## 依赖分层

SciPy 的仓库把核心运行依赖、可选运行依赖和测试/开发依赖分别表达在 `pyproject.toml` 的不同字段中。SciRel 采用相同边界：

- `[project].dependencies` 只放无 extra 即可运行的核心科学闭包；
- `[project.optional-dependencies]` 放用户主动选择的能力，例如 `plot` 和暂定的 `netcdf`；
- `[dependency-groups]`（若后续工具链稳定）放测试、文档、构建和开发环境，不进入 wheel 的 `Requires-Dist`。

`uv.lock` 是该 Git 提交的开发解析锁，不是第二份发行元数据。发布和 clean-venv 验收仍需记录目标平台实际解析到的 wheel 与摘要。

## 当前迁移边界

本轮先执行不改变科学 API 的迁移：

1. 核心依赖收敛为 NumPy、SciPy、mpmath；Matplotlib 和 netCDF4 进入可选/测试闭包；
2. `uv.lock` 与 `pyproject.toml` 同步到 `0.1.0.dev9`；
3. 从安装包验证脚本生成 core、`plot` extra 和测试闭包的独立 receipt；
4. 旧的每版本 release JSON 不属于工作树活动资产；历史身份从 Git 历史和短发行说明恢复，不再扩展平行版本目录；
5. 发行指针收敛为一个当前 Git 绑定的 `release/CURRENT.json` tuple，旧 dev8 记录不改写。

这套模型保留完整历史证据，同时让“当前版本是什么、由哪个提交生成、文档和 wheel 是否同源”都能从 Git 和一个当前 receipt 直接回答。

## 对标依据

本模型参考 SciPy 当前仓库的公开做法：核心运行依赖与 optional runtime 依赖分列，测试/构建/文档使用 dependency groups；版本由 `pyproject.toml` 管理，发布提交、tag 和后继 `.dev0` 提交按 Git 顺序推进；发行说明按版本生成，但正文仍随同一源码仓库维护。

- SciPy `pyproject.toml`: https://github.com/scipy/scipy/blob/main/pyproject.toml
- SciPy Core Developer Guide（Tagging a release）: https://scipy.github.io/devdocs/dev/core-dev/index.html
- SciPy Release Notes: https://scipy.github.io/devdocs/release.html

SciPy 的发布工具仓库还把“要构建哪个源码版本”显式表示为一个 Git ref；构建系统检出该 ref 后生成 wheel/sdist，发布上传前再检查它是否为 tag。SciRel 后续可用同样的 `SOURCE_REF_TO_BUILD` 语义驱动本地或 CI 构建，但不把生成物复制回源码目录；当前由 `release/CURRENT.json` 保存 source revision 和外部 artifact 摘要。
