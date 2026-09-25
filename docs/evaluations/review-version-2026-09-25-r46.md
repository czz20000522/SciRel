# SciRel KN1DPy 速度空间制备族整合 r46

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)本轮开始与结束均复核为空,未消费任何合格 L1 输入。本版是 r45(`4bae43e00fa774ca25be6864e1b562739f21165d`,快照 `build/verification/review-2026-09-25-r45-clean-install`)的 successor;既有快照原样保留。

## 科学增量(两项新增资产,KN1DPy N1 速度空间制备族)

按科学语义从 KN1DPy 保存包(D1待重审历史产物,provisional)挑选与已整合 Maxwellian 速率平均直接组合的下一组独立关系:网格制备与分布种子。未发布候选池(52 个 Pleiades 单元及附加快照)无速度网格制备类资产;`热速度标度换算` 保存叶经审查**不立项**——其闭式 `sqrt(2eT/(m·amu))` 已作为种子资产的 `thermal_speed_m_s` 返回值与 Maxwellian 模块的已文档化常数存在,无超出该闭式的独立合同,处置记录为重叠/被吸收。

1. **`scirel.kinetic.cylindrical-velocity-quadrature`**(operator,`make_cylindrical_velocity_quadrature`):源锚 `KN1DPy/make_dvr_dvx.py:20-123`(实现文件 SHA-256 `0a52064747e92b223bdc1c6f78ccdd8bc63a696edc64a7b9c903a6b0515fa0a6`)。由严格递增的归一化 `vr`/`vx` 网格构造 ghost 扩展半格面、环形径向测度、`(nvr,nvx)` 圆柱体积(即下游 `cylindrical_volume` 端口)、ghosted 有限体积系数、速度平方与 ±vx 索引范围,共 18 个输出字段。有据修复一处:非有限网格点按参数名拒绝(保存实现静默传播 NaN,其文档却声明 fail-closed)。
2. **`scirel.kinetic.shifted-maxwellian-seed`**(operator,`build_shifted_maxwellian_seed`):源锚 `KN1DPy/create_shifted_maxwellian_include.py:58-76`(实现文件 SHA-256 `c495a86822c02dbb4bd84fe11f5cffb6093a85906be3dae66773d2e334641051`)。补偿前归一化指数种子:逐 shift 温度、分子数因子(`molecule_count` ∈ {1,2})、严格内部 `-80` clamp(argument=0 的节点与远尾同样取 floor,exponent 输出保留原值)、体积加权归一化(`Σ volume·distribution = 1` 每 shift)。保存实现已检查输入有限性,无此类修复。

两份 exact document 如实记录模型条件、ghost-face/strict-clamp 约定、常数冻结、证据上限与 provisional 来源边界。

## 科学证据

- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,实现文件 SHA-256 绑定):quadrature 在两个网格(均匀 2×4、非均匀 3×5)上逐字段复现保存实现(rtol 1e-15),含 NaN 修复差分见证;seed 在单/双分子 holdout 上复现 distribution/exponent/thermal_speed(rtol 1e-15)。9 passed。
- **独立 oracle**:quadrature 以手算预言(不同网格)验证环形测度(如 `[π, 3π]`)、ghost 面、体积、速度平方与符号索引,及盒分割闭合 `Σ volume = π·r_ghost²·Δvx_ghost`;seed 以逐 shift 独立 loop 公式对比分布/指数(rtol 1e-15)、远 shift 均匀极限(floor 后归一化 = 1/(nvr·nvx))、严格内部 clamp 精确见证、分子数指数翻倍。
- **组合链**:quadrature → volume → seed(加权归一化 = 1)→ 同一网格快照喂 Maxwellian 速率平均(有限正速率),覆盖文档声明的 N1→N2 组合。
- 保存包自身证据(包级 oracle 4 passed/3 passed、ledger `ACCEPT_OPERATOR`、N62/N81/N82 evidence-only 独立审计)作为有界历史对照引用。

## 验证

- 失败回归先行(ImportError);直接测试 **49 passed**;复放 **9 passed**。
- `check.ps1 -Mode affected`(版本变更选全套):**1005 passed, 52 skipped**;计数断言 69→71、包级 `__all__` 更新,无既有数值断言弱化。
- 71/71 文档源码态与安装态(干净 venv,`python -I`)校验通过;干净离线安装(`include-system-site-packages=false`,`--no-index --find-links build/dependency-wheelhouse`,wheelhouse 与 r31 记录逐哈希一致):source-free 科学/组合/公共入口套件 **732 passed, 43 skipped**(历史 L1 根已配置,KN1DPy 复放真实运行)。
- 内部 wheel `scirel-0.1.0.dev21-py3-none-any.whl`,SHA-256 `c5f360d96f4f418af52cb98c076bdd9ada377ed88e18c20461d381651c54c607`;开发 catalog `complete: 71/71`,root digest `sha256:54c3280ead435c4c15d2e91c75a933b0ec64deed9785f98bd3bca45979349865`。

## 边界与待决

- 不宣称:合格 L1 消费、ghost-face 约定对任意下游 scheme 的适用性、种子未经补偿即物理充分、调用方网格的物理有效性、专家认可、可信晋级或公开发行。
- 保存链中补偿后分布(`平移Maxwellian离散矩补偿`)与本轮其他叶节点(自适应网格、跨网格插值、电荷交换速率系数等)保留未决,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 71 项资产。
