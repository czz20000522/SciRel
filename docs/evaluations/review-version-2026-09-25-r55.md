# SciRel 候选索引路径纠正 r55(evidence-only)

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根本轮开始与结束均复核为空。本版是 r54(`dc90bcfed87763b961b6cef67b009ac8186b6608`,快照 `build/verification/review-2026-09-25-r54-dissociation-rates`)的 **evidence-only successor**:零科学代码、零测试文件、零 exact-document 变更;版本 `0.1.0.dev27` 不变,dev27 wheel 与 catalog 字节逐字节复用 r54(复用声明见下),未做无关全仓重跑。r54 快照目录及其 manifest/材料副本原样保留,不可改写。

## Codex 只读复核发现与独立核验

复核指出 `docs/evaluations/candidate-review-materials-index-2026-09-25.md` 的 r54 批 36 个代码/测试/JSON 条目写成根级文件名,而其实际位于该批 Directory(`review_candidates/2026-09-25-dissociation-rates/`)之下的 `proposal/` 子目录;按 Directory 头逐条解析时 88 条中 36 条 missing。

独立核验(本先解析脚本自身一个缺陷——Directory 行路径的 markdown 反引号未剥离导致首跑误报 88 条全缺——修正后重跑):**88 条中 52 条解析成功且哈希匹配,36 条缺失,缺失者恰为 r54 批的 36 个裸文件名条目**;与 Codex 结论一致。错因:r54 重写索引时的 `Add-Entries` 调用对 r54 批把 36 个文件相对 `proposal/` 子目录解析,但条目行未写 `proposal/` 前缀,使条目相对声明的 Directory 不可解析;各条目的 SHA-256 本身自生成起即对真实文件计算,全部正确(r54 manifest 中 139 个文件摘要匹配亦印证字节无漂移)。

## 纠正方式与核验结果

- 索引中 r54 批的 36 条加 `proposal/` 前缀(仅路径文字,摘要一字不动);其余四批条目本就正确,不动。
- 修正后全量重验:**88/88 条按各自 Directory 解析存在且 SHA-256 逐条匹配**(52 原本已对 + 36 修正后对),0 missing、0 mismatch。
- r54 冻结材料中该索引的副本与其记录摘要保持历史原样;本 successor 的冻结以修正后的索引字节为准。

## 审阅材料覆盖边界(如实声明)

本索引自 r52 起用于弥补"冻结材料仅收 docs/*.md、候选三件套不在 manifest 材料清单"的覆盖边界。r52–r54 各版索引均存在同样的解析约定问题:条目路径必须相对其批次 Directory 头可解析才构成有效的审核入口指针。r55 起四批 88 条全部满足该约定;任何后续批次入索引时必须同样逐条解析验证。

## 复用声明与验证

- wheel `scirel-0.1.0.dev27-py3-none-any.whl` SHA-256 `7768b32bbc95bb0b36604bde6d89fd0543deaf656d906d1f2b765f6ce7b00e03` 与 catalog `complete: 90/90` root `sha256:2399fdbcae4fc8c7e6b0147d964548d3e1556a4803317c21401194e05b99d344` **逐字节复用 r54**:r55 只改索引 Markdown 的 36 行路径文字,wheel 仅打包 `src/scirel`(逐字节未变),catalog 输入未变;freeze 的 wheel==committed-source 校验照常执行。
- 本轮执行的验证仅为索引逐条存在性 + SHA-256 复算(两次:修正前 52/36/0,修正后 88/0/0),无科学测试运行,无既有断言变化。
- 不宣称:科学增量(r55 无)、合格 L1 消费、专家认可、可信晋级或公开发行。许可证 `pending-human-decision`;无可信基线,首次专家审核覆盖全部 90 项资产。
