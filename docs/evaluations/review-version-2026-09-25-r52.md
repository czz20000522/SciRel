# SciRel 审核证据纠正 r52(evidence-only)

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空。本版是 r51(`de0342ac3319c6c2e2726ce10f89791e9609b9fb`,快照 `build/verification/review-2026-09-25-r51-h2-collision-data`)的 **evidence-only successor**:零科学代码、零测试文件、零 exact-document 变更;版本 `0.1.0.dev25` 不变,dev25 wheel 与 catalog 字节逐字节复用 r51(复用声明见下),未为文案变动重跑任何全仓测试。r51 快照目录及其 manifest/证据副本原样保留,不可改写。

## Codex 只读复核发现与核验结果

复核指出 r51 审核材料中的测试计数错误。经 `pytest --collect-only`(2026-09-26,仅针对相关文件,非全仓重跑)核实:

1. **r51 计数确属错写**。四个 H2 测试文件的真实函数数为:截面直接 **8**、速率直接 **7**、截面历史复放 **3**、速率历史复放 **4**,即 **15 direct + 7 replay = 22**。`review_candidates/2026-09-25-h2-collision-data/review.md` 原文"24 total: 17 direct + 7"为错误算术;`build/test-evidence-r51.md` 原文"17 direct, 7 replay minus shared count: 8+9 direct, 3+4 replay = 24 collected ... deduplicated fixtures"既算错又以不存在的"fixture 去重"机制臆测解释——四个文件共 22 个测试函数,无共享、无去重。
2. **同型错误延伸至 r49 候选文字**(自查发现):`review_candidates/2026-09-25-atomic-h-collision-data/review.md` 原文"63 total: 21 direct + 4 replay per asset"与 README 三行"21 direct + 4 replay"亦错。collection 实测:原子三资产为截面 8+4、速率 7+4、COLLRAD 10+4,即 **25 direct + 12 replay = 37**(与 r49 冻结说明中"37 passed"一致的运行数,错的是候选文档的分项解释)。
3. **冻结材料无此错**:r51/r49 的 dossier 与 intake 文档中的计数("22 passed"、"37 passed")经核均正确,无需也不应改写任何冻结材料。

## 纠正方式(可核对差异保留)

- 可变候选文字逐处更正并标注 "corrected in r52":两份 H2 候选文件(review.md 计数、README 速率行 9→7)、两份原子候选文件(review.md 的 63→37 分项、README 三行 21→8/7/10)。
- `build/test-evidence-r51.md` 第 2 条改为正确分项并以 "Correction note (r52)" 保留原错句于文内,审计轨迹完整;该文件为未跟踪工作文件,r51 快照内副本保持原字节。
- 冻结材料(dossiers、intake 文档)一字未动;其与 r51 manifest 记录的摘要继续逐位一致。

## 审阅材料覆盖边界(如实声明)

r51(及 r49)manifest 的 `review_materials` 只含 docs/ 下领域、整合与版本文档(冻结脚本硬约束仅接受 `docs/*.md`),**未列出本批 H2 候选 review.md/README/8 份 proposal 三件套,也未列出 r49 原子批三件套**。这些字节确实存在于冻结 commit 的 tracked tree(`dbb4385`/`0035e9e`/`de0342a`),但仅凭 manifest 材料清单的专家不会被指向它们——因此此前各快照**不能声称自包含**,首轮全 76 项审核的入口材料存在此覆盖边界。

r52 的处置:新增 `docs/evaluations/candidate-review-materials-index-2026-09-25.md` 并纳入本轮冻结材料,以精确 SHA-256 逐文件绑定两批候选三件套(共 24 个文件)于 r52 冻结 commit,使 manifest 材料链显式指向真实专家审核入口;其中 H2 review.md/README 为本轮计数纠正后的字节。摘要绑定与精确范围以该索引为准,任何后续候选文字改动需新 successor 而非静默编辑。

## 复用声明与验证

- wheel `scirel-0.1.0.dev25-py3-none-any.whl` SHA-256 `a3b72aee1d01021e8cbee6005a3ed5c620ded553ac318b1f54fc4d74ef782ee1` 与 catalog `complete: 76/76` root `sha256:9b87786685adea5d120a4616c74d44a607f9bc1d8c4e5fe3a0edf8d98a26953e` **逐字节复用 r51**:r52 只改 Markdown 候选/说明文字,wheel 仅打包 `src/scirel`(逐字节未变,freeze 的 wheel==committed-source 校验照常执行),catalog 输入未变。
- 本轮执行的验证仅为 `pytest --collect-only` 两次(22 = 15+7;37 = 25+12),未执行任何科学测试运行,无既有断言变化。
- 不宣称:科学增量(r52 无)、合格 L1 消费、专家认可、可信晋级或公开发行。许可证 `pending-human-decision`;无可信基线,首次专家审核覆盖全部 76 项。
