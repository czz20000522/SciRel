# SciRel KN1DPy mesh/seam family r61

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r60c(`913accd74bab1b822d47b84e5a4694c63014c3bf`,快照 `build/verification/review-2026-09-26-r60c-neutral-moments`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:两项新 operator(网格构造 + 跨网格接缝)

1. `scirel.kinetic.adaptive-neutral-velocity-mesh`
   (`create_adaptive_neutral_velocity_mesh`;源锚
   `KN1DPy/create_vr_vx_mesh.py:16-56`):对称圆柱速度网格——近均匀温度
   (spread ≤ 0.1·Tmax)走 vmax=3.5 均匀分支,否则走保存的二次拉伸;请求的
   正能量作为精确节点插入且保持轴向对称;Tnorm = 所选总体均值。保存常数
   (3.5、0.1 阈值)逐字保留。
2. `scirel.kinetic.cross-mesh-scalar-interpolation`
   (`interpolate_scalar_across_mesh`;源锚 `KN1DPy/interp_scalarx.py`,
   消费点 `kn1d.py:485-486、521` 的 H↔H2 接缝):1-D 标量 profile 的跨网格
   线性插值;mesh_a 范围外的 mesh_b 节点严格置零(保存的相空间合同);
   do_warn 模式仅产生保存的边界警告,不改输出。

最小依赖闭包理由:网格构造是已整合全部输运叶的上游;接缝是此前缓付的
H↔H2 跨网格 handoff 的先决条件。更大的跨网格分布插值(411 行)与按物种
源生产装配依赖更长的上游链,继续缓付。

## 声明的适配(一项,开放专家问题)

保存 callable 的 `requested_energy_ev` 缺省为空 tuple;JSON 文档无法表达
tuple,本集成改为 `None` 缺省并按等价处理(两种缺省的网格结果不变),
已在 exact document assumptions 中记录,交专家审定。

## 科学证据

- 双臂复放:两个保存实现文件逐一 SHA-256 绑定;网格在均匀/拉伸/插能量/
  加 cap/多温度五种情形、插值在 4 组随机网格上逐位一致;拒绝路径
  (nv=0、cap 掏空总体、全越界 mesh_b、fa/xa 失配)双臂一致。
- 独立 oracle:均匀 3.5 网格公式、二次拉伸公式、对称性、闭式线性 profile、
  越界零填充、仿射不变性。
- 逐文件测试计数(`pytest --collect-only`):7 直接 + 3 复放 = 10。

## 验证(全部 pwsh 7.6.6)

- 112/112 文档源码态与安装态(`--installed-runtime`)校验通过,含示例执行。
- 干净 venv `build/venv-r61-clean`(本地 wheelhouse,`--no-index
  --no-deps --force-reinstall`,隔离探针 under-prefix):r45 子集与全树计数
  见 test-evidence-r61.md。
- catalog `build/catalog/r61`:`complete: 112/112`,root digest 见
  test-evidence-r61.md。
- 内部 wheel `scirel-0.1.0.dev33-py3-none-any.whl`,SHA-256 见
  test-evidence-r61.md。

## r59→r60 计数澄清(上版证据勘误,原 r60c 快照不改写)

r60c 证据中"+51"算式不准确:axisymmetric 测试文件在预审第二轮补入
`test_nonfinite_scalar_inputs_fail_closed` 后由 6 变 7,实际增量为
11+7+14+8+12 = **52**,1301 + 52 = 1353 与全树实测一致。本版证据按 +52 记载。

## 边界与待决

- 不宣称:合格 L1 消费、对外部物理参考的正确性、专家认可、可信晋级、公开发行。
- 继续缓付:跨网格分布插值、按物种源生产装配、BoltzmannRHS、SIG 矩阵、
  分子 sigv 表、平移 Maxwellian 矩补偿、Franck-Condon 源、壁面源序列。
- 许可证状态均为 `pending-human-decision`。
