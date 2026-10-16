# SciRel 科学关系手册与 Agent 查询

手册是持续维护的领域文档入口。学习指南按通行学科与问题分章，左侧使用全书可折叠目录树，不按来源项目组织。已运行的首个完整案例为“电磁学 → 磁静力学 → 轴对称线圈磁场”，包含单圆环、亥姆霍兹线圈对、矩形截面线圈组和离散加密检查。每节依次说明问题、输入与单位、代码、实际结果和解释。来源仅保留在函数参考的溯源记录中。

函数参考支持科学问题、中文名称与 API 检索，以及领域与资产类型筛选；正式输入输出、适用条件、失败行为与验证限制仍来自唯一 exact document。API 参考左侧只列领域，正文按科学问题分组列出可点击的“函数 / 复合入口—用途”表格；进入函数详情后保留同一领域导航。指南继续采用更深的学习目录树。

## 生成与浏览

在 SciRel 开发 checkout 中创建独立文档环境。生成 HTML 使用与 SciPy 相同的 Sphinx + PyData Sphinx Theme；科学模块不被导入，查询与服务只使用 Python 标准库：

```sh
python3 -m venv .runtime/docs-venv
.runtime/docs-venv/bin/python -m pip install -r tools/docs/sphinx/requirements.txt
.runtime/docs-venv/bin/python scripts/scirel_docs.py build --output .runtime/docs-snapshot-001
.runtime/docs-venv/bin/python scripts/scirel_docs.py serve --snapshot .runtime/docs-snapshot-001 --port 8765
```

打开 <http://127.0.0.1:8765>。`/user-guide/index.html` 提供领域指南，`/reference/index.html` 提供 API 参考；具体函数使用 `/reference/generated/<asset-id>.html`，主题使用 `/user-guide/topics/<topic-id>.html`。完整磁场案例为 `/tutorials/magnetostatics.html`。顶部区分指南与参考，左侧为当前部分的领域目录树，右侧为页内导航。旧根路径的资产、章节、主题与案例锚点保留跳转。服务器仅绑定本机回环地址；结束时 Ctrl-C。新内容构建到新目录，工具拒绝覆盖已有快照。默认输入为 `catalog/examples`，也可通过 `--documents` 指定完整依赖闭包的正式文档目录，并用 `--outline` 指定覆盖同一精确文档集合的目录 JSON；该集合还必须有对应的完整中文说明与案例依赖。

页面采用白底黑字、细分隔线和清晰的键盘焦点。函数页沿 SciPy/numpydoc 的顺序展示签名、参数、返回值、失败行为、说明、适用范围、相关函数和示例。正文默认中文；Python 名称、单位符号与原始示例代码不翻译。源码字段或验证结论存在内部冲突时明确标注，不能把翻译当成科学裁决。

## Agent 渐进查询

使用交付包的 Agent 应从 `scirel-solving` 进入。便携查询工具位于
`skills/development/usage/scientific-asset-navigation/scripts/query.py`，只需 Python 标准库，
无需构建工具、源码或科学包导入。交付目录内自动定位 `delivery/docs/manual`；开发 checkout 用
`--snapshot <快照路径>` 显式指定。先 `routes`，再 `routes --chapter <id>`、
`search --topic <id> --limit 5`，最后 `show <asset-id>`。默认返回原合同的完整公共章节（端口、适用范围、失败、示例、验证与图执行规则），
`--view graph` 展开节点/边，`--view full` 返回完整原文及溯源；省略部分明确列出。已知 ID 可直达；
全库 `search --q <词>` 用于跨主题召回，命中不等于科学适用，零命中不证明不存在。
工具只向模型返回当前层，不输出全文搜索字段。读取的索引、目录和单份合同均按快照摘要校验；
它不作全站 HTML 完整性审计。下列开发者 HTTP/CLI 入口继续用于手册维护和浏览。

HTML 与 HTTP、CLI 使用同一个内容快照。网页采用 Sphinx 的分词与全文排序；HTTP/CLI 共用有界字面 AND 查询，两者排序不保证相同。中文网页搜索在构建时依赖 jieba 分词，缺少依赖会拒绝构建。Agent 无需加载所有完整文档，也不导入或执行科学函数。

```sh
# 查询摘要，支持 q、kind、domain、topic、offset、limit
curl 'http://127.0.0.1:8765/api/search?q=field&limit=5'
# 按精确 ID 读取完整正式文档（含依赖 ID）
curl 'http://127.0.0.1:8765/api/asset?id=scirel.field.current-green-superposition'
# 同时取得原合同与摘要绑定的中文阅读说明
curl 'http://127.0.0.1:8765/api/reader?id=scirel.field.current-green-superposition'
# 不启动服务也可以查询相同快照
python3 scripts/scirel_docs.py query --snapshot .runtime/docs-snapshot-001 --q field --limit 5
python3 scripts/scirel_docs.py query --snapshot .runtime/docs-snapshot-001 --asset scirel.field.current-green-superposition
python3 scripts/scirel_docs.py query --snapshot .runtime/docs-snapshot-001 --reader scirel.field.current-green-superposition
```

`GET /api/handbook` 返回完整学科目录与主题资产 ID，`GET /api/topic?id=<id>` 返回单个主题，`GET /api/search?topic=<id>&limit=20` 分页读取该主题下的正式合同摘要；CLI 对应 `query --snapshot … --handbook` 与 `query --snapshot … --topic <id>`。全书搜索同时查主题导读与正式科学合同，结果可继续在函数参考筛选。

`GET /api/chapters` 返回已具备执行绑定的案例目录，`GET /api/chapter?id=magnetostatics` 返回与页面相同的完整章节、代码、实际结果及执行绑定；CLI 对应 `query --snapshot … --chapter magnetostatics`。

`GET /api` 返回接口发现说明，`GET /api/manifest` 返回快照身份。查询结果包括 `snapshot_sha256`、`source_commit`、`items`、`total`、`next_offset`；详情返回 `document`。空格分隔关键词采用小写字面 AND 匹配；领域匹配已有 taxonomy 标签，类型为 `operator` 或 `task_graph`。页大小 1–100，默认 20，关键词最长 512 字符。重复/未知参数和非法分页返回 400；不存在的资产或路径返回 404。HTTP 不支持科学调用或写入。可用 `--expected-digest` 固定预期快照身份。

这是实际可用的 HTTP/CLI 查询接口，尚未实现 MCP transport。已有 `scirel_adapter` 是面向同版本 catalog release 的独立薄适配核心；不要把本手册多版本记录集交给它伪装成同一个科学 wheel。后续 MCP 或 CodeFusion 可消费上述只读接口，科学内容及版本边界仍由 SciRel 持有。

## 版本、覆盖与验证边界

构建器复用正式文档 schema、语义和依赖闭包验证，复制完整记录，绑定每个输出文件的字节数和 SHA-256。启动校验全部绑定，读取索引或详情时再核对其原字节。SHA-256 用于绑定，不是签名或人工认可。

`scirel.documentation-snapshot.v1` 是开发文档快照，不是 `scirel.catalog-release.v1`。每条记录保持自身 `implementation_version`，快照记录源码提交与构建时 dirty 状态，不统一改版本号。收录条数不等于 SciRel 全部公共 API 数量，也不等于项目完成数；未有正式文档的资产不会生成占位科学内容。

文档构建不重新验证数值、不执行示例、不证明当前宽 wheel 可发行。已有验证范围、已知限制、历史来源资格和许可状态全部原样展示；原有科学资格不因页面可访问而扩大。人审和公开发行决定仍然独立。

该工具与页面属于开发层，不加入科学 wheel。新增项目达到正式文档冻结条件后，在同一次整合中更新 exact document、中文阅读说明与目录，重新生成手册，并验证搜索与原文一致。

选定科学发行内容时，可为同一份 exact documents 显式提供完整中文读者集合和目录，例如：

```sh
python3 scripts/scirel_docs.py build --documents <所选正式文档目录> --output <新快照目录> --outline tools/docs/handbooks/scientific-core-r8.json --translations <selected-reader-bundle.json>
```

`--translations` 可重复传入多个 bundle；提供后只读取这些 bundle，仍严格校验完整资产集合、原文摘要、端口顺序及全部条款。省略时继续使用默认 `tools/docs/zh/*.json` 集合。选定内容的中文 bundle 与目录独立保存，不把其他候选记录混入同一选择。文档构建不执行科学计算；安装应用和正式认可仍分别验证。

中文层位于 `tools/docs/zh/*.json`，格式为 `scirel.reader-translation.v1`。每项绑定原始正式 JSON 的 SHA-256，只翻译阅读字段；构建校验精确资产集合、参数名称与顺序、模型假设与适用/验证条目数量，拒绝缺项、重复、摘要失效与约束丢失。结构校验不能替代语义审阅。正式文档变化后必须重新审阅对应中文内容，不能只换摘要。中文层不能改变签名、数值、单位、默认值、实现版本、验证资格或许可。

## 全书目录与持续维护

`tools/docs/handbook.json` 是模型审阅后的学科目录，只写导读与精确资产 ID；公共 API、参数、科学范围、版本、失败行为、证据和许可仍从正式资产文档读取。每条正式文档有且只有一个主主题，多个记录可共用同一 Python 模块；不由路径、来源项目或函数名自动推导学科。构建拒绝缺漏、未知 ID、重复主归属、空主题和没有执行绑定呈现器的案例链接。新增资产必须同步目录，删除或合并资产必须处理旧链接，不能静默丢到“其他”。

全书导读、函数参考、已执行案例是不同层次。主题已有参考文档不表示已有完整教程；尚未编写并运行的案例明确显示待补充。文档覆盖率只以输入的正式记录集合为分母，不表示源码所有公共接口、科学 wheel 闭包或完整项目验收。旧快照保留，稳定更新始终生成新快照。

每次科学资产整合同时执行的步骤与章节编写模板见 [手册编写与维护](handbook-authoring.md)。本手册以现有磁场案例的形式继续扩展；新主题无需改写页面目录，新的案例结果结构须有明确的执行绑定和对应呈现支持。

## 章节的案例与维护

章节内容位于 `tools/docs/magnetostatics/chapter.json`。`example.py` 是顺序运行的完整示例；页面代码从其小节标记提取，不另抄一份。`results.json` 保存已运行的数值，`plot.py` 使用 Matplotlib 从结果生成黑白 SVG，图表不发明数值。`execution.json` 绑定示例、结果、未改动的科学实现文件与实际安装 wheel。构建器拒绝实现或案例字节变化后继续发布旧结果；应先重新运行并更新证据。

案例采用已安装的精确开发 wheel，在没有源码挂载、没有网络的独立容器中运行；解析式、对称性和线性叠加检查通过。所用五个实现文件的源提交见执行记录。该选择性开发 wheel 仅用于章节验证，不是完整 SciRel 发行。执行环境首次构建遇到系统 Python 没有 pip，改用镜像自带 ensurepip 创建独立 venv 后完成离线构建与安装；未改变科学实现。

今后增章应沿同一学科树扩展，复用正式函数合同。案例需要给出目标问题、模型假设、实际输入输出、结果解释和限制；观察点、电流权重和离散方式必须明确。构建校验不替代案例的真实执行，案例通过也不授予全项目科学资格。

## 问题、算子与复合入口

目录按学科和物理问题组织，章节按学习顺序解释模型、调用、结果与限制；函数参考按同一公共 API 提供精确合同。单个 Operator 表达可独立复用的科学关系，TaskGraph 表达多个能力的稳定组合，两者均可用普通 Python callable 调用。不强制“一节一函数”或“一条公式一算子”；教程可以介绍同一资产的多种用法，多个章节可以链接同一资产。来源只进入溯源，不决定章节或包的领域分类。

例如圆环轴上磁场是明确的求解问题，但本章当前代码实际调用单位电流响应与电流叠加两个入口，不能将其描述为已存在的单函数接口。矩形截面线圈组已有 `solve_multi_coil_vacuum_field` 复合入口。新增便利函数须复用已验证实现并完成公共合同与安装验证，不能在文档示例中藏一套新的科学算法。

复合入口必须核对单位、坐标/轴序、归一化、边界、模型假设、误差与状态；各节点正确不自动证明组合正确。迭代使用显式初始状态、更新顺序、停止条件、上限和不收敛结果，不伪装成普通 DAG。公共调用保持简洁，内部依赖与版本、诊断和中间量按需披露；避免为每个参数组合新增公共图。

章节的两条展示公式继续使用原生 MathML。正文中显式以 `$…$` 标记的行内 LaTeX 在构建时经 latex2mathml 转为 MathML，保留原式作为辅助阅读标签；不猜测未标记的普通文本公式，也不支持任意 TeX 文档。转换错误会阻止构建。公式不加载外网服务，Agent 仍取得原合同与中文文本。代码块采用等宽字体，右上角复制按钮复制代码；失败时由 Copybutton 提示手动复制。输出与代码分别显示，教程与函数参考共享主题资源，JSON 合同不因排版被改写。

参考采用：[SciPy 领域教程](https://docs.scipy.org/doc/scipy/tutorial/)与 [API 参考](https://docs.scipy.org/doc/scipy/reference/)。实际使用 Sphinx 8.1.3、PyData Sphinx Theme 0.19.0 和 Sphinx Copybutton 0.5.2；版本见 `tools/docs/sphinx/requirements.txt`。构建器以正式合同和中文阅读层生成 reStructuredText，再用 Sphinx 的 warnings-as-errors 构建 HTML。主题脚本、字体、样式和搜索索引随不可覆写快照保存；阅读不依赖 CDN。`renderer.json` 保存实际构建版本，清单覆盖输出字节。

## 代码阅读与后续交互

当前 Sphinx 页面使用构建时 Pygments 语法高亮与 Sphinx Copybutton。显式标注 Python、Shell、JSON；只为语法使用少量颜色，页面保持白底黑字。旧 Highlight.js 资源继续为历史页面保留，不参与新的 Sphinx 页面渲染。

保留原始空格、缩进与换行，制表符按四列显示；长行可横向滚动，不自动重新排版 Python。右上角提供复制按钮，复制原始代码并去掉交互提示符，不复制标签与高亮标记。高亮不执行示例，也不改变科学合同和已有结果。

后续可以提供类似 Jupyter 的可运行示例，但需另行落实隔离运行环境、精确 SciRel 与依赖版本、单元格顺序与状态、超时/资源上限及实际结果绑定。当前阶段只改进阅读与复制，不展示没有执行能力的“运行”按钮。
