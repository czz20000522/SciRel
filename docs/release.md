# SciRel 发行说明

发行说明只记录 Git 提交/tag 对应的短变更摘要。源码、API 参考、科学手册和 exact documents 继续维护在当前 `docs/` 树中；这里不复制整套文档，也不保存 wheel 文件。

## Wheel 与文档版本线

发行按[发行批次策略](design/scirel-release-batching.md)执行。单个函数修复、性能优化或边界
失败修正先进入 Git 累积；维护者切出批次时才一次性推进 wheel、exact documents、selection
和平台回执。`release/CURRENT.json` 始终指向上一个已绑定候选，直到下一批次完成验收。

Wheel 和文档必须属于同一公开 `major.minor` 主线，但不要求两个完整的 PEP 440
版本字符串相等。wheel 的完整版本来自 `pyproject.toml`；文档可以在同一主线上推进自己的编辑修订，
`compatible_wheel` 和每条 exact document 的 `implementation_version` 仍精确指向兼容的
wheel。只纠正文案、导航、翻译或示例排版时，可以在同一主线上推进独立的
`documentation.version` 并保持
相同 wheel 版本和结果字节；仍须从新的 Git 提交重新构建/重新绑定候选，文档 receipt 仍须
绑定 exact compatible wheel、source revision、selection 和 snapshot 摘要。

wheel 自身也可以在同一 `major.minor` 主线上推进 patch、post 或 dev 修订。累计的实现改动
达到批次边界时，才生成新的 wheel 候选和文档 selection；`compatible_wheel` 及每条 exact
document 的 `implementation_version` 在该批次中精确跟随新的 wheel。文档编辑修订号可以
独立推进，但不能替代运行时实现版本。

如果文档变化触及科学定义、公开 API、默认值、失败行为、适用域、依赖或 TaskGraph 组合，
它就不是文档修订，必须和新的 wheel 候选一起发布。文档修订号不能替代
`implementation_version`，也不能增加 wheel 没有的能力。当前 dev8/dev9 历史候选继续由
Git、短发行说明和外部 manifest 恢复；当前 dev10 使用单一 exact `0.1.0.dev10`。

## 开发版本

- [0.1.0.dev8](release/0.1.0.dev8-notes.md)：历史开发候选摘要；完整源码和 wheel 由 Git 历史恢复。
- [0.1.0.dev9](release/0.1.0.dev9-notes.md)：依赖分层、安装包版本读取和 Linux amd64 + CPython 3.14 clean-venv 验收；历史开发候选。
- [0.1.0.dev10](release/0.1.0.dev10-notes.md)：文档闭包重资格化和 sampling 失败语义修正；当前仍是开发候选。

历史版本由 Git 提交和 tag 恢复。构建产物摘要、平台回执和当前候选绑定见 [`release/CURRENT.json`](../release/CURRENT.json)。
