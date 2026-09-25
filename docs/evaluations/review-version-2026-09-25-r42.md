# SciRel KN1DPy Maxwellian 速率平均 successor r42

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。当前合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)为空,本轮未消费任何合格 L1 输入。r41 快照(`build/verification/review-2026-09-25-r41-kn1dpy-maxwellian-rate`,commit `c71c6a5`)原样保留,不改写;本版是其 successor。

## 相对 r41 的差异(监控方只读复核三项发现的修复)

科学内容增量仍只有一项新增资产 `scirel.collisions.maxwellian-relative-speed-rate-average`(与 r41 相同的关系、公式与合同),r42 轮变化是三项修复与工程绑定:

1. **文本更正**:exact document 的溢出见证误印为 `1e-305`,实际示例与测试使用 `1e305`;正本与候选副本全部更正,无剩余 `1e-305`。
2. **回调顺序修复(第三项有据修复)**:失败回归先复现——极端但有限的粒子能量(`1e308` eV 使 `2eE/(m·amu)` 溢出)令采样碰撞能量数组为 inf/NaN,保存实现和 r41 都在检查前把它交给调用方截面回调;现在在调用回调前按公共失败合同抛 `ValueError`,记录型回调观察不到任何值,普通有限输入数值不变。
3. **审阅材料**:r41 仅附本轮整合记录一份;r42 轮逐步补齐至本版(v3)的 30 份,见下节,并如实区分现行背景与到期历史。

另:内部版本 `0.1.0.dev19` → `0.1.0.dev20` 并重建 wheel/catalog;其余 68 份 exact document 仅机械更新版本号,不产生新的科学证据。

## 审阅范围的如实说明

- **内容增量**:相对 r41 只有一份 exact document 的合同文案/文本更正、一处运行时检查(仅影响原本会溢出的极端输入)与其回归、机械版本更新;相对 r40 是一项新增资产。
- **保守审阅范围**:`review_scope.py` 对 r40→r41 的开发比较把根/包导出(`src/scirel/__init__.py`、`src/scirel/collisions/__init__.py`)列为无法归属到单一资产的未解析源码路径,并因此保守建议复审全部当前资产(本轮已在候选提交上 detached 复跑证实);r41→r42 的开发比较因导出未变,建议复审集合为 1 项(另 68 项为机械版本更新)、未解析路径 0。
- **首次审核基线**:无可信版本,首次专家审核覆盖**全部 69 项公共资产**及其反向依赖,不能因为内容增量只有一项或某个比较建议集合较小而缩减;以上三句话不得互相替代。

## 审阅材料(v3,30 份)与有效性区分

v2 仅附 6 份材料却称"自包含"首审入口,不成立。v3 携带 r39 首选快照(`build/review-version-20260925-e09d98c`)的全部 27 份背景材料,加 r40 审核说明与本轮整合记录、r41 审核说明,共 30 份,并按性质区分:

- **现行背景(描述当前合同/来源,11 份领域导航与草稿 + 2 份)**:`docs/domains/README.md` 与 10 份领域草稿、`docs/evaluations/review-provenance-coverage-2026-09-25.md`(覆盖既有 68 项的来源与有界证据;第 69 项由本轮整合记录说明)、`docs/evaluations/p4-flux-convention-development-2026-09-25.md`。
- **到期历史(绑定其确切版本,仍有效但不描述当前状态,17 份)**:4 份既有整合记录(bosch-hale、fluidbw-kinetic、planar-wavevector、plasma-dispersion)与 9 份 r28–r38 审核说明为各自版本的历史冻结与更正记录;r40、r41 审核说明与本轮整合记录是本候选的直接前史。这些记录不因后续 successor 被改写,其结论也不自动延伸到当前版本。

## 更正记录

- v2 更正(相对初稿):r41→r42 比较范围误写为保守建议全部资产,实为建议 1 项(另 68 项机械)、未解析 0;r40→r41 确因根/包导出未解析保守建议 69 项,均按 detached 复跑更正。
- v3 更正(相对 v2):其一,本说明与整合记录把 r41 快照路径误写为 `build/review-version-2026-09-25-r41-kn1dpy-maxwellian-rate`,实际为 `build/verification/review-2026-09-25-r41-kn1dpy-maxwellian-rate`;其二,v2 更正记录称首份 r42 冻结目录与本版"同 commit",实际首份 r42 绑定 `813c45f`、v2 绑定 `0f4acb6`,两份 wheel/catalog 字节相同仅因两者之间只改了 `docs/`;其三,v2 以 6 份材料自称覆盖 69 项的全库自包含首审入口,不成立,已由 30 份材料集与本节区分更正。首份 r42 目录与 v2 目录均原样保留、作废,本版(v3)为该说明唯一有效的冻结绑定与首选审阅入口。

## 验证证据

- 失败回归先行:新回调顺序测试先失败(回调先被调用),修复后通过;直接测试 **45 passed**,历史复放 **3 passed**。
- `pwsh ./scripts/check.ps1 -Mode affected`(版本变更选全套):**942 passed, 46 skipped**;69 份 exact document 源码态运行时/示例校验通过;安装态(独立 venv,`--no-index --no-deps` 安装 dev20 wheel,`python -I`)69/69 通过(`runtime_origin: installed`),安装态直接/复放/相邻算子测试 **101 passed**(45+3+21+32,含安装态回调顺序见证)。以上门禁与安装态证据在 commit `813c45f` 的运行代码上取得;`813c45f → 0f4acb6 → 本提交` 只改 `docs/evaluations/` 与 `docs/domains/` 无关文件之外的评估文档(见更正记录),`src/scirel`、测试与 exact documents 未变,证据按未变运行代码复用,本轮未重跑;freeze 校验 dev20 wheel 模块与本提交 `src/scirel` 逐模块一致。
- 内部 wheel `scirel-0.1.0.dev20-py3-none-any.whl`(构建于 `813c45f`,SHA-256 `0e85f236526b6b664d44a177b7a0a42f87d52613f2024e73d10c6eceecf9aa11`),catalog `complete: 69/69`(root digest `sha256:702b1e9635ae1bddbac397e133b588d6182599405a3d9c2a103b149b850b4294`)在本 successor 中字节复用;确切绑定见快照 manifest 与 `test-evidence.md`。

## 边界

venv 复用开发机科学依赖,不证明全依赖干净离线 wheelhouse 重装。历史复放仍是 SHA-256 绑定的有界历史开发证据:KN1DPy 严格 D1 资格已撤回,保存包属 `D1待重审历史产物`,本候选仅为 provisional 整合。测试通过、文档校验、构建与冻结都不构成科学认可;专家需决定新资产身份、三处修复、粒子质量碰撞能量约定、单节点图子并处置与来源证据边界。许可证状态均为 `pending-human-decision`。
