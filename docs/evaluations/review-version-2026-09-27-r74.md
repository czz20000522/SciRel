# SciRel firehose B^2/mu0 措辞修正 r74

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r73-v2(`5241278`,`0.1.0.dev48`,148 资产,快照 `build/verification/review-2026-09-27-r73-pointwise-firehose-margin-v2`)的 successor;既有快照(含 r73-v1 与 r74-v1)原样保留。本批不消费任何 L1、保存包或合格交付根(开始复核为空,0 项);唯一输入是一次只读出库审计发现的科学措辞错误,由维护者直接下达修正任务。

v2 说明:本 dossier 是 r74-v2 的更正版审核说明。r74-v1(快照 `build/verification/review-2026-09-27-r74-firehose-tension-wording-v1`,commit `1da9e14`)冻结后,只读 Codex 评审发现其 post-freeze addendum 把两项开发差量误述为"专家审核范围"。r74-v2 与 v1 的科学内容、exact documents、wheel、catalog、测试证据完全相同(digest 不变),唯一差异是本 dossier 补充的审核范围更正;v1 原样保留,不被改写。

## 性质:纯科学措辞修正(零科学行为变化)

只读出库审计发现:火焰管裕度公式中的 `B^2/mu0` 项在两份活文档的 `magnetic_field` 输入描述里被称为磁压(magnetic pressure)项,但 SI 磁压是 `B^2/(2*mu0)`;`B^2/mu0` 在该公式中是**以压强为单位的磁张力贡献**(磁场弯曲产生的单位长度张力,写作压强量纲)。同义别名 "firehose tension margin"(组合资产)本就使用张力措辞,公式、单位(Pa)与数值本身自始正确,错的只是名称。

本批修改(无任何 `src/scirel` 字节变化,无公式、数值行为、API、容差、默认值变化,无资产增删):

- `catalog/examples/scirel.diagnostics.pointwise-firehose-margin.json`(`magnetic_field.description`):"the B^2/mu0 magnetic-pressure term" → "the B^2/mu0 term, the magnetic-tension contribution in pressure units (SI magnetic pressure itself is B^2/(2*mu0), a different quantity)"。
- `catalog/examples/scirel.diagnostics.firehose-mirror-margins.json`(`magnetic_field.description`):"for magnetic pressure and the B-value derivative" → "for the B^2/mu0 magnetic-tension contribution and the B-value derivative"。
- `tests/operator_contracts/test_pointwise_firehose_margin.py`:两个测试更名(`test_overflowing_magnetic_pressure_fails_closed` → `test_overflowing_magnetic_tension_term_fails_closed`;`test_mu0_override_changes_only_the_magnetic_pressure_term` → `test_mu0_override_changes_only_the_magnetic_tension_term`)并同步修正两行注释(明示 SI 磁压为 B²/(2mu0)、不是本项);测试体逐字节未动,断言与容差原样。
- 机械版本提升 `0.1.0.dev48` → `0.1.0.dev49`(全部 148 份 exact documents 与 `pyproject.toml`);其余 146 份文档仅此机械变化。

## 范围审计

- 全仓检索 `magnetic pressure`/`磁压`:活树命中仅上述两份文档与该测试文件;`provenance/pleiades-import.json` 与 `review_candidates/2026-09-27-pointwise-firehose-margin/proposal/` 属冻结来源/候选记录,按"冻结记录不可改写"保留原文。`docs/domains/anisotropic-pressure-diagnostics.md` 只陈述公式,未把 `B^2/mu0` 称作磁压,无需修改。`src/scirel` 两个诊断模块的 docstring 无磁压措辞。
- 领域复核:磁压 `B^2/(2mu0)` 出现在垂直力平衡的 `∇⊥(B^2/2mu0)` 项;火焰管判据 `p_∥ - p_⊥` 侧的 `B^2/mu0` 来自磁张力。两份 exact document 的 `identity.model`/`definition` 均只写公式与 "written in pressure units",无需改动;`anisotropic-force-balance` 的无量纲裕度不含磁压措辞。

## 审核范围:首次审核集合为全部 148 份 exact documents

当前没有可信基线:`docs/development-process.md`(冻结待审版一节)与 `docs/requirements/scirel-workflow.md` 均明确,无可信版时不传比较快照,首审集合为全部文档。因此本版的专家审核范围(`review_scope.py` 无比较快照模式,对 r74-v1 与 r74-v2 实测相同)是 `mode: first_review`、`review_asset_ids` 为**全部 148 项资产**、`baseline_approval_verified: false`。

与 r73-v2 的快照比较(`--comparison-snapshot r73-v2`)返回 `mode: snapshot_comparison`、`changed_document_ids` 2 项、`mechanical_only_document_ids` 146 项、`baseline_approval_verified: false`——r73-v2 本身是 `pending_unapproved` 开发快照,该比较只作为**开发增量导航辅助**(帮助专家定位本批相对上一开发版改了什么),不是审核范围,也不把 r73-v2 冒充上一可信版。

## 流程修正记录

本批的措辞编辑最初在嵌套 Git worktree(`.claude/worktrees/r74-tension-wording`,commit `8ea24e5`,branch `r74-firehose-tension-wording`)中进行并做过一轮验证;该环境阻断了 pwsh、迫使 Git Bash 绕行,被判定为无效验证。已将该 commit 以 `git apply --binary` 逐字节转移到本 checkout(150/150 个变更文件 SHA-256 逐一比对一致),嵌套 worktree 在比对通过后才移除(branch 与 commit 保留)。下列全部回执均在 pwsh 7+ 于本 checkout 对转移后字节实测。详见 `build/test-evidence-r74.md`。

r74-v1 冻结后,只读 Codex 评审发现其 post-freeze addendum(`build/test-evidence-r74-scope-addendum.md`)把 "review_asset_ids equals changed_document_ids(2 项)" 表述为专家审核范围——这忽略了无可信基线时的全量首审要求。本 v2 以更正后的 dossier 重冻;更正后的 addendum 在 v2 冻结后以两种 `review_scope` 模式的实测回执重写并以新 commit 记录。

## 验证(全部为实测回执,子进程 returncode 已核;详见 `build/test-evidence-r74.md`)

- 受影响选择器:`full_suite_required: true`(公共基线变化:pyproject + 148 份文档 fail closed 到全套),按冻结门禁跑全仓。
- 源码态全仓(复放根激活):**1550 passed, 43 skipped, 0 failed**,returncode 0(与 r73-v2 完全一致;更名不改计数)。
- 文档校验源码态:**148/148**,`runtime_origin: source`,`examples_executed: true`。
- 安装态(干净 venv `build/venv-r74-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1 + setuptools 84.0.0,wheel `--no-index --no-deps`,`-I`):文档 **148/148**(`runtime_origin: installed`,示例执行通过);全树 **1398 passed, 195 skipped, 0 failed**,returncode 0,含 `test_admitted_wheel_runs_the_source_free_user_acceptance` 实跑通过(均与 r73-v2 安装态回执一致)。
- 更名的两个测试在源码态与安装态均按名执行通过(2 passed 各)。
- catalog `build/catalog/r74`:`complete: 148/148`,root digest `sha256:66130f61f5e013370d0ffef7972f11c60749bd006709b86205458e9bb54c8d43`。
- 内部 wheel `scirel-0.1.0.dev49-py3-none-any.whl`,SHA-256 `4796ff07cb13972fed6fe366d84ba70de22615b2893dfe5dd555a79da66f5ac9`。

## 相对 r73-v2 的开发增量(导航辅助,非审核范围;审核范围见上节)

- 两份 exact document 的输入描述措辞修正(唯一非机械文档变化);1 个测试文件更名/注释;146 份文档机械版本提升;`src/scirel` 零字节变化。
- 版本 `0.1.0.dev48` → `0.1.0.dev49`;资产数不变(148);测试计数不变。

## 边界与待决

- 不宣称新合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 不宣称 2026-09-27 出库 holdout 的后续自主评测已完成;其证据尚未冻结
- 冻结材料中的同源措辞(`review_candidates/2026-09-27-pointwise-firehose-margin/proposal/`、`provenance/pleiades-import.json`、r73 评估记录与 r73 快照)按冻结不可改写原则保留原文;专家如认为需要,可在审核本版时决定是否另立冻结记录修正流程
- 许可证状态仍为 `pending-human-decision`
