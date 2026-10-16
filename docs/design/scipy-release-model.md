# SciPy 式 Git 发行模型

这份设计记录 SciRel 对 SciPy 仓库与 `scipy-release` 发布仓库的定向借鉴。它约束
版本、源码、文档和 wheel 的所有权，不把 SciPy 的 native 构建系统或平台矩阵直接搬进
SciRel。

## 要解决的重复成本

同一个 `0.1.0.devN` 候选如果同时以 wheel 文件、完整文档树、HTML 快照和多个 JSON
版本目录保存在工作树，就会出现多个相互漂移的真值。维护者需要反复核对字节、版本和
文档选择，消费者也会误把某个旧副本当成当前候选。

SciRel 的目标是让 Git 提交（以及在获得发布资格后创建的 tag）成为版本历史，让一个
确切 ref 生成匹配的 wheel、catalog 和文档快照。生成物只保留在外部构建目录或发行平台，
不作为另一套源码提交。

## SciPy 参考机制

SciPy 主仓库把源码、测试、构建配置和文档放在同一历史中；`doc/source/release.rst`
只汇总各版本的短 release notes，而不保存每个版本的完整 HTML 文档。发布流程在成功
构建 sdist、各平台 wheel 和文档后，再把产物上传到 PyPI、GitHub Releases 和文档站点。
SciPy 还使用一个最小的 `scipy-release` 仓库：发布工作流先 checkout 发布工具，再按
`SOURCE_REF_TO_BUILD` checkout SciPy 的 tag、branch 或 commit，在独立目录构建并输出
到外部 `dist/`。

SciPy 的版本基础仍来自主仓库的 `pyproject.toml`。构建时可生成包含 Git revision 的
运行时版本信息；这类信息是生成元数据，不是第二个手写版本文件。

## SciRel 的采用决定

| 参考机制 | 决定 | SciRel 约束 |
| --- | --- | --- |
| `pyproject.toml` 的 `project.version` | **采用** | 它是包版本唯一基础来源；`src/scirel.__version__` 从源码元数据或已安装 distribution 读取。 |
| 每版本一个短 release-note 源 | **采用** | `docs/release/<version>-notes.md` 只写变更摘要、状态和复核入口，不复制完整手册或 wheel。 |
| 以 ref 构建 sdist/wheel/docs | **采用** | 构建器必须从干净 Git archive 读取源码，并把生成物写到仓库外的新目录。 |
| 最小独立 release tooling 仓库 | **适配** | 当前脚本先留在 SciRel 的 `scripts/` 以便开发；当跨平台发布矩阵稳定后，再拆成只含构建 workflow 的最小发布项目。它不能复制 SciRel 源码或文档。 |
| SciPy 的 native/C/Fortran 构建和 wheel 矩阵 | **拒绝直接移植** | SciRel 当前是纯 Python wheel；平台差异来自依赖闭包和科学回执，不能因为 SciPy 有 manylinux/macOS/Windows matrix 就扩大 SciRel 的支持声明。 |

## 仓库内允许保留的内容

- `pyproject.toml`、`src/`、测试、许可证和一套 canonical handbook/exact documents；
- `docs/release.rst` 等发行总目录，以及每个版本一个短 release note；
- `release/CURRENT.json` 这种当前候选的协调回执。它只绑定 source revision、wheel/docs
  摘要、选择集和平台回执，不定义新的版本；
- 可复核的来源、科学证据和 provenance。它们描述能力与验证边界，不是 wheel/docs 副本。

仓库内禁止提交：

- `*.whl`、完整 HTML 文档、完整 catalog snapshot 或按版本复制的 handbook；
- `release/wheel/versions/*`、`release/docs/versions/*` 等平行版本目录；
- 为了记录候选而复制一整份 `src/`、`docs/` 或 runtime。

用于开发文档服务器的少量 HTML 页面外壳（例如 `tools/docs/index.html`）属于源码模板，
可以继续保留；它们不携带某个版本的完整科学文档内容。版本化的完整 HTML snapshot
仍只能由 ref-bound 构建写入仓库外。

当前 `release/wheel/CURRENT.json` 和 `release/docs/CURRENT.json` 仅是兼容指针；它们不应
增加版本字段或新的候选记录。后续可在不改变 `release/CURRENT.json` 语义的前提下移除旧
消费者依赖，并把当前构建缓存完全迁移到仓库外。

## 版本和文档的实际流程

1. 在 Git 分支中修改源码、exact documents 和 release note；所有公共科学行为变化先有
   失败回归。
2. 提交后以完整 commit（或已审 tag）作为 `source_revision`，从 archive 构建 wheel 和
   文档。构建目录必须是仓库外的空目录，并保存 manifest、字节摘要和构建环境。
3. 在声明平台的 clean venv 中安装该 wheel，运行 `pip check`、公共 API、代表性科学
   回归和文档示例；把回执绑定回同一个 commit。
4. 只更新根 `release/CURRENT.json` 的当前绑定。历史候选由 Git commit/tag 和短 release
   note 恢复；不要把历史 wheel 或文档快照复制回工作树。
5. 只有人工 release approval 完成后才创建正式 tag；开发候选保持可追溯但不冒称公开发行。

这套流程保留 SciRel 的科学边界：版本历史由 Git 管理，科学正确性由包和测试负责，Agent
只组合已经验证的能力。跨平台和 offline wheelhouse 仍需逐平台证据，不能由仓库结构推断。

