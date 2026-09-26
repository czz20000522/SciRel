# SciRel KN1DPy collision frequency contraction family r66

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r65(`228a2d6fc936b425574c0d837dbfa4a3ae1b9759`,快照 `build/verification/review-2026-09-26-r65-terminal-molecular-v6`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

当前待审快照为 v3:`build/verification/review-2026-09-27-r66-alpha-contraction-v3`。v1(`review-2026-09-27-r66-alpha-contraction-v1`,commit `33653d5`)与 v2(commit `09096b3`)原样保留、不可改写,但不再是最终待审交付。v1 的候选 review.md 把 r65 冻结路径误写成 r64-v3 快照;其证据表述把仅覆盖原子 H_H 族的 one-hot F-order 载子见证扩大成两项算子全部族的独立重算;109 项 review materials 未含候选三件套。v2 修正以上三点并直接收录候选三件套,但其冻结脚本的材料校验把 `review_candidates/` 下任意 tracked 文件都放行,超出三件套的必要面;v3 收紧校验为确切结构并补回归测试(材料集合在两种规则下完全相同,均为 7 文件)。版本与科学行为在 v1→v2→v3 全程不变(`0.1.0.dev40`,128 资产)。

## 性质:两项新 operator(碰撞频率收缩家族)

来源为保存 KN1DPy 包(`D1待重审历史产物/KN1DPy-631d0bf1`,严格 D1 资格已撤回,provisional),实现文件按 SHA-256 钉定:

1. `scirel.kinetic.atomic-alpha-contraction`(`contract_atomic_hydrogen_alpha_frequencies`):原子四族 SIG 矩阵(CX、H-H、H-H2、H-P)逐空间单元 Fortran-order 收缩为四个 `(nvr,nvx,nx)` Alpha 频率场(`Alpha_CX`、`Alpha_H_H2`、`Alpha_H_P`、`Alpha_H_H`);原子臂逐字移植,无修复。
2. `scirel.kinetic.molecular-alpha-contraction`(`contract_molecular_hydrogen_alpha_frequencies`):分子三族 SIG 矩阵(CX、H2-H、H2-P)收缩为三个 Alpha 频率场(`Alpha_CX`、`Alpha_H2_H`、`Alpha_H2_P`);`ni_correct` 分支选择源定义的 `ni = max(n - nHP, 0)` 密度修正。

## 已登记的源缺陷与修复(分子臂)

原源 `kinetic_h2.py:1204` 写 `Alpha_CX[:,:,k] = SIG_CX @ Work` 缺少 Fortran-order 恢复 reshape,在 canonical `nvr*nvx` 载子上崩溃。保存 formal 实现已带最小 `.reshape(..., order='F')` 修复;本移植逐位复现修复后的保存实现,原始缺陷在不可变源中保持原样登记,留待专家审阅。文档不声称分子臂"原样移植无修复"。

## 科学边界

- 负密度/零密度运行时不拒绝:收缩按给定有限值执行;`ni_correct` 的 `max(n-nHP,0)` 是源定义密度修正,不是正密度门禁。
- 弹性 SIG 族带符号因子(`vx_vx`/`vr2_vx2`)传播的有界负元如实复现、不 clamp;物理可接受性留待专家。
- SIG 矩阵为上游装配产物(截面 × 相对速度 × 速度空间权重,source-discrete),本算子只收缩,不做隐式单位换算;Alpha 输出按频率端口声明 `s^-1`。

## 组合证据

- 12 项测试(7 直接 + 5 环境 gating 复放)。独立一阶重算见证仅一项:原子臂 one-hot `SIG[5,3]=1` + Fortran-order 标号 fH 的载子映射测试(C-order 会映射不同位置),只钉定 `Alpha_H_H` 族的 flatten/restore 顺序;原子 CX/H-H2/H-P 族与分子臂无等价独立重算,其余直接测试只建立键/形状、fail-closed 拒绝与 `ni_correct` 分支判别。跨臂科学保证其余来自 SHA-256 钉定的保存 formal 实现逐位复放;外部原子物理参考缺口(`validation_oracle_gap`)保留。
- `SIG_H_H` 在预审中补上缺失的对称 asarray/shape 校验。

## 相对 r65 的增量

- r65: terminal molecular diagnostics family(6 项),126 资产 dev39
- r66: collision frequency contraction family(2 项),128 资产 dev40
- 版本 `0.1.0.dev39` → `0.1.0.dev40`

## v2/v3 预审修正(科学行为与版本不变)

- `review_candidates/2026-09-27-alpha-contraction/review.md`:r65 冻结路径改为 `build/verification/review-2026-09-26-r65-terminal-molecular-v6`(commit `228a2d6`);Evidence 段收窄为"实际直接测试 + SHA-pinned 保存 formal 历史复放",保留外部物理缺口。
- 两份 exact doc(`catalog/examples` 与 proposal 副本字节一致):`evidence_ceiling` 同步收窄,不宣称全族独立重算。
- `test_alpha_contraction.py` 注释修正:nvr=3 时 F-order flat 3 为 `(0,1)` 而非 `(1,1)`(含 `fH_labelled[0,1,0]`),断言未动。
- `scripts/freeze_review_version.py`:review materials 在 tracked `docs/*.md` 之外,仅接受确切候选结构——`review_candidates/<batch>/review.md` 与 `review_candidates/<batch>/proposal/*.py|*.json`;`tests/test_review_version_freeze.py` 补接受 7 类当前文件与拒绝其他候选路径/扩展名的回归;clean Git、仓内路径、重复拒绝、复制后摘要复核不变。v3 快照直接收录候选三件套 7 文件(`review.md`、两份代码、两份测试、两份 exact doc)。
- 材料/证据同步:候选材料索引 r66 批次摘要更新(脚本逐条核验 7/7 吻合;更旧批次的既有漂移不属于本批)。

## 验证(全部记录于 `build/test-evidence-r66.md`)

- 源码态受影响验证(复放激活,修正后字节):**1436 passed, 43 skipped, 0 failed**(`SCIREL_KN1DPY_REVIEW_ROOT` 指向保存 bundle;v1 全树 1436/43 复用仍有效,src 未变)
- 128/128 文档源码态校验通过,含示例执行(`runtime_origin: source`)
- 安装态 128/128 与全树回执沿用 v1(src 与 wheel 未变,摘要相同)
- catalog `build/catalog/r66-v2`:`complete: 128/128`,root digest `sha256:690006fbd78ed9f856b6841deb1a8f114d94e90bba4d2bae1c336243ba97a558`;v1 的 `build/catalog/r66`(root `sha256:73473c7a...`)原样保留
- 内部 wheel `scirel-0.1.0.dev40-py3-none-any.whl`,SHA-256 `be8e86b95de14c65e8e7035f253507f065c576b0ee74ea13bdce68ebfac705f5`(与 v1 相同,`src/scirel` 未变,直接复用 `build/wheel-r66/`)

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:SIG 矩阵装配、分子 sigv 表、N4-3/N3-4 Omega 下游聚合、外部原子物理参考(`validation_oracle_gap`)
- 弹性族负元与负密度的物理可接受性为开放专家问题,不是运行时门禁
- 许可证状态均为 `pending-human-decision`
