# SciRel FIDASIM fast-ion kinematics family r70

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r69(`33fa7db`,`0.1.0.dev43`,135 资产,快照 `build/verification/review-2026-09-27-r69-gseq-green-v2`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空,未消费任何合格 L1 输入。FIDASIM 保存包实际位于兄弟主仓库 checkout `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`(读取只,零写入),只支持 provisional 有界历史开发比较。

## 性质:两项新 operator(FIDASIM 快离子运动学)

1. `scirel.fusion.dd-neutron-emission-anisotropy`(`dd_neutron_kinematic_anisotropy`,源锚 fidasim.f90:10994-11078):Brown-Jarmie 冻结系数表插值 + 方向归一化,逐事件输出 D(d,n)3He 各向异性因子。
2. `scirel.fusion.first-order-larmor-correction`(`first_order_larmor_guiding_center_correction`,源锚 gyro_step):按源 FLR 0/1/2 阶把引导中心状态映射为粒子状态;order-2 消费调用方供给的 12 项柱坐标磁场态与旋转矩阵。

## 复用判断:DD 实验室能量不新增公共身份

保存包 `DD中子运动学能量` 与已集成资产 `scirel.fusion.dd-neutron-lab-energy` 是同一物理关系(同输入:两氘核速度+探测单位方向;同输出:keV;同非相对论闭式),集成资产还带登记修复(非正实验室能量回落 CM 能量而非源伪影)并声明恒为 1 的 `angular_weight` 字段——该字段不是科学能力。处置:**复用/来源映射**,不立第三个公共算子;保存包只在 provenance 链引用。两项新算子在 catalog 中均无等价物。

## 判重与登记的分歧

- **一般表顶域条件**:Brown-Jarmie 表顶 116.909 keV;声明域为 `0.5*scale*|v1-vrot|^2 < 116.909`,即 `|v1-vrot| < sqrt(2*116.909/scale)`;达到或超过表顶 fail-closed 拒绝(保存包自身 probe vrel=200、scale=0.01 得 ehalf=200 keV,即此类拒绝)。
- **源插值器 quirk 逐字保留**:1-D 插值器在非均匀能量表上使用第一间距作均匀网格;记录为源行为,不宣称为准确插值。
- **范数溢出有据收容(不扩大主张)**:极端中子速度使范数溢出,但角度代数自身的 fallback(`abs(k0*sinphi)<=1` 对 NaN 为假)强制 `costheta=0`,各向异性保持有限——极端 probe 实测结果为 1.0;末位非有限输出门作为兜底。这是记录的源行为,验证于极端探针。
- **FLR 输出门(登记加固)**:位置-半径相减在有限极值下可溢出(记录链:position 1e308、velocity -1e308、B 1e-8 → radius 约 -1.04e308 有限、相减 → +Inf);本移植对全部三个返回字段终检并拒绝,保存臂静默返回 Inf。
- **源窗口与轴奇点保留**:order-2 比例窗 `(0, 2)` 与柱轴未定义均为源 fail-closed,逐字保留;`flr_order` 严格 int 0/1/2,None 选择历史 `flr_enabled` 契约;三个 order-2 附加参数的 None 表示缺席(order 2 报错,order 0/1 不使用),不是 flr_enabled 选择器。

## 组合证据

- 10 项直接测试:保存包冻结前向 probe(rtol 1e-14)、横向旋转对称、域内随机正值性、一般表顶拒绝(含极端离子速度溢出进入该拒绝)、范数溢出收容、FLR order-0 恒等、order-1 精确叉积半径+垂直性+位移+历史契约、order-2 均匀场 scale 恰 1 与窗外拒绝、轴上未定义、缺态拒绝、记录的相减溢出链。fixture 每次调用重新播种。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要按"路径 → 资产 ID → 摘要"同行记录于 `build/test-evidence-r70.md`(参考记录,无自动漂移检测)。

## 相对 r69 的增量

- r69: GSEQ filament-coil Green family(3 项),135 资产 dev43
- r70: fast-ion kinematics family(2 项),137 资产 dev44
- 版本 `0.1.0.dev43` → `0.1.0.dev44`
- `docs/domains/fusion.md` 增补两关系与 DD 能量复用处置

## 验证(全部记录于 `build/test-evidence-r70.md`,所有子进程 returncode 已核)

- 源码态全仓(复放激活):**1508 passed, 43 skipped, 0 failed**,returncode 0(r69 全树 1498,+10)
- 137/137 文档源码态与安装态校验通过,含示例执行(`runtime_origin: installed`)
- 安装态全树(干净 venv `build/venv-r70-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps`):**1354 passed, 197 skipped, 0 failed**,returncode 0(r69: 1344/197)
- catalog `build/catalog/r70`:`complete: 137/137`,root digest `sha256:bce5623814d94469cf103b019db730c5c4f192a971bb415108c2697e7b0451f9`
- 内部 wheel `scirel-0.1.0.dev44-py3-none-any.whl`,SHA-256 `d72e89f26022018ae04957b5eb6daa1e8aafa3cd5a325df3dd343eb9969403f5`

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:NBI 出生采样/谱合成链、中子谱归约(MPI 门包非科学关系)、DT/D-He3 角分布、相对论运动学
- 开放专家问题:Brown-Jarmie 表的物理精度与适用域;FLR order-2 调用方磁态的几何一致性验证责任
- 许可证状态均为 `pending-human-decision`
