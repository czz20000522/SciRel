# SciRel 开发与增量整合流程

本流程适用于已完成人工准入后的首次组包、增量资产整合、公共 API 维护和发行候选验证。它不替代 CodeFusion 的拆解、机器/AI 检查、人工验收或发布授权。

## 1. 冻结输入与基线

先读取 `README.md`、相关实现、科学测试、`provenance/admitted-assets.json` 和当前 Git 状态。记录本次精确准入 revision、当前 SciRel 版本/内容锁、公共 callable、依赖闭包和相关测试。磁盘上的候选文件、源项目 checkout 或“最新”别名不能替代准入版本。

没有正式发行基线时才按首次组包处理。有基线但暂时缺少 wheel 或内容锁时先恢复基线，不能借此绕过兼容检查。不得整批覆盖导入；逐项对照当前 Git 基线，并保留其他贡献者的修改。

## 2. 形成最小整合清单

每个输入只记录一次：目标科学身份、与现有能力的关系、拟采取动作、理由、公共 API 影响、受影响 TaskGraph、验证方式和待决项。清单可以放在当前任务或既有组装记录中，不为单次工作复制多份状态文档。

比较顺序如下：

1. 关系/equation、实现方向、变量和假设；
2. 单位、坐标、轴序、shape/dtype、符号和归一化；
3. 模型、几何、边界、闭合、初始条件和适用域；
4. 状态所有权、更新顺序、反馈、收敛、重启和失败行为；
5. 离散、插值、求解器、矩阵/RHS、容差与误差；
6. 证据上限、provenance、许可证和实现差异。

据此选择复用、新增、保留变体、无损适配、组合、兼容替换或保持未决。哈希可以筛出相同字节，名称和相似度可以帮助检索，但都不能独立证明科学等价。无法判断的资产保持分离；可以继续不依赖它的工作。

## 3. 实施最小变化

- 先写或保留能观察目标行为的合同；科学行为变化必须先有失败回归。
- 公共 API 继续使用按领域组织的 Python callable；REST/CLI 仅在有明确消费者时作为适配器增加。
- TaskGraph 显式绑定节点、边、状态、反馈和依赖 revision，不把新科学规则藏进 glue。
- 从变更资产沿反向依赖找到受影响 TaskGraph；未受影响资产保持精确锁。
- 行为相同的共享代码可以提取，但只有科学合同相同才可合并身份。
- 参考实现只吸收与当前问题相关的可观察行为和反例，不复制其整个框架。

任务专有的参数、数据路径和一次性选择留在任务中；可迁移的方法进入 skill；已经确认的公共行为由测试保护。一次事故优先补局部回归或修正文档，不自动增加全局门禁。

## 4. 分层验证

测试分离是 SciRel 的基本合同。每个 admitted asset 必须能映射到直接合同测试；TaskGraph 的精确 dependency refs
形成科学依赖图，Python import 形成共享实现依赖图。一次源码变更的测试范围是：改变资产的直接测试、所有传递
依赖它的 TaskGraph 测试、相关共享/准入一致性测试。不能映射的 `src/scirel` 文件、测试共享材料或公共基线变更
必须 fail closed 到全套，不能返回空测试集。

使用仓库统一入口，避免手工遗漏 `src`/`tests` 的 Python 路径：

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
pwsh ./scripts/check.ps1 -Mode affected -BaseRef <merge-base-or-release-ref>
pwsh ./scripts/check.ps1 -Mode focused
pwsh ./scripts/check.ps1 -Mode full
pwsh ./scripts/check.ps1 -Mode release -OutputRoot build/verification/<new-run>
```

- `affected`：从显式路径、Git 工作区或 `base...HEAD` 计算影响闭包，输出机器可读选择报告后只运行所选测试；共享模块会自然扩大到其消费者，未知源码会转为 full。
- `focused`：默认检查公共 surface、组合和准入绑定；也可通过 `-TestPath` 指定本次精确测试。
- `full`：运行完整科学与工程测试。
- `release`：先运行全套测试，再生成新的 admitted-only staging/wheel，并在不含源码 `PYTHONPATH` 的独立环境安装该 wheel、执行用户验收。

内循环默认运行 `affected`；正在编写失败回归时可用 `focused -TestPath` 只跑该断点。修复后重跑失败断点和受影响闭包，
不因单个独立算子变化反复运行全仓。合并到共享基线前按影响与仓库策略运行 full，候选确定后再执行一次 release
门禁。未变化的代码、输入和环境可以复用仍有效的证据，但发行结论必须绑定本次实际 wheel、工具链和输出摘要。

`scripts/select_affected_tests.py` 的 JSON 报告是可重建工程证据，不是新的治理事实。新增资产没有直接测试映射、
依赖引用缺失或选择器无法解释源码归属时应阻断增量门禁；禁止用手写排除列表绕过。选择器自身的回归测试必须覆盖
独立算子、直接图依赖、嵌套图依赖、共享模块扩散、文档零测试和未知源码 fail-closed。

`release` 的输出目录必须不存在，脚本不会覆盖或清理已有结果。正式发行还需固定 Python 与构建工具版本；不同工具链下 wheel 字节摘要不同，即使内置内容 manifest 保持一致，也不能声称可复现构建。

## 5. 收尾与发行边界

提交前重新读取当前基线；若并行变更改变了公共 API、依赖或内容锁，重新比较受影响项。交付记录应列出实际修改文件、执行的检查、候选 wheel/manifest 摘要、未验证边界和待决项的关闭条件。

构建、测试、组装和自然语言任务验收均不自动产生人工批准或公开发布。冻结的准入/审核记录不回写；SciRel 源码演进、版本和新证据单独记录。正式发布前还必须确认许可证、声明依赖、固定工具链，以及发布方要求的授权与投影一致性。
