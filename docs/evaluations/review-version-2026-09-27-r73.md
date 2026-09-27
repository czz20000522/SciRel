# SciRel pointwise firehose-margin relation r73

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r72(`c1f7fcd`,`0.1.0.dev47`,147 资产,快照 `build/verification/review-2026-09-27-r72-cross-node-leaves-v3`)的 successor;既有快照原样保留。本批不消费任何 L1、保存包或合格交付根(开始与结束均复核为空);唯一输入是 SciRel 自有关系的独立分解与出库评测的开发期证据记录。

## 性质:一项新 operator(逐点火焰管压强裕度)

`scirel.diagnostics.pointwise-firehose-margin`(`compute_pointwise_firehose_margin`):逐点返回 Pa 量纲 `firehose_margin = B^2/mu0 + p_perp - p_parallel`,元素独立计算。没有导数、没有磁镜分支、没有最小值归约、没有任何 stable 标志;单样本与全等 B 是正常输入域。

## 出库评测问题的独立评估

两个新的无辅导出库运行(兄弟主仓库 checkout 的开发期记录 `results-2026-09-27-flat-b.md` 与 `results-2026-09-27-state-json.md`,各有摘要绑定的 manifest、trace 与归档原始证据)呈现同一选择失败:

- flat-b:三个独立虚构的 B=1 T 单点状态,`run_evidence.json` 自身记录 `mirror_branch_applicable=false` 的同时仍发生了 3 次组合诊断 `callable.invoke`;
- state-json:两个单点状态各被调用一次,CSV 记录了退化的正"mirror margin"(恰为 `B^2/mu0`)与 `mirror_sample_flag=True`,仅以 `mirror_criterion_evaluated=False` 列作缓兵;两次运行的最终散文都正确拒绝给出稳定结论,但程序层没有。

对照当前实现(`src/scirel/diagnostics/firehose_mirror_margins.py`)、其 exact document(`identity.boundary` 的零导数约定、`assumptions` 的调用方前提)与直接测试:组合资产自身一致且如实——问题是关系形状,不是文字问题。需要逐点量的调用方被迫调用同时携带集合依赖磁镜分支与聚合 stable 标志的资产;技能文字多轮收窄(含 flat-b 在最终方法修订后的运行)都没有消除该失败。flat-b 记录的备选补救("science-owner 决定分离逐点关系与集合依赖 callable")即本批实现。

## 判重结论

- 对组合诊断 `firehose-mirror-margins`:不同关系(方向与输出签名不同);新资产是刻意去除跨样本与标志机制后的逐点子关系,直接测试钉定共享字段逐位相等,数值合同不分叉。
- 对 `anisotropic-force-balance`:其无量纲 `1 - mu0*(p_parallel - p_perp)/B^2`(B 下取 tiny)单位与代数形均不同,领域草稿本就记录两者非同端口。
- 对 `parallel-pressure-residual` 与磁镜动理学族:不同关系,无重叠。
- 未发布候选池按关系复核:无任何待审批含火焰管/磁镜/各向异性压强裕度关系(2026-09-24 池快照的 firehose 命中是已迁移的 Pleiades 开发样本)。

## 登记的合同决定

- **输出恰含一个字段** `firehose_margin`:测试把五个禁用键(mirror/最小值/stable)的缺席作为合同断言。
- **无稳定性语义**:负值原样返回、正值不加标签;exact doc 明示"不解释符号"。
- **登记的 fail-closed 加固**(沿 r71/r72 路线):空样本集拒绝(组合资产要到最小值归约才失败);`B^2/mu0` float64 溢出拒绝(`errstate` 抑制中间警告);**非标量 mu0 在算术前拒绝**(1 元素数组会静默把输出广播成 (1,) ——评审发现,已回归)。
- **与组合诊断共享字段逐位相等**:随机有限输入上的精确数组相等测试。

## 组合证据

- 10 项直接测试(见 `build/test-evidence-r73.md`)。新资产无 TaskGraph 消费者(对照 r72 catalog 反向依赖索引核实);组合证据 = 跨资产相等测试 + 公共 surface 导入测试,该组合缺口(无已发布组合)如实声明。
- 无保存源复放:本批不消费外部来源,无源映射摘要表;以"无进入来源"声明替代。

## 相对 r72 的增量

- r72: FIDASIM cross-node leaf family(5 项),147 资产 dev47
- r73: pointwise firehose-margin relation(1 项),148 资产 dev48
- 版本 `0.1.0.dev47` → `0.1.0.dev48`;其余 147 份文档仅机械 `implementation_version` 提升;组合诊断的源码字节、文档语义与测试原样未动。

## 验证(全部记录于 `build/test-evidence-r73.md`,所有子进程 returncode 已核)

- 源码态全仓(复放激活):**1550 passed, 43 skipped, 0 failed**,returncode 0(r72 全树 1540,+10:9 项直接测试 + 1 项 mu0 评审回归;无复放根的同树实测 1398/194,两项均为预期状态)
- 148/148 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r73-clean`,自装 numpy 2.5.1 / scipy 1.18.0 / pytest 9.1.1 + setuptools,wheel `--no-index --no-deps`,`-I -o pythonpath=`):**1406 passed, 194 skipped, 0 failed**,returncode 0(r72 干净 venv 回执 1386/197;本轮回执在含 setuptools 的 venv 中运行,`test_admitted_wheel_runs_the_source_free_user_acceptance` 实际执行并通过,并附显式 import 路径检查)
- catalog `build/catalog/r73`:`complete: 148/148`,root digest 见 manifest
- 内部 wheel `scirel-0.1.0.dev48-py3-none-any.whl`,SHA-256 见 manifest

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 开放专家问题:逐点 firehose 关系是否应与组合资产长期并存(还是组合资产未来重构为该逐点关系 + 显式镜像关系);出库评测暴露的"调用方选择"失败是否需要额外的 catalog 消费端指引;许可证状态均 `pending-human-decision`
