# Contributing to SciRel

SciRel 是长期维护的独立 Python 科学关系库。贡献必须同时保护科学合同、公共 API、准入来源边界和可安装发行物；不能把它当作一次性资产汇总目录。

## 开发环境

使用 Python 3.10+ 与 `pwsh` 7+。在隔离环境安装项目及测试依赖：

```powershell
python -m pip install -e ".[test]"
pwsh ./scripts/check.ps1 -Mode affected
```

科学函数运行时不得依赖 CodeFusion、源项目 checkout、数据库、网络或主机绝对路径。依赖变更需先说明用途、运行时影响、许可证和替代方案；不为便利引入新的框架。

## 开始修改前

1. 阅读 `README.md`、[架构合同](docs/architecture.md)、相关函数、科学测试和 provenance。
2. 确认输入是否已有最终人工准入；候选、机器或 AI 检查结果不能代替准入。
3. 对照当前 Git/release 基线，列出公共 API、科学身份、直接依赖和受影响 TaskGraph。
4. 对增量资产使用项目的 `scirel-integration` skill；不要重新导入整批文件覆盖维护源码。
5. 新增或改变公共资产时维护对应标准资产文档，并运行 runtime/example/catalog release 验证；缺失可信元数据时保留 metadata gap，不生成占位科学合同。

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

选择器会加入改变资产的直接合同测试、所有传递依赖 TaskGraph、共享实现测试和准入一致性测试。当前工作区可省略
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
