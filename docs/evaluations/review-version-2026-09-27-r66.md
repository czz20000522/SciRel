# SciRel KN1DPy collision frequency contraction family r66

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r65(`228a2d6fc936b425574c0d837dbfa4a3ae1b9759`,快照 `build/verification/review-2026-09-26-r65-terminal-molecular-v6`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

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

- 12 项测试(7 直接 + 5 环境 gating 复放):非对称 SIG、互异分布、one-hot SIG[5,3]=1 + Fortran-order 标号 fH 的载子映射见证(C-order 会映射不同位置),两个 `ni_correct` 分支,拒绝行为与保存臂逐位一致。
- `SIG_H_H` 在预审中补上缺失的对称 asarray/shape 校验。

## 相对 r65 的增量

- r65: terminal molecular diagnostics family(6 项),126 资产 dev39
- r66: collision frequency contraction family(2 项),128 资产 dev40
- 版本 `0.1.0.dev39` → `0.1.0.dev40`

## 验证(全部记录于 `build/test-evidence-r66.md`)

- 源码态全仓:**1436 passed, 43 skipped, 0 failed**(`SCIREL_KN1DPY_REVIEW_ROOT` 门控下复放激活;r65: 1424,+12)
- 128/128 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树:见证据文件
- catalog `build/catalog/r66`:`complete: 128/128`,root digest `sha256:73473c7a6641d29d7cfc6769d995d2c650eb5071faea7bcb00d33dffa6c474d3`
- 内部 wheel `scirel-0.1.0.dev40-py3-none-any.whl`,SHA-256 `be8e86b95de14c65e8e7035f253507f065c576b0ee74ea13bdce68ebfac705f5`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:SIG 矩阵装配、分子 sigv 表、N4-3/N3-4 Omega 下游聚合、外部原子物理参考(`validation_oracle_gap`)
- 弹性族负元与负密度的物理可接受性为开放专家问题,不是运行时门禁
- 许可证状态均为 `pending-human-decision`
