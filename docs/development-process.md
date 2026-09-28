# SciRel 开发与增量整合流程

本流程适用于从保存的 L1 产物开始的候选准备、专家审核、批准后整合和 release。SciRel 拥有这些领域状态；CodeFusion 只提供中性 Agent 执行、artifact、身份和审核 UI。历史 admitted-only 内容仅作为开发期输入证据，不构成新流程的长期前置条件。

完整的生命周期需求和 plugin 边界见 [`SciRel L1 到 Release 需求`](requirements/scirel-workflow.md) 与 [`CodeFusion 宿主插件需求`](requirements/codefusion-plugin.md)。

这里有一条必须保持的边界：`scirel-integration` skill 描述模型理解、比较、去重、变体判断和
整合的方法；代码只实现已经稳定、可复用且能确定判断的门禁。模型可以为当前资产临时编写
探针、数值实验和测试，不要求统一验证脚本或固定中间产物。只有反复证明具有项目级复用价值
的检查才进入 `scripts/` 或测试基线。

## 1. 冻结输入与基线

先读取 `README.md`、相关实现、科学测试、历史 `provenance/admitted-assets.json`、当前 Git 状态和全部未发布候选。固定本次保存的 L1 输入、只读 SciRel baseline、公共 callable、依赖闭包和相关测试。候选准备期间不得修改该 baseline；候选文件只写入隔离 worktree、patch 或本次输出目录。历史准入记录只用于理解已有来源和行为，不能阻止从新的 L1 输入重新比较，也不能替代后续专家审核。

没有正式发行基线时才按首次组包处理。有基线但暂时缺少 wheel 或内容锁时先恢复基线，不能借此绕过兼容检查。不得整批覆盖导入；逐项对照当前 Git 基线，并保留其他贡献者的修改。

## 2. 形成最小整合清单

每个输入只记录一次：目标科学身份、与现有能力、未发布候选及同批候选的关系、拟采取动作、理由、公共 API 影响、受影响 TaskGraph、验证方式和待决项。冻结基线、未发布候选池和当前 L1 共同构成比较视图，但只有冻结基线是权威且可运行的资产事实。清单可以使用最适合当前任务的形式放在任务或既有组装记录中；不要求统一 manifest/receipt，也不为单次工作复制多份状态文档。

比较顺序如下：

1. 关系/equation、实现方向、变量和假设；
2. 单位、坐标、轴序、shape/dtype、符号和归一化；
3. 模型、几何、边界、闭合、初始条件和适用域；
4. 状态所有权、更新顺序、反馈、收敛、重启和失败行为；
5. 离散、插值、求解器、矩阵/RHS、容差与误差；
6. 证据上限、provenance、许可证和实现差异。

据此选择复用、新增、保留变体、无损适配、组合、兼容替换或保持未决。哈希可以筛出相同字节，名称和相似度可以帮助检索，但都不能独立证明科学等价。无法判断的资产保持分离；可以继续不依赖它的工作。

## 3. 准备候选三件套

专家审核前只准备候选，不修改冻结 SciRel：

- 候选文档是主审查入口，解释现有能力、L1 能力、拟议处置、科学差异、API/依赖影响、证据、限制和专家需决定的问题；
- 候选代码给出批准后将实施的最小 patch 或隔离实现；
- 候选测试证明文档中声称的新行为、等价性、兼容性、边界和失败语义，并记录实际执行结果。

完全重复或直接复用可以没有运行时代码 patch，但文档必须明确说明，且测试或实验要支撑判断。候选三件套不要求统一 schema 或目录；不得为了形式完整制造空实现。

候选同时记录比较时的 SciRel Git base。模型可以在上传前合并、替换或撤回草稿以减少重复审核；上传时逐项固定初始三件套版本，工作台不在后台运行模型来改写队列。专家查看记录所见版本，领取后可保存修改；放回保存版本并释放锁但不完成审核，显式提交才产生该项审核结论。若需要新的 AI 准备，另起任务生成关联候选并由上传者明确提交。候选入队后原模型运行结束，不等待人工审核。

## 4. 批准后实施最小变化

- 先写或保留能观察目标行为的合同；科学行为变化必须先有失败回归。
- 公共 API 继续使用按领域组织的 Python callable；REST/CLI 仅在有明确消费者时作为适配器增加。
- TaskGraph 显式绑定节点、边、状态、反馈和稳定依赖 asset IDs，不把新科学规则藏进 glue。
- 从变更资产沿反向依赖找到受影响 TaskGraph；未受影响资产沿用当前 canonical contracts。
- 行为相同的共享代码可以提取，但只有科学合同相同才可合并身份。
- 参考实现只吸收与当前问题相关的可观察行为和反例，不复制其整个框架。

当组装过程触及 L3 能力边界时，停止猜测式拼接并登记 `capability_gap`。缺口记录至少说明缺少的关系/模型、已检查的兼容条件、未满足的输入或证据，以及是否需要新 Operator、TaskGraph、标准或数值方法。后续按“发现 -> 拆解 -> 标准文档 -> 审核/验证 -> catalog -> 组装”推进；临时运行实例和 skill 产物不直接写入公共资产。

任务专有的参数、数据路径和一次性选择留在任务中；可迁移的方法进入 skill；已经确认的公共行为由测试保护。一次事故优先补局部回归或修正文档，不自动增加全局门禁。

只有专家批准的处置才进入本节。实施必须与批准的候选文档、代码和测试可核对；实质变化需要重新审核，不能借实施阶段扩大候选范围。

批准后由独立固化任务对照当前基线实施。初期串行处理已批准候选：原 patch 仍可保持时应用并运行 affected tests；若同一资产、科学合同、依赖闭包、TaskGraph 或 patch hunk 已被其他候选改变，则停止并基于当前基线生成新候选。旧批准不自动转移，新候选即使变成“重复/复用”也要明确交代。候选可以堆积在隔离 artifact、branch 或 worktree，但不能进入公共 import、catalog 或 wheel。

## 5. 分层验证

SciRel 的库门禁从已交付的输入包开始，不重验具体源项目的 D1 冻结；接收包时验证传输、路径与结构安全，
不把来源实现与当前 SciRel 函数逐输出一致作为维护或发行条件。来源记录可保留为历史证据，科学合同、
直接函数测试、TaskGraph 组合、审核状态和 wheel 验收才是当前库门禁。

测试分离是 SciRel 的基本合同。每个受维护的公共资产必须能映射到直接合同测试；TaskGraph 的精确 dependency refs
形成科学依赖图，Python import 形成共享实现依赖图。一次源码变更的测试范围是：改变资产的直接测试、所有传递
依赖它的 TaskGraph 测试、相关共享/准入一致性测试。不能映射的 `src/scirel` 文件、测试共享材料或公共基线变更
必须 fail closed 到全套，不能返回空测试集。

使用仓库统一入口，避免手工遗漏 `src`/`tests` 的 Python 路径：

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
pwsh ./scripts/check.ps1 -Mode affected -BaseRef <merge-base-or-release-ref>
pwsh ./scripts/check.ps1 -Mode focused
pwsh ./scripts/check.ps1 -Mode full
pwsh ./scripts/check.ps1 -Mode release -WorkflowSnapshot <approved-workflow.json> -ReleaseId <release-id> -OutputRoot build/verification/<new-run>
```

- `affected`：从显式路径、Git 工作区或 `base...HEAD` 计算影响闭包，输出机器可读选择报告后只运行所选测试；共享模块会自然扩大到其消费者，未知源码会转为 full。
- `focused`：默认检查公共 surface、组合和准入绑定；也可通过 `-TestPath` 指定本次精确测试。
- `full`：运行完整科学与工程测试。
- `release`：先验证输入是 approved workflow，再运行全套源码维护测试和 exact document 检查，从当前维护基线构建普通 wheel 与 catalog；随后在隔离环境中验证已安装 wheel 的文档示例、科学合同、公共 API 和用户验收，最后用实际摘要生成 release manifest 与 released workflow 快照。历史 admitted-only builder 不参与此路径。

内循环默认运行 `affected`；正在编写失败回归时可用 `focused -TestPath` 只跑该断点。修复后重跑失败断点和受影响闭包，
不因单个独立算子变化反复运行全仓。合并到共享基线前按影响与仓库策略运行 full，候选确定后再执行一次 release
门禁。未变化的代码、输入和环境可以复用仍有效的证据，但发行结论必须绑定本次实际 wheel、工具链和输出摘要。

`scripts/select_affected_tests.py` 的 JSON 报告是可重建工程证据，不是新的治理事实。新增资产没有直接测试映射、
依赖引用缺失或选择器无法解释源码归属时应阻断增量门禁；禁止用手写排除列表绕过。选择器自身的回归测试必须覆盖
独立算子、直接图依赖、嵌套图依赖、共享模块扩散、包级公开导出、文档零测试和未知源码 fail-closed。

`release` 的输出目录必须不存在，脚本不会覆盖或清理已有结果。其 venv 不继承 system site-packages，SciRel wheel 以 `--no-index --no-deps` 安装，并清空源码 `PYTHONPATH`；当前离线方式通过 `.pth` 暴露开发解释器中 NumPy/SciPy/Pytest 所在开发 site-packages，因此只证明 wheel 可在不导入 SciRel 源码的环境配合这些已存在依赖运行，不证明未声明包完全不可见，也不等价于从干净离线 wheelhouse 安装全部依赖。正式发行还需从固定的离线 wheelhouse 安装声明依赖，并固定 Python 与构建工具版本；不同工具链下 wheel 字节摘要不同，不能仅凭相同源码声称 wheel 字节可复现。

当前 catalog 为 `partial: 79/114` 开发 pilot。release manifest 只证明 approved draft 中的 exact documents 已与本次 catalog/wheel 绑定；它不会把 wheel 中未进入 catalog 的维护代码解释成已批准资产。正式首发前必须为全部可见发布资产完成 bootstrap/batch 审核与 exact documentation，并把 `.dev` schema 统一冻结为 `v1`。

## 6. 收尾与发行边界

提交前重新读取当前基线；若并行变更改变了公共 API、依赖或内容锁，重新比较受影响项。交付记录应列出实际修改文件、执行的检查、候选 wheel/manifest 摘要、未验证边界和待决项的关闭条件。

构建、测试、组装和自然语言任务验收均不自动产生人工批准或公开发布。冻结的准入/审核记录不回写；SciRel 源码演进、版本和新证据单独记录。正式发布前还必须确认许可证、声明依赖、固定工具链，以及发布方要求的授权与投影一致性。
