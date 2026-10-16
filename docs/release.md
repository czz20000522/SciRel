# SciRel 发行说明

发行说明只记录 Git 提交/tag 对应的短变更摘要。源码、API 参考、科学手册和 exact documents 继续维护在当前 `docs/` 树中；这里不复制整套文档，也不保存 wheel 文件。

## 开发版本

- [0.1.0.dev8](release/0.1.0.dev8-notes.md)：历史开发候选摘要；完整源码和 wheel 由 Git 历史恢复。
- [0.1.0.dev9](release/0.1.0.dev9-notes.md)：依赖分层、安装包版本读取和 Linux amd64 + CPython 3.14 clean-venv 验收；当前仍是开发候选。

历史版本由 Git 提交和 tag 恢复。构建产物摘要、平台回执和当前候选绑定见 [`release/CURRENT.json`](../release/CURRENT.json)。
