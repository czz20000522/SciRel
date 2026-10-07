# Contributing to SciRel

SciRel 是长期维护的独立 Python 科学关系库。贡献必须同时保护科学合同、公共 API、准入来源边界和可安装发行物；不能把它当作一次性资产汇总目录。

## 开发环境

使用 Python 3.10+ 与 `pwsh` 7+。在隔离环境安装项目及测试依赖：

```powershell
python -m pip install -e ".[test]"
pwsh ./scripts/check.ps1 -Mode affected
```

科学函数运行时不得依赖 CodeFusion、源项目 checkout、数据库、网络或主机绝对路径。依赖变更需先说明用途、运行时影响、许可证和替代方案；不为便利引入新的框架。

上述安装只提供科学库。开发 workflow/plugin/adapter 在源码 checkout 通过项目脚本、测试入口或显式
`PYTHONPATH=src` 使用；宿主服务须另行部署。项目与包的范围、历史样本及多版本 worktree 规则见
[开发项目与科学包交付](docs/design/project-and-distribution.md)。各整合/候选/维护分支使用独立环境和输出。

## 开始修改前

1. 阅读 `README.md`、[架构合同](docs/architecture.md)、相关函数、科学测试和 provenance。
2. 固定本次保存的 L1 输入和只读 SciRel 基线，并读取当前全部未发布候选；候选准备期间只写隔离 worktree/输出目录，L1 来源材料、机器检查和模型结论都不能代替后续专家审核。
3. 对照当前 Git/release 基线与候选池，列出公共 API、科学身份、直接依赖和受影响 TaskGraph；不要把不完整 catalog 当作全部已有能力。未发布开发候选可以明确其信任状态后用于内部验证，不能冒充已批准能力。
4. 对 L1 整合使用项目的 `scirel-integration` skill，逐项判断复用、重复、变体、组合、新增或未决；在隔离开发分支修改维护源码、测试和开发包。比较、去重与代码稳定后生成保留增量的正式文档，再提交最终待审三件套；人工认可不阻断日常开发，上一可信版保持只读。
5. 候选记录比较时的 Git base；上传前草稿可合并、替换或撤回，上传时固定逐项初始内容，首次打开只记录所见版本。候选入队后原 Agent run 即可结束；批准后由独立任务对照最新基线固化，同一资产、合同、依赖闭包、TaskGraph 或 patch hunk 已变化时形成关联候选，不采用 last-write-wins 或改写原审核版本。
6. 新增或改变公共资产，在代码稳定后、最终待审冻结前维护唯一标准资产文档，并运行相关 runtime/example/catalog 验证；缺失可信元数据时保留 metadata gap，不生成占位科学合同。

## 变更分类

- 科学行为：公式、模型、单位、轴序、边界、默认值、容差、失败行为、数值算法或图绑定发生变化。先写失败回归，并确认是否需要新的候选与审查。
- 公共接口：signature、module/symbol、返回结构或异常合同变化。默认保持兼容；破坏性变更说明调用方、版本影响、弃用与迁移路径。
- 行为不变重构：仍需运行原科学回归和受影响 TaskGraph，不改写冻结准入记录。
- 文档/工具：不得声称未实现能力；命令、路径和当前边界应能由可执行检查验证。

共享实现前先证明科学合同、默认值和失败行为确实相同。实现复用不自动合并科学身份；无法确定等价时保留变体或未决状态。

## 验证与提交

内循环默认按资产依赖计算精确测试：

```powershell
pwsh ./scripts/check.ps1 -Mode affected -ChangedPath src/scirel/<domain>/<asset>.py
```

选择器会加入改变资产的直接合同测试、所有传递依赖 TaskGraph、共享实现测试和历史绑定一致性测试。当前工作区可省略
`-ChangedPath`，提交范围使用 `-BaseRef <ref>`。只有正在处理单个失败断点时使用
`-Mode focused -TestPath tests/<relevant-test>.py`；不能手工缩小已经计算出的影响闭包。

切片稳定后按影响和合并策略运行 `-Mode full`。准备发行候选时使用一个全新的输出目录运行 `-Mode release`；保留 wheel、manifest digest、验收报告以及 Python/pip/setuptools 版本。不要删除旧断言、扩大容差或弱化异常检查来使替换通过。

标准资产文档和 catalog 改动另外运行：

```powershell
python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples
python -m pytest tests/test_asset_documentation.py
```

公开 provenance 只保留 framework-neutral lineage 摘要、公开参考和许可证状态。正式分发许可证仍是发布前的人类决定；贡献不得自行添加或推定许可证。

提交说明应解释为什么改变、可观察行为、兼容性和实际验证。交付时列出修改文件、检查结果、未验证边界与待决项。构建成功不产生人工批准或发布授权；冻结 provenance 不随源码演进改写。
