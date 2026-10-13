# SciRel 科学关系手册与 Agent 查询

学习指南按通行学科与问题分章，左侧使用可折叠目录树，不按来源项目组织。首章为“电磁学 → 磁静力学 → 轴对称线圈磁场”，包含单圆环、亥姆霍兹线圈对、矩形截面线圈组和离散加密检查。每节依次说明问题、输入与单位、代码、实际结果和解释。来源仅保留在函数参考的溯源记录中。

函数参考支持科学问题、中文名称与 API 检索，以及领域与资产类型筛选；正式输入输出、适用条件、失败行为与验证限制仍来自唯一 exact document。

## 生成与浏览

在 SciRel 开发 checkout 中运行（仅使用 Python 标准库）：

```sh
python3 scripts/scirel_docs.py build --output .runtime/docs-snapshot-001
python3 scripts/scirel_docs.py serve --snapshot .runtime/docs-snapshot-001 --port 8765
```

打开 <http://127.0.0.1:8765> 阅读章节；`/reference` 查询函数。章节小节与资产详情均可用地址中的锚点收藏。旧的根路径资产锚点会转到函数参考。服务器仅绑定本机回环地址；结束时 Ctrl-C。新内容构建到新目录，工具拒绝覆盖已有快照。默认输入为 `catalog/examples`，也可通过 `--documents` 指定完整依赖闭包的正式文档目录。

页面采用白底黑字、细分隔线和清晰的键盘焦点，不使用彩色装饰。页面是使用手册，不是人审队列。适用范围与限制在调用示例前展示；科学定义、验证证据、来源、任务图和 JSON 合同可继续查看。中文标题来自正式记录，英文科学正文保持原意，不凭名称补写翻译或科学字段。

## Agent 渐进查询

HTML 与 HTTP、CLI 使用同一个查询实现和快照。无需加载所有完整文档，也不导入或执行科学函数。

```sh
# 查询摘要，支持 q、kind、domain、offset、limit
curl 'http://127.0.0.1:8765/api/search?q=field&limit=5'
# 按精确 ID 读取完整正式文档（含依赖 ID）
curl 'http://127.0.0.1:8765/api/asset?id=scirel.field.current-green-superposition'
# 不启动服务也可以查询相同快照
python3 scripts/scirel_docs.py query --snapshot .runtime/docs-snapshot-001 --q field --limit 5
python3 scripts/scirel_docs.py query --snapshot .runtime/docs-snapshot-001 --asset scirel.field.current-green-superposition
```

`GET /api/chapters` 返回章节目录，`GET /api/chapter?id=magnetostatics` 返回与页面相同的完整章节、代码、实际结果及执行绑定；CLI 对应 `query --snapshot … --chapter magnetostatics`。

`GET /api` 返回接口发现说明，`GET /api/manifest` 返回快照身份。查询结果包括 `snapshot_sha256`、`source_commit`、`items`、`total`、`next_offset`；详情返回 `document`。空格分隔关键词采用小写字面 AND 匹配；领域匹配已有 taxonomy 标签，类型为 `operator` 或 `task_graph`。页大小 1–100，默认 20，关键词最长 512 字符。重复/未知参数和非法分页返回 400；不存在的资产或路径返回 404。HTTP 不支持科学调用或写入。可用 `--expected-digest` 固定预期快照身份。

这是实际可用的 HTTP/CLI 查询接口，尚未实现 MCP transport。已有 `scirel_adapter` 是面向同版本 catalog release 的独立薄适配核心；不要把本手册多版本记录集交给它伪装成同一个科学 wheel。后续 MCP 或 CodeFusion 可消费上述只读接口，科学内容及版本边界仍由 SciRel 持有。

## 版本、覆盖与验证边界

构建器复用正式文档 schema、语义和依赖闭包验证，复制完整记录，绑定每个输出文件的字节数和 SHA-256。启动校验全部绑定，读取索引或详情时再核对其原字节。SHA-256 用于绑定，不是签名或人工认可。

`scirel.documentation-snapshot.v1` 是开发文档快照，不是 `scirel.catalog-release.v1`。每条记录保持自身 `implementation_version`，快照记录源码提交与构建时 dirty 状态，不统一改版本号。收录条数不等于 SciRel 全部公共 API 数量，也不等于项目完成数；未有正式文档的资产不会生成占位科学内容。

文档构建不重新验证数值、不执行示例、不证明当前宽 wheel 可发行。已有验证范围、已知限制、历史来源资格和许可状态全部原样展示；原有科学资格不因页面可访问而扩大。人审和公开发行决定仍然独立。

该工具与页面属于开发层，不加入科学 wheel。新增项目达到正式文档冻结条件后，在同一次整合中更新 exact document，重新生成手册，并验证搜索与原文一致；不维护第二份可漂移的科学描述。

## 章节的案例与维护

章节内容位于 `tools/docs/magnetostatics/chapter.json`。`example.py` 是顺序运行的完整示例；页面代码从其小节标记提取，不另抄一份。`results.json` 保存已运行的数值，`plot.py` 使用 Matplotlib 从结果生成黑白 SVG，图表不发明数值。`execution.json` 绑定示例、结果、未改动的科学实现文件与实际安装 wheel。构建器拒绝实现或案例字节变化后继续发布旧结果；应先重新运行并更新证据。

案例采用已安装的精确开发 wheel，在没有源码挂载、没有网络的独立容器中运行；解析式、对称性和线性叠加检查通过。所用五个实现文件的源提交见执行记录。该选择性开发 wheel 仅用于章节验证，不是完整 SciRel 发行。执行环境首次构建遇到系统 Python 没有 pip，改用镜像自带 ensurepip 创建独立 venv 后完成离线构建与安装；未改变科学实现。

今后增章应沿同一学科树扩展，复用正式函数合同。案例需要给出目标问题、模型假设、实际输入输出、结果解释和限制；观察点、电流权重和离散方式必须明确。构建校验不替代案例的真实执行，案例通过也不授予全项目科学资格。
