# SciRel 的 Git 单一来源发行模型

SciRel 采用与 SciPy 同类的单一来源模型：源代码、`pyproject.toml` 中的版本、领域文档和发行说明都在同一个 Git 仓库中演进；Git 提交和 tag 定义版本身份，wheel 与文档是从被构建的提交生成的产物。工作树不为每个候选复制一套源码、文档或 wheel 内容。

发行按[批次策略](scirel-release-batching.md)执行：小修和性能优化先在 Git 中积累，`release/CURRENT.json` 保持上一个已绑定候选；只有切候选时才一次性推进版本、文档 selection、wheel 和平台回执。

## 版本身份

- `pyproject.toml` 的 `project.version` 是当前 checkout 的唯一版本来源。
- 一个候选必须绑定确切 commit；候选 wheel、文档快照和平台回执都引用这个 commit，而不是仅引用分支名或目录名。尚未提交的工作树只能标记为未绑定候选。
- 发布准备完成后，先提交版本和文档变更，再从同一提交构建 wheel、文档和验收材料；技术验收未完成时不能创建发布 tag。构建摘要可以在构建后作为 Git 记录回写，但必须保留被构建的 source revision。
- tag 只指向已经构建并验收的提交。后续开发从 tag 之后的新提交继续，版本号按下一开发序列递进。
- 历史版本通过 Git tag、commit 和外部归档恢复。不要新增 `release/wheel/versions/<version>.json` 或 `release/docs/versions/<version>.json` 作为平行复制品。

历史候选的身份由 Git 历史和短发行说明保留。开发期可以连续提交多个实现修复而不切新的
候选；切批次时再推进一个维护版本（通常为 PEP 440 `patch` 或 `dev`；`post` 只用于打包/元数据修正），
并为该批次绑定新的 commit 和 artifact 路径。版本推进由批次切出触发，不由单次提交触发；不能覆盖
已经生成的 wheel、文档快照或回执。

### Wheel 与文档的主线和修订号

Wheel 和文档需要保持同一条公开发行主线，但不要求每次文字修订都重建相同的
wheel。主线取公共版本的 `major.minor` 对（例如 `0.1`）；wheel 的完整
PEP 440 版本仍由 `pyproject.toml` 唯一决定，文档则可以在该主线上拥有独立的
编辑修订号。

这条规则同时适用于实现演进：wheel 可以在同一 `major.minor` 主线上推进维护批次版本。
每次维护批次切出才生成新的候选；该候选的
`compatible_wheel` 与每条 exact document 的 `version.implementation_version`
必须精确跟随新的 wheel 版本。文档编辑修订号可以在同一主线上独立推进，但不能
替代这个运行时实现版本。

这里有两个必须分开的字段：

- exact document 的 `version.implementation_version` 是运行时兼容性字段，必须
  精确等于它所描述的 compatible wheel 版本。它不随错别字、导航、翻译或示例
  排版修订而改变。
- `release/CURRENT.json` 中的 `documentation.version` 是文档发行修订身份，记录
  文案/导航/翻译的递进；它必须声明同一 `major.minor` 主线、exact
  `compatible_wheel`、source revision、selection digest 和 snapshot digest。

因此，文档只纠正文案时可以在 `0.1` 主线上推进文档修订而保持 wheel 的 exact
版本和结果字节不变；仍须从包含文档修订的新 Git 提交重新构建/重新绑定候选，
以便 wheel 与文档 receipt 继续拥有同一 source revision。文档的实现版本仍然写
wheel 的 exact 版本。若文档变化触及科学定义、公开
API、默认值、失败语义、适用域、依赖或 TaskGraph 组合，则它已经改变实现合同，
必须构建新的 wheel 候选，并从同一 source revision 生成新的文档 selection；不能
用文档修订号掩盖能力或实现漂移。

当前开发候选仍采用最简单的单一 exact 版本：wheel、selection 和所有
`implementation_version` 都来自同一个 `project.version`。引入独立文档修订号前，
不能把 `project_version` 或 `implementation_version` 改成一个仅用于文案的版本值。

当前契约不允许文档偷偷使用独立的 source ref：即使只是编辑修订，也要把修改提交
到新的 Git commit，并从这个 commit 重新构建/重新绑定 wheel 与文档。这样
`release/CURRENT.json` 仍可用一个 `source_revision` 绑定完整候选；wheel 字节和
实现版本可以保持不变，但它们的构建身份已经明确地指向包含该文档修订的新 commit。

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

这些记录必须相互引用同一 `source_revision`、compatible wheel、主线和能力计数。
`release/CURRENT.json` 是当前候选的唯一协调记录；`release/wheel/CURRENT.json` 和
`release/docs/CURRENT.json` 只保留兼容指针，不再承载另一份版本元数据。当前文档
选择中的每条 exact document 必须使用 `pyproject.toml` 的同一 `project.version`；
`documentation.version` 若另有编辑修订，也只能作为文档记录字段，不能成为运行时版本或替代
`implementation_version`。不再在当前 tuple 中保存 `asset_implementation_baselines`
或其他多版本列表。历史版本从 Git 提交、tag 和短发行说明恢复。任何文档变更若
超出已安装 wheel 的能力闭包，必须先改变源码/API并重新构建后继候选，不能只改文档
记录扩大声明。

## 依赖分层

SciPy 的仓库把核心运行依赖、可选运行依赖和测试/开发依赖分别表达在 `pyproject.toml` 的不同字段中。SciRel 采用相同边界：

- `[project].dependencies` 只放无 extra 即可运行的核心科学闭包；
- `[project.optional-dependencies]` 放用户主动选择的能力，例如 `plot`；NetCDF4 仅保留在测试依赖组，不进入用户 wheel extra；
- `[dependency-groups]` 放测试、构建和开发环境，不进入 wheel 的 `Requires-Dist`；当前 `test` 组通过 `build` 组复用构建工具。

`uv.lock` 是该 Git 提交的开发解析锁，不是第二份发行元数据。发布和 clean-venv 验收仍需记录目标平台实际解析到的 wheel 与摘要。

## 当前迁移边界

当前迁移边界按候选逐步推进：

1. 核心依赖收敛为 NumPy、SciPy、mpmath；Matplotlib 保留为 `plot` extra，netCDF4 仅在测试闭包中保留；
2. 每次修改依赖时，在同一 Git 提交中同步 `uv.lock` 与 `pyproject.toml`；用户 extra 只保留实际运行能力，测试/构建依赖使用 `dependency-groups`；
3. 从安装包验证脚本生成 core、`plot` extra 和测试闭包的独立 receipt；
4. 旧的每版本 release JSON 不属于工作树活动资产；历史身份从 Git 历史和短发行说明恢复，不再扩展平行版本目录，也不在当前 tuple 中保留多版本基线列表；
5. 发行指针收敛为一个当前 Git 绑定的 `release/CURRENT.json` tuple，历史记录不改写。

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
| 源码仓库中的构建与 wheel 配置（`pyproject.toml`、`tools/building/`、`tools/wheels/`、CI workflow） | SciRel 也把构建入口和边界保留在源码仓库；`scripts/build_scirel_from_ref.py` 与 `scripts/build_scirel_docs_from_ref.py` 先归档确切 Git ref，再把生成物写到仓库外 | SciRel 当前是纯 Python wheel，不复制 SciPy 的 Meson/Cython/native 构建链 |
| 小型顶层 namespace 与惰性 domain imports | `scirel` 根包只暴露版本和领域入口，领域 API 按 `__all__`/惰性 facade 整理 | 现有领域导出仍需按公共 API 审查逐步收敛，不能把未验证名称写进合同 |

因此，每个候选的身份由其 Git 提交、tag（若有）和短发行说明恢复；不会新增
`release/wheel/versions/`、`release/docs/versions/` 或完整文档副本。`release/CURRENT.json`
可以随着当前候选更新，但它不产生新的版本线，也不替代 `pyproject.toml`、Git 或当前文档树。

SciPy 当前仓库把构建边界分布在 `pyproject.toml`、`tools/building/`、
`tools/wheels/` 和 `.github/workflows/wheels.yml`；wheel workflow 通过 checkout 当前
提交并在平台矩阵中运行 `cibuildwheel`，同时以 `scipy-release` 仓库作为流程对齐参考。
SciPy 的 `tools/building/gitversion.py` 在构建时从 `pyproject.toml` 读取版本，并为开发
版本生成带 Git revision 的安装时版本模块；源码树不保存一份按版本复制的 `version.py`。

SciRel 采用其中的单一版本源、短 release notes 和源码仓库内构建配置，但针对当前纯 Python
wheel 增加了更严格的 ref-bound 适配：`scripts/build_scirel_from_ref.py` 与
`scripts/build_scirel_docs_from_ref.py` 先归档确切 Git ref，再把 wheel、文档快照和 manifest
写到仓库外。这样既保留 SciPy 式的源码结构，也能让每份外部产物回溯到唯一提交，而不会把
源码、handbook 或历史 wheel 复制回工作树。若以后引入 `.so`、`.pyd` 或其他平台二进制扩展，
再单独评估是否需要 `cibuildwheel`/release automation；不能因为参考项目使用这些工具就提前
把它们加入 SciRel 的运行依赖。

SciPy 的版本工具还把 Git revision 暴露给安装后的运行时，便于把开发版本追溯到提交。SciRel
当前先把 revision 固定在 wheel、文档和平台 receipt 的外部 manifest 中；在不改变公共科学
API 的后续版本中，可以增加只读的 `scirel.version.git_revision`，但它必须由 ref-bound
构建生成，不能在运行时依赖用户 checkout 或网络查询。

### 发布编排层的采用边界

SciPy 把科学源码和发布编排分成两个 Git 仓库。主仓库保存源码、`pyproject.toml`、构建配置、
完整文档和短发行说明；最小化的 `scipy-release` 仓库只保存 wheel/sdist 的 CI、锁文件和发布
安全边界。发布 workflow 用 `SOURCE_REF_TO_BUILD` 明确指定要构建的 SciPy 分支、tag 或 commit，
再把该 ref checkout 到独立目录；发布仓库不复制 SciPy 源码或文档。这个边界同时解决了两个
问题：源码历史仍由主仓库和 tag 管理，发布权限和干净构建又不会被业务源码树中的临时产物
污染。

SciRel 采用这套边界时分两步进行：

1. 当前阶段继续把 ref-bound 构建脚本和一个 `release/CURRENT.json` 候选回执放在 SciRel 主仓库，
   因为项目仍是纯 Python wheel，且需要在同一提交中审查源码、合同、文档选择和平台回执。这个
   回执只有一个当前 tuple，不承载历史版本列表；`release/wheel/CURRENT.json` 和
   `release/docs/CURRENT.json` 只是已标记弃用的兼容指针，不能写入版本或 artifact 身份。
2. 当需要多平台自动构建、签名或上传时，新增一个与主仓库同级的最小发布工作区（例如
   `SciReL-release`），只保存构建 workflow、构建依赖锁和 `SCIREL_SOURCE_REF_TO_BUILD`。
   它从 SciRel 的 tag/commit checkout 源码，调用主仓库随 ref 提供的构建入口，把 wheel、完整
   文档和平台 receipt 写到仓库外；不得把源码、手册、历史 wheel 或按版本的完整 manifest 复制
   回 SciRel 主仓库。

这意味着历史开发 wheel 的身份来自 Git commit/tag、对应的短 release notes 和外部 artifact
manifest。开发候选可以继续使用同一个 `pyproject.toml` 开发版本，但必须绑定新的 source ref，
并将产物写入以版本和 commit 共同命名的外部目录；不能覆盖旧 wheel，也不能通过复制一份旧文档树
来表示历史。

### 文档重新资格化

文档中的 `version.implementation_version` 是运行时兼容性约束，不是第二个版本源。
后继候选不能把旧文档目录复制一份再改版本；使用
`scripts/requalify_document_selection.py` 从旧版本的确切 Git ref 对候选版本的确切
source ref 逐条核对。`--source-ref`（也接受 `--target-ref` 作为 CLI 别名）默认是
`HEAD`，正式历史重资格化必须显式绑定候选提交，避免后续开发提交改变历史分母：

1. 候选 ref 的文档必须仍由旧 selection 的摘要绑定，且只允许实现版本字段变化；
2. 文档声明的公共模块必须在基线 ref 与候选 source ref 中逐字节一致；
3. 任一合同或公共模块发生变化，都输出阻塞项并停止完整 requalification；
4. 只有完成针对性科学测试且没有任何阻塞项后，才可以用 `--apply` 在同一
   `catalog/examples` 文件上更新版本字段，并生成新的完整 selection/receipt；
   `--allow-partial` 只能用于 dry-run，不能缩小能力分母。旧 selection 和 Git 历史保持不变。

因此，版本迁移产生的是 Git diff、selection receipt 和外部 catalog 构建物，不是第二套
文档树。若基线与当前源码的公共合同发生变化，requalification 必须保留阻塞项并等待
针对性修正；不能静默批量改写旧文档。

发行验收可用 `scripts/validate_release_alignment.py --expected-source-revision <commit>`
把当前协调记录锁到确切 Git commit。未提供该参数时，工具仍允许审查历史或外部归档中的
候选；正式构建和回写 `release/CURRENT.json` 时必须提供构建 ref，避免旧 wheel 摘要在
新提交上继续通过结构校验。正式平台门禁还应增加
`--require-bound-candidate-match`：`byte_identical=true` 只证明两次重建彼此一致，
`matches_bound_candidate=true` 才证明重建结果就是当前绑定 wheel；验证器会从回执摘要重新
计算这两个关系。

SciPy 的构建和版本工具都从当前 checkout 的 Git 内容产生发行信息；SciRel
采用同一事实边界，并额外要求构建脚本显式接收确切 Git ref，从该提交读取源码和
`pyproject.toml`，再在外部输出 wheel、文档快照和平台回执。生成物不能反向成为另一份
源码或文档事实。
