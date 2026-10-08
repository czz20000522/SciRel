# 维护与生成

使用指南的长期源在 `docs/user-guide/`；它属于项目文档。静态导出可附在交付包旁或放在网站，
不进入科学 wheel 的运行实现。

## 维护顺序

1. 在现有物理领域和功能页维护问题、物理含义、单位、假设、适用限制与调用路径。新物理功能有稳定主题 ID，
   不以更换某个函数名称来更换物理主题。
2. 对照确切 wheel 的公共声明与已稳定的 canonical 文档更新 `api-snapshot.json`、`binding.json`。
   snapshot 是静态生成的调用及合同投影；签名、默认值、科学端口与验证字段不得手改猜补。
   物理导航的标题/主题映射由维护者审阅后选择。缺少合同的兼容入口保留有限状态。
3. 新例子先由该 exact 安装包实际运行再登记输入与输出；相同实现/依赖可按受影响范围复用已绑定证据。
   调用结构片段与可复现完整例子明确分开，不需要为文字/导航变化重跑无关科学矩阵。
4. 构建网页和 Agent 分片，检查链接、版本、入口数、原容差及公开内容；用浏览器看实际排版与搜索。
5. 新版本使用独立输出目录；保存源码提交、文档摘要和 wheel 摘要。稳定文档随对应开发版本一起接续，
   网站发布与人工科学认可仍按实际流程处理。

## 本版生成命令

生成器使用 Node.js 和 `marked`；它们是文档构建依赖，不是科学运行依赖。
在已有项目文档环境中解析 `marked`，无需为此打包任何运行依赖给用户。

当前兼容实现的声明抽取工具 `scripts/update_user_guide_api.py` 只读取 wheel AST 与 catalog，
不 import 科学库。先更新 version binding 和审阅 `api-topics.json` 的物理标题/归属，再执行：

```bash
python scripts/update_user_guide_api.py --wheel <exact-wheel> --catalog <catalog/release.json>
```

工具核对独立绑定的 wheel/catalog 摘要与记录版本。未指定物理归属的入口拒绝生成；本版工具支持
当前来源的 lazy-export 声明形态，新包装形态需增加静态抽取支持，不能将工具限制当作科学能力缺失。

```bash
node scripts/build_user_guide.mjs build/user-guide
```

如果环境将库装在独立目录，使用 `NODE_PATH` 指向已有 Node 包目录。
该命令读取 Markdown 和只读 API snapshot，生成 `api-reference.md`、独立 `SciRel-使用指南.html`、
`markdown/`、`agent/route.json`、`agent/topics/`、`agent/apis/`、`version.json` 和文件摘要 manifest。
构建不 import 科学库，不计算新的科学结果。

## Agent 与网站消费

Agent 先按 `agent/route.json` 的物理问题定位，读取一个主题，再读取必要的 API 记录。
JSON 记录含机器可读签名及已有合同的投影，主题文件含对应 Markdown；普通文件读取或静态 HTTP GET 即可。
不要求专用向量库、MCP 服务或全量 registry。需要全文检索时，Markdown 可以作为索引输入。

HTML 包含样式与搜索，可本地打开，也可原样托管。CodeFusion 可以链接该静态页或复用相同源生成站内页面；
部署路径、外观或检索适配不改变 SciRel 的物理功能及科学合同。

本版 `api-snapshot.json` 来自已核对的开发 wheel 静态 AST 声明与 7 份已有 canonical 文档。
其中 source docstring、字段类型和符号默认值是兼容参考，不能单独成为新的科学有效性断言。
