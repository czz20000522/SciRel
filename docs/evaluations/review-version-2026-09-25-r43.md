# SciRel review_scope 纯导出归属 r43

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根仍为空,KN1DPy 保存包仅为 provisional 历史对照。本版是 r42 v3(`4f55e48179bdd5c7828f88d9f6e7b580e3b8c70a`,快照 `build/verification/review-2026-09-25-r42-kn1dpy-maxwellian-rate-v3`)的 successor;r41、首份 r42、v2 原样保留。

## 工程增量(无科学行为变化)

`scripts/review_scope.py` 此前对 r40→r41 这类根/包 `__init__.py` 导出变更无法归属:选择器给 `public_exports` 分类但 `affected_assets` 为空,`_source_impact` 随即判未解析并把全部当前资产列入建议审阅集合——在已有可信基线后,一个单算子新增也会保守要求全库科学复审。本版为该缺口做最小修复:

- `_public_export_surface` 把一份 `__init__.py` 解析为导入表(相对导入按包解析为绝对 `scirel.*` 模块)、非 `scirel` 导入表、`__all__` 字面量与去掉导入/`__all__` 后的 AST 残差;语法错误、星号导入、动态 `__all__` 一律判不可解析。
- `_attributed_export_assets` 用 `git show` 取两份冻结提交的字节,仅当**残差 AST 完全一致、非 `scirel` 导入不变、且每个新增/移除的公共符号都经该版本自身导入解析到候选快照中的资产 callable** 时,把变更精确归属到这些资产;否则返回"不可归属",调用方维持原 fail-closed(路径列入 `unresolved_source_paths` 并扩大到全部资产)。纯 `__all__` 顺序调整、纯注释/空白差异归属为空集(公共面机器验证未变)。
- `_source_impact` 签名增加 baseline commit(仅 `review_scope` 一个调用方);首审模式与"无可信基线须覆盖全部资产"的规则未动。
- `docs/development-process.md` 补充该唯一精确归属例外与 fail-closed 边界的描述。

失败回归先行:9 项新测试先失败(归因函数不存在/签名不匹配)后通过——纯增/纯删/仅 `__all__` 成员变化三种归属,非导出改动、未映射符号、非 `scirel` 导入变化、星号导入四种 fail-closed,加两个端到端用例(纯导出变更把审阅集合缩到新增资产;非导出改动仍全库)。`tests/test_review_scope.py` 26 passed。

## 历史比较复验(新逻辑对既有冻结快照)

- **r40→r41**(候选 `c71c6a5`,守卫以 detached 等价的 HEAD 模拟通过;`git show/diff` 均为基于提交的真实读取;已断言工作树 catalog 的 69 个资产 ID 与候选快照一致):建议集合从 69 项缩为 **3 项**——新增的 `scirel.collisions.maxwellian-relative-speed-rate-average`,加上 `scirel.collisions.normalized-momentum` 与 `scirel.collisions.thermal-electron-momentum`(r41 确实修改了它们的直接测试文件 `test_momentum_scales.py`,属真实的证据触达)。`unresolved_source_paths` 从 2 降为 0,`runtime_requirements_changed` 为 False。
- **r41→r42**:建议集合 **1 项**(另 68 项机械版本更新)、未解析 0,与 v2/v3 审核说明的复跑结论一致。
- 这两个数字只描述快照间工程差异;无可信基线,首次专家审核仍覆盖全部 69 项资产,本工具改动不改变该规则,也不构成任何科学批准。

## 验证证据与复用声明

- 受影响门禁精确选择 `tests/test_review_scope.py`(脚本映射)与文档变更,**26 passed**;未因窄脚本改动重跑全仓。`942 passed、46 skipped` 与安装态 `101 passed` 属 r42 轮在 `813c45f` 运行代码上的证据;`813c45f → 0f4acb6 → 4f55e48 → 本提交` 只改 `docs/` 与 `scripts/review_scope.py`(不入 wheel),`src/scirel`、exact documents、测试断言未变,科学证据按未变代码复用。
- dev20 wheel(SHA-256 `0e85f236526b6b664d44a177b7a0a42f87d52613f2024e73d10c6eceecf9aa11`)与 catalog(`complete: 69/69`,root `sha256:702b1e9635ae1bddbac397e133b588d6182599405a3d9c2a103b149b850b4294`)字节复用;`scripts/` 不入 wheel,freeze 校验 wheel 模块与本提交 `src/scirel` 一致。

## 边界

本工具只产出只读的差异/影响报告,不验证比较快照是否获专家认可,不判定科学等价、证据充分或发布资格;AST 级归属是工程保守判断,不证明被归属资产的科学合同无需专家阅读。合格 L1 根仍空、来源许可证、可信晋级与公开发行未完成。
