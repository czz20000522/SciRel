# SciRel KN1DPy Omega aggregation family r68

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r67(`3554469`,`0.1.0.dev41`,130 资产,快照 `build/verification/review-2026-09-27-r67-collision-matrix-assembly-v1`)的 successor;既有快照原样保留。合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均复核为空,未消费任何合格 L1 输入。

## 性质:两项新 operator(Omega 弹性频率聚合族)

来源为保存 KN1DPy 包(`D1待重审历史产物/KN1DPy-631d0bf1`,严格 D1 资格已撤回,provisional),实现文件按 SHA-256 钉定:

1. `scirel.kinetic.atomic-omega-aggregation`(`assemble_atomic_hydrogen_omega_frequencies`,kinetic_h.py:1116-1188):逐空间单元把原子弹性 Alpha 频率与分支时刻 `SIG_H_H @ F(fH)` 内联再收缩聚合为 `Omega_H_P`、`Omega_H_H2`、`Omega_H_H`、`Omega_EL` 及 `VxH`、`Wperp_paraH`(各 `(nx,)`)。
2. `scirel.kinetic.molecular-omega-aggregation`(`assemble_molecular_hydrogen_omega_frequencies`,kinetic_h2.py:1232-1296):分子侧同构聚合,消费原子流 `VxH` 作为 H2-H 通道漂移目标,返回 `VxH2`、`Omega_H2_P`、`Omega_H2_H`、`Omega_H2_H2`、`Omega_EL`、`Wperp_paraH2`。

本批闭合基线 `elastic-frequency-channels`/`elastic-regeneration-aggregation` 资产声明缺失的 "species-pair Omega evaluations" 上游,并消费 r66/r67 的 Alpha 收缩与 SIG 装配输出——两头依赖均已就位。

## 保留的源语义与登记的分歧

- **分支选择不对称逐字保留**:原子 Wperp 用 `sum(MH_H_sum) <= 0`(零取直接 vr2 投影),分子用 `< 0`(零取累计矩路径);判别 oracle 测试把两臂钉在相反分支。
- **源精确除法次序保留**:分子 `Omega_H2_P` 分母在求和外(kinetic_h2.py:1257),`Omega_H2_H` 分母在求和内(:1270);oracle 按两种次序分别复算,复放逐位一致。
- **登记的 fail-closed 加固(与保存臂静默行为的有意分歧)**:非正密度且启用任一弹性通道 → `ValueError`(保存臂静默跳过整块返回零);`Vth`/`DeltaVx_tol`/`Wpp_tol` 必须有限正标量(保存臂不校验——零 `Vth` 或绕过 `tol<=0` 检查的 NaN 会流入除法);全部输出终检有限(保存臂会静默返回 NaN/Inf,包括源记录的合法输入隐患:legacy `sign(0)=0` 使漂移差恰为零的对称载子上钳制分母为 0 → NaN)。
- **逐字保留**:legacy 符号函数(源注 "replace with np.sign",归一化为带零值保护形态是开放专家问题)、`max(Omega_*, 0)` 零钳制(输出恒非负,与带符号 Alpha/SIG 族不同)、源硬编码 `DeltaVx_tol=0.01`/`Wpp_tol=0.001`、分支时刻 SIG 再收缩(C-order 预分配缓冲布局在内)、`Wperp_paraH`/`Wperp_paraH2` 不 clamp 如实返回。

## 科学边界

- Omega 族输出恒非负(源零钳制);`Wperp_paraH` 如实带符号返回,其符号驱动 H-H/H2-H2 通道方向。
- 无状态确定性映射:不读 `KH.Internal`/`KH2.Internal` 缓存、不写回调用方状态。
- 原子臂 Wperp 累计矩分支(`MH_H_sum > 0`)是源 `#NOTE Not Tested Yet` 区域:端口逐字实现并被 oracle 分支测试复现,但源执行证据只覆盖直接投影分支。

## 组合证据

- 24 项测试(19 直接 + 5 环境 gating 复放):独立闭式归约 oracle(保存包 1e-12/1e-9 预算)覆盖每臂全部六个输出、两分支路径、求和内外除法次序、F-order vs C-order 载子判别、零钳制、`Omega_EL` 精确和、开关门控、输入只读、登记加固与非有限输出终检(极端 `Vth` 溢出探针)。fixture 随机源每次调用重新播种,单 affected 用例与整文件运行的载子逐位一致。
- 复放:SHA-256 钉定保存臂,两臂在两个分支载子上全部六个输出逐位一致;拒绝协议一致仅限于保存臂自身也抛错的边界。

## 相对 r67 的增量

- r67: collision-matrix assembly family(2 项),130 资产 dev41
- r68: Omega aggregation family(2 项),132 资产 dev42
- 版本 `0.1.0.dev41` → `0.1.0.dev42`
- 每臂声明 2 项集成依赖(r66 收缩、r67 装配);其他资产合同不变(仅机械版本号 bump)

## 验证(全部记录于 `build/test-evidence-r68.md`)

- 源码态全仓(复放激活):**1486 passed, 43 skipped, 0 failed**(r67 全树 1462,+24)
- 132/132 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r68-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1332 passed, 197 skipped, 0 failed**(r67: 1313/192)
- catalog `build/catalog/r68`:`complete: 132/132`,root digest `sha256:d622280dce145ae53d1e10eac748a9e6697779db038ee1dc6c06be66408037f9`
- 内部 wheel `scirel-0.1.0.dev42-py3-none-any.whl`,SHA-256 `28271440e006d9ee6f460fdd3153824cc42338634bdca7b22a082d309ad50a55`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:分子 sigv 反应速率表(需 10 叶速率算子的图编排)、`SIG_D2_*` 其他碰撞族、外部原子物理参考(`validation_oracle_gap`)
- 开放专家问题:legacy sign 是否归一化为带零值保护的 `np.sign` 形态;`DeltaVx_tol`/`Wpp_tol` 钳制值的物理合理性;原子臂 Wperp 累计矩分支的物理验证
- 许可证状态均为 `pending-human-decision`
