# 人工裁决工单

这里存放需要物理审核人裁决的 C 级问题。分级、格式、状态机和读写权限以
[supply-pipeline.md 第 7 节](../docs/maintainer/supply-pipeline.md) 为准，这里只写怎么用。

- 一张工单一个文件：`tickets/<kind>/<id>.md`。`kind` 是 `physics-dispute`、`convention`、
  `scope`、`evidence-gap` 之一，并且和所在目录同名；文件名等于 `id`（`T-YYYY-NNNN`）。`kind` 定下后不再改。
- 状态只写在 frontmatter 里，状态变化时不移动文件。工单不删除，处理完写成 `closed`。
- 本仓库是公开的：工单不写来源项目的身份、私有路径或未公开材料。


## 工单准入：只有两类问题可以进

**工单是给专家看的，不是缺陷收集箱。** 写进去的每一条，都在要求一个人花专业时间读一页并作出判断。
准入不足的单子会稀释这份注意力，让真正需要专家的问题淹没在可以被证据解决的问题里。

**准入（两条都不满足就不进）：**

1. **复杂物理语义判断**：agent 无法通过证据、测试、文献、文档或案例决定。例如两个碰撞项该如何组合才不重复计入同一份动量。
2. **必须由人判断危害**：技术上可以定，但定错的代价需要人来承担。例如某个公开接口的语义没有公认标准，暴露它本身就是风险。

**不进工单的（走证据路线，能推荐就推荐并执行）：**

| 情况 | 走哪条 |
| --- | --- |
| 合同与代码不符 | 按代码改合同（合同是衍生物），不需要人 |
| 合同与项目规范不符 | 规范是上位，改实现去对齐 |
| 上游库有明确约定（scipy / numpy / OpenFOAM） | 实测上游行为，按它的约定统一 |
| 有解析恒等式、极限或守恒律可验 | 写测试验它 |
| 只是措辞不精确 | 改措辞 |
| 已经自我订正、仅留说明性记录 | 结案，不占位置 |

**并且：没有确定标准支撑的接口，先撤下来。** 宁可不暴露，也不暴露一个可能错的。暴露错的危害远大于少一个功能——少一个功能用户会去找别的办法，错一个功能用户会拿到一个看起来对的数。

这条规则由维护者定（2026-11-18），先于本页其余流程。

## 开工先查工单

```sh
python3 scripts/tickets.py list tickets --status decided
```

列出的工单已经有裁决，先执行它们：按 `resolution` 改实现，完成后写 `applied: {"by": ..., "ref": <commit 或 PR>, "date": ...}`，并把 `status` 改成 `applied`。核对无误后改成 `closed`。

## 新开工单

1. 先执行安全默认：不改实现，把疑点写进合同的局限性；如果是新增能力，先不合并。
2. 在对应的 `kind` 目录下新建 `<id>.md`，`status: open`。`decisions` 和 `resolution` 由审核平台写，agent 不写。
3. `decision_owner` 必填，取 `maintainer` / `physics-reviewer` / `api-reviewer` / `platform` 之一。
   **没有归属人的工单是本仓库最贵的一种欠账**：它开着、门禁不红、安全默认悄悄变成永久行为。
   `T-2026-0800` 就是这样挂了七轮才等到一句话。
4. 正文必须做到：审核人只读这一页就能作出决定。

## 台账

```sh
python3 scripts/tickets.py ledger tickets          # 每张 open 工单：谁裁决、默认是什么、后果写了没
python3 scripts/tickets.py ledger tickets --json
```

退出码非零意味着某张 open 工单缺归属人或缺「不决定的后果」段落——这两种缺失都不该被
「清单看起来挺整齐」掩盖。

## 检查

```sh
python3 scripts/tickets.py check tickets                     # 格式、位置、id 唯一
python3 scripts/tickets.py check tickets --base origin/main  # 加上相对基线的状态流转
```

第一条随完整检查运行（`tests/tooling/test_tickets.py`）。第二条由合并者在合并前运行，用来拦住跳步、越权写字段和删除工单。
