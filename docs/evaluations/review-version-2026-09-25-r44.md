# SciRel review_scope 归属 fail-open 修复 r44

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根仍为空,KN1DPy 保存包仅为 provisional 历史对照。本版是 r43(`6ac636672be776c4aa5025bf0fdcbee7b4e3aeb9`,快照 `build/verification/review-2026-09-25-r43-review-scope-export-attribution`)的 successor;r43 快照**原样保留,但其纯导出归属已证实存在 fail-open,不能作为可靠增量审核工具使用**,见下。

## 缺陷(监控方只读复核,两条可复现反例)

r43 的 `_attributed_export_assets` 以"本地名 → 模块"字典建模导出面,并把全部 ImportFrom 从残差 AST 中剥离,导致两类静默漏报——别名重绑定完全不可见,函数在应当 fail closed 时返回空集合(即"无受影响资产"):

1. `from .a import old as x` → `from .a import new as x`(`by_callable` 按 `scirel.collisions.a.x` 映射):`x` 的实际绑定已改变,旧实现返回 `set()`。
2. `from os import path as x` → `from os import sep as x`(非 `scirel` 导入,`by_callable` 为空):旧实现同样返回 `set()`。

自查发现同类漏报还包括:**重复本地别名**(`from .a import old as x` 与 `from .a import new as x` 并存时字典去重掩盖新增)与**导入重排**(集合相等即放行,而导入顺序具有可观察的副作用语义)。

## 最小保守修复

导出面改按有序 `(module, symbol, local_name)` 三元组建模,非 `scirel` 导入同样记录绑定符号。归属要求:残差 AST 一致;非 `scirel` 导入(含绑定符号)不变;`__all__` 有无不一致的直接 fail closed;导入与 `__all__` 的顺序只允许增删、不允许重排(过滤增删后的有序序列必须相等);任一本地名重复绑定直接不可解析。新增/移除的**符号**(而非本地别名)经该版本自身导入解析到候选快照资产 callable——别名重绑定若新旧符号都可映射,则前后受影响资产都纳入;否则 fail closed。不试图硬解任意别名语义。

失败回归先行:5 项新回归先失败后通过——上述两条 monitor 反例判 `None`、重复别名判 `None`、导入重排判 `None`、以及双符号均可映射时返回前后两个资产的正例。`tests/test_review_scope.py` **31 passed**(26 既有 + 5 新)。

## 历史比较复验(修复后逻辑,真实 `git show/diff`)

- **r40→r41**:建议集合仍为 **3 项**(新增 Maxwellian 资产 + 两个 momentum 资产,其直接测试文件在 r41 确实被改),未解析 **0**,与 r43 记录一致——r41 的导出变更确为纯增,修复不影响该结论。
- **r41→r42**:**1 项**(+68 机械)、未解析 0,不变。
- 两个数字仍只描述快照间工程差异;无可信基线,首次专家审核仍覆盖全部 69 项;本工具不构成科学批准。

## 验证证据与复用声明

- 受影响门禁精确选择 `tests/test_review_scope.py`,**31 passed**;未重跑全仓。`942 passed、46 skipped` 与安装态 `101 passed` 属 r42 轮 `813c45f` 运行代码的证据;此后各提交只改 `docs/` 与 `scripts/`(不入 wheel),科学证据按未变代码复用。
- dev20 wheel(SHA-256 `0e85f236526b6b664d44a177b7a0a42f87d52613f2024e73d10c6eceecf9aa11`)与 catalog(`complete: 69/69`,root `sha256:702b1e9635ae1bddbac397e133b588d6182599405a3d9c2a103b149b850b4294`)字节复用;freeze 校验 wheel 模块与本提交 `src/scirel` 一致。

## 边界

r43 快照的归属结论(含其记录的历史比较数字)凡涉及别名/重排/重复别名情形的保证一律作废,以本版为准;其历史比较数字因实际导出变更确为纯增而未受影响。本工具仍是只读差异报告,AST 级归属不证明被归属资产的科学合同可免于专家阅读,也不验证基线认可、科学等价或发布资格。合格 L1 根仍为空;来源许可证、可信晋级与公开发行未完成。
