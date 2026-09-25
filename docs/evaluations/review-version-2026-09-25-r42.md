# SciRel KN1DPy Maxwellian 速率平均 successor r42

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。当前合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)为空,本轮未消费任何合格 L1 输入。r41 快照(`build/review-version-2026-09-25-r41-kn1dpy-maxwellian-rate`,commit `c71c6a5`)原样保留,不改写;本版是其 successor。

## 相对 r41 的差异(监控方只读复核三项发现的修复)

科学内容增量仍只有一项新增资产 `scirel.collisions.maxwellian-relative-speed-rate-average`(与 r41 相同的关系、公式与合同),本轮变化是三项修复与工程绑定:

1. **文本更正**:exact document 的溢出见证误印为 `1e-305`,实际示例与测试使用 `1e305`;正本与候选副本全部更正,无剩余 `1e-305`。
2. **回调顺序修复(第三项有据修复)**:失败回归先复现——极端但有限的粒子能量(`1e308` eV 使 `2eE/(m·amu)` 溢出)令采样碰撞能量数组为 inf/NaN,保存实现和 r41 都在检查前把它交给调用方截面回调;现在在调用回调前按公共失败合同抛 `ValueError`,记录型回调观察不到任何值,普通有限输入数值不变。
3. **自包含审阅材料**:r41 仅附本轮整合记录一份;本快照自包含 r40 仍有效的背景材料(领域草稿 `docs/domains/flux-coordinate-sampling.md`、P4 约定记录 `docs/evaluations/p4-flux-convention-development-2026-09-25.md`、r40 审核说明、来源覆盖记录 `docs/evaluations/review-provenance-coverage-2026-09-25.md`)、本轮候选审查文档(整合记录)与 r41 审核说明(作为其确切版本的历史记录)。

另:内部版本 `0.1.0.dev19` → `0.1.0.dev20` 并重建 wheel/catalog;其余 68 份 exact document 仅机械更新版本号,不产生新的科学证据。

## 审阅范围的如实说明

- **内容增量**:相对 r41 只有一份 exact document 的合同文案/文本更正、一处运行时检查(仅影响原本会溢出的极端输入)与其回归、机械版本更新;相对 r40 是一项新增资产。
- **保守审阅范围**:`review_scope.py` 把 `src/scirel/__init__.py` 等根/共享导出列为无法归属到单一资产的未解析源码路径,因此对 r40→r41、r41→r42 的开发比较都保守建议复审全部当前资产。
- **首次审核基线**:无可信版本,首次专家审核覆盖**全部 69 项公共资产**及其反向依赖,不能因为内容增量只有一项而缩减;上述三句话不得互相替代。

## 验证证据

- 失败回归先行:新回调顺序测试先失败(回调先被调用),修复后通过;直接测试 **45 passed**,历史复放 **3 passed**。
- `pwsh ./scripts/check.ps1 -Mode affected`(版本变更选全套):**942 passed, 46 skipped**。
- 69 份 exact document 源码态运行时/示例校验通过;安装态(独立 venv,`--no-index --no-deps` 安装 dev20 wheel,`python -I`)69/69 通过(`runtime_origin: installed`),安装态直接/复放/相邻算子测试 **101 passed**(45+3+21+32,含安装态回调顺序见证)。
- 内部 wheel `scirel-0.1.0.dev20-py3-none-any.whl`,SHA-256 `0e85f236526b6b664d44a177b7a0a42f87d52613f2024e73d10c6eceecf9aa11`;开发 catalog `complete: 69/69`,root digest `sha256:702b1e9635ae1bddbac397e133b588d6182599405a3d9c2a103b149b850b4294`。确切绑定见快照 manifest 与 `test-evidence.md`。

## 边界

venv 复用开发机科学依赖,不证明全依赖干净离线 wheelhouse 重装。历史复放仍是 SHA-256 绑定的有界历史开发证据:KN1DPy 严格 D1 资格已撤回,保存包属 `D1待重审历史产物`。测试通过、文档校验、构建与冻结都不构成科学认可;专家需决定新资产身份、三处修复、粒子质量碰撞能量约定、单节点图子并处置与来源证据边界。许可证状态均为 `pending-human-decision`。
