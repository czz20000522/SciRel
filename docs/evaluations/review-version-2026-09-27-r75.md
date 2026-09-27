# SciRel FIDASIM NBI 源面几何与轨迹初始化图 r75

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r74-v2(`8c20a2b`,`0.1.0.dev49`,148 资产,快照 `build/verification/review-2026-09-27-r74-firehose-tension-wording-v2`)的 successor;既有快照原样保留。合格 L1 交付根在本轮复核为空(0 项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`(读取零写入),只支持 provisional 有界历史开发比较。最终科学 HEAD `dd3a366`。

## 性质:两项新 operator + 一项新 task_graph(N2 neutral_beam_source_sampling)

按保存包 `program_framework_map.md` 节点归属,本批关闭 r72 dossier 中缓付的四项中的两项:

1. `scirel.fusion.nbi-source-plane-ray`(`construct_nbi_source_ray`):mc_nbi 源面分支——矩形/椭圆源面映射、焦距与发散射线项、束基坐标变换、逐孔径接受判定(源锚 `src/fidasim.f90:12780-12860`)。随机性由调用方变量(variate)承载,与 r71/r72 叶家族约定一致。
2. `scirel.fusion.beam-grid-ray-intersection`(`intersect_ray_with_rectilinear_grid`):grid_intersect 有限直角分支——六面枚举、首有效面配对(>0.001 cm)、dot 排序出入口(源锚 `src/fidasim.f90:8685-8814`)。
3. `scirel.fusion.nbi-trajectory-initialization`(`initialize_nbi_trajectory`,kind task_graph):保存包 `NBI轨迹初始化图` 的 caller-random 路径——归一化先行,`source_ray` 与 `cell_directed` 两分支互斥;组合五个已集成叶(normalization、两个新叶、能量分量速度缩放、单元定向射线),无嵌套图、无反馈,execution.feedback 为空。

其余两项缓付(如实声明,不强行凑资产):

- **NBI 权重生产链(NPA/FIDA 谱)**:保存包的权重/三谱资产是 MPI 门包与 LOS+谱 bin 消费者(r71 已登记 "MPI 归约/门包是运行时门而非科学关系"),其科学闭包依赖尚未提取的 LOS Doppler 几何与 colrad 状态。
- **DCX 谱线状态**:DCX 系列依赖六能级 colrad 推进(`碰撞辐射本征态推进`)与 CX 库,均未集成;保存包对该链自身的 formalization(R-N1-N3-DCX-HALO-MARKER-TRACE)也复用 colrad 核心。闭包不完整,不整合。

## 判重结论

- 对 r71/r72 已集成叶:源面射线与 `nbi-cell-directed-ray` 是同节点两条互斥源码路径(mc_nbi 源面分支 vs mc_nbi_cell 单元分支),输入域与几何方向不同,不合并;`beam-grid-cell-sampling` 是 cell 出生位置采样,与六面求交是不同关系;基线无任何射束网格求交或源面射线资产。
- 对未发布候选池:22 个候选目录均为 KN1DPy/PDR/碰撞/JH 等来源,无 FIDASIM NBI 候选,无重叠。
- 三资产构成最小依赖闭包:图的全部依赖均已是公共资产或本批叶;不发明缺失源事实。

## 登记的分歧与加固

- **声明未移植的运行时边界**:保存图的串行 `utilities.f90` 两字 RNG(seed、捕获状态、1000 次拒绝回退)是受控 glue,不是科学关系;本图拒绝 `source_serial_rng_seed`/`source_rng_state`/`source_fallback_axis_beam` 键,拒绝重采样由调用方驱动。保存包 16-marker 捕获态回放证据不继承。
- **候选射线语义(评审后修正措辞)**:source_ray 分支在孔径拒绝时仍计算候选速度与可选网格 handoff(保存 caller-random 对齐);exact document 明确下游必须按 `accepted` 门控,调用方拥有重试。
- **无限线配对语义(评审后钉定)**:束网格求交无 origin-side 检查,配对可整体位于射线起点后方;这正是原点在网格内时入口合法落在后方的同一规则。算术逐字保留并以回归钉定,文档 bounded,不做"仅向前"加固。
- **登记加固**:有限焦距/发散/半宽(NaN 通过源臂)、Python 与 NumPy bool 的 source_shape 拒绝、射线范数有限且非零(评审发现 Inf 范数塌缩为零"单位"射线)、输出有限门、网格边长有限(源臂 NaN 边长静默无交)。
- **源 quirk 逐字保留**:Float32 速度除数、theta_z-uses-focy(r72 已钉)、六面枚举顺序、0.001 cm 配对阈、无交回填起点。

## 组合证据

- 24 项直接测试:15 项算子测试(保存 probe 复现、闭式重算、孔径边界、加固见证、钉定语义)+ 9 项图合同测试(组合次序、分支互斥、可选 handoff 对叶直调、同变量(variate)逐位重放、RNG 边界拒绝、拒绝候选 parity)。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要逐资产同行记录于 exact documents 与 `build/test-evidence-r75.md`(参考记录,无自动漂移检测)。

## 相对 r74-v2 的增量

- r74-v2: 火焰管措辞修正(2 文档 + 2 测试更名),148 资产 dev49
- r75: NBI 源面几何家族(2 operator + 1 task_graph),151 资产 dev50;版本 `0.1.0.dev49` → `0.1.0.dev50`
- 全部 148 份既有文档仅机械版本提升;`src/scirel` 新增 3 文件 + `fusion/__init__.py` 纯公共导出追加

## 验证(全部为实测回执,子进程 returncode 已核;详见 `build/test-evidence-r75.md`)

- 源码态全仓(复放根激活):**1574 passed, 43 skipped, 0 failed**,returncode 0(r74 全树 1550,+24)
- 文档校验源码态:**151/151**,`runtime_origin: source`,`examples_executed: true`
- 安装态(干净 venv `build/venv-r75-clean`,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1 + setuptools 84.0.0,wheel `--no-index --no-deps`,`-I`):文档 **151/151**(`runtime_origin: installed`,示例执行通过);全树 **1573 passed, 44 skipped, 0 failed**,returncode 0。回执说明:本次安装态继承了激活的 KN1DPy 复放根,r74 安装态回执(1398/195)未激活复放根——+152/-151 的差异是该配置差异,不是测试集变化
- catalog `build/catalog/r75`:`complete: 151/151`,root digest `sha256:fa189331c58158df3e3c1d8fdd82a212dfc3735fcd3175e9fe4e6335023750a3`(评审修正后于最终 HEAD 重建)
- 内部 wheel `scirel-0.1.0.dev50-py3-none-any.whl`,SHA-256 `95515acce6684198bc7b57b5090bdd1a88c9c3c84223c549a82f238fafcb454d`(最终 HEAD 重建;评审前 wheel 已废弃)

## 审核范围:首次审核集合为全部 151 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r74-v2 的快照比较(`--comparison-snapshot`)只作开发增量导航辅助——r74-v2 本身是 `pending_unapproved` 开发快照,不冒充上一可信版。实测回执在冻结后以 `scripts/review_scope.py` 记录于 post-freeze addendum。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:NBI 权重生产链(NPA/FIDA 谱)、DCX/Halo 谱线状态、中子谱归约(MPI 门包)
- 开放专家问题:无限线配对语义是否需要未来的 forward-only 变体资产、源面/单元两分支的随机性约定是否统一、e0 差异裁决(沿 r71/r72 登记)
- 许可证状态均为 `pending-human-decision`
