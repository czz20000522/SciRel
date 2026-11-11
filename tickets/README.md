# 人工裁决工单

这里存放需要物理审核人裁决的 C 级问题。分级、格式、状态机和读写权限以
[supply-pipeline.md 第 7 节](../docs/maintainer/supply-pipeline.md) 为准，这里只写怎么用。

- 一张工单一个文件：`tickets/<kind>/<id>.md`。`kind` 是 `physics-dispute`、`convention`、
  `scope`、`evidence-gap` 之一，并且和所在目录同名；文件名等于 `id`（`T-YYYY-NNNN`）。`kind` 定下后不再改。
- 状态只写在 frontmatter 里，状态变化时不移动文件。工单不删除，处理完写成 `closed`。
- 本仓库是公开的：工单不写来源项目的身份、私有路径或未公开材料。

## 开工先查工单

```sh
python3 scripts/tickets.py list tickets --status decided
```

列出的工单已经有裁决，先执行它们：按 `resolution` 改实现，完成后写 `applied: {"by": ..., "ref": <commit 或 PR>, "date": ...}`，并把 `status` 改成 `applied`。核对无误后改成 `closed`。

## 新开工单

1. 先执行安全默认：不改实现，把疑点写进合同的局限性；如果是新增能力，先不合并。
2. 在对应的 `kind` 目录下新建 `<id>.md`，`status: open`。`decisions` 和 `resolution` 由审核平台写，agent 不写。
3. 正文必须做到：审核人只读这一页就能作出决定。

## 检查

```sh
python3 scripts/tickets.py check tickets                     # 格式、位置、id 唯一
python3 scripts/tickets.py check tickets --base origin/main  # 加上相对基线的状态流转
```

第一条随完整检查运行（`tests/tooling/test_tickets.py`）。第二条由合并者在合并前运行，用来拦住跳步、越权写字段和删除工单。
