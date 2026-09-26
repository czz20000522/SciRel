# SciRel KN1DPy convergence/accumulation family r64

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r63(`10e1ee10239d9b4682182b89171a6984d97c9513`,快照 `build/verification/review-2026-09-27-r63-transport-v11`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:四项新 operator(收敛/累计家族)

1. `scirel.kinetic.neutral-generation-stopping`(`evaluate_neutral_generation_stopping`;源锚 `KN1DPy/kinetic_h.py:1278-1305`;保存 SHA-256 `dd110cbd…89cc3`):Δn = max(gen)/max(acc),truncate 和 seed_relative 路径,返回 3 元组 (delta, done, reason)。
2. `scirel.kinetic.generation-accumulation-update`(`update_neutral_generation_accumulation`;源锚 `KN1DPy/kinetic_h.py:1240-1276`;保存 SHA-256 `77eca995…e4f80`):state 为 required positional 参数;first call 从 None 创建,二次调用累加。
3. `scirel.kinetic.outer-seed-convergence`(`evaluate_neutral_outer_seed_convergence`;源锚 `KN1DPy/kinetic_h.py:1090-1115`;保存 SHA-256 `25f4918f…e9e03`):seed_error = max(abs(diff))/max(curr),reentry 阈值 = 10*truncate,返回 mapping(seed_error/reentry_threshold/should_reiterate/reason)。
4. `scirel.kinetic.kn1d-outer-convergence`(`evaluate_kn1d_outer_convergence`;源锚 `KN1DPy/kn1d.py:493-511`;保存 SHA-256 `3a5913b2…3dbbe2`):reentry 阈值 = truncate(非 10*),返回 mapping。

保存实现逐位复现;无修复。

## 预审修正(r64)

- **ratio-of-max vs per-node 注释**:从 "900/100=9 per-node" 修正为 "900/200=4.5 ratio-of-max";增加判别性回归(prev=[300,200] → seed_error=1.0,应不重入,而 per-node 会错误地返回 True)。
- **stopping 返回类型**:exact doc 从 mapping 更正为 3-tuple (delta, done, reason)。
- **accumulation state 参数**:从 optional 更正为 required positional。
- **所有示例**:替换为真实计算值,不再仅检查 docstring 存在。

## 变更清单

- 新增 4 个模块 + 导出;新增 4 份 exact document + 其余 116 份机械提升;`dev37` → `dev38`。
- 新增 2 个测试文件(`test_convergence_accumulation.py` 8 direct + `test_convergence_accumulation_l1.py` 5 replay)。
- 新增候选文档 `review_candidates/2026-09-27-transport-step/review-r64.md`。
- 账本与 _validation/_composition 字节零变化。

## 科学证据

- 双臂复放(SHA-256 绑定):所有 4 个算子逐位一致;拒绝行为双臂一致。
- 独立 oracle:ratio-of-max 公式、累加总量、判别性回归。

## 验证(全部 pwsh 7.6.6)

- 源码态全仓:**1410 passed, 43 skipped, 0 failed**(log `1410 passed, 43 skipped, 7 warnings in 215.43s`)。
- 120/120 文档源码态与安装态校验通过,含示例执行。
- 安装态全树:**1276 passed, 177 skipped, 0 failed**(log `1276 passed, 177 skipped, 7 warnings in 206.26s`)。
- catalog `build/catalog/r64`:`complete: 120/120`,root digest `sha256:9060cedfd46ba988125882757a078b6d7d965aff87fe79eb191f1dc50a17ae92`。
- 内部 wheel `scirel-0.1.0.dev38-py3-none-any.whl`,SHA-256 见 manifest。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行。
- 继续缓付:SIG 矩阵、分子 sigv 表、Franck-Condon 源、平移 Maxwellian 矩补偿、壁面源序列。
- 许可证状态均为 `pending-human-decision`。
