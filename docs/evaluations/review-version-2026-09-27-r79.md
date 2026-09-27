# SciRel FIDASIM neutral-reservoir/population merge family r79

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r78-v2(`01f3988`,科学 HEAD `a8ca079`,`0.1.0.dev55`,162 资产,快照 `build/verification/review-2026-09-27-r78-beam-deposition-family-v2`)的 successor;既有快照原样保留。合格 L1 交付根在本轮开始与结束均复核为空(0 项,含隐藏项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout `build/verification/neutral-harness-baseline-v2/inputs/l1/FIDASIM`(读取零写入),只支持 provisional 有界历史开发比较。最终科学 HEAD `987c7f2`。

## 性质:三项新 operator + 一项组合 task_graph(N3 neutral_population_transport)

本批整合 r78 缓付的 "多 cell 种群合并(中性库合并家族)":

1. `scirel.fusion.neutral-population-density-merge`(`merge_neutral_population_density`):保存包 `中性库种群合并` 的单 cell 六能级逐分量加法,目标拥有写入、源只读,暴露 before/after/贡献向量与六能级和(src/fidasim.f90:10484-10498,加法在 :10493)。
2. `scirel.fusion.neutral-population-grid-merge`(`merge_neutral_population_cells`):同一关系在显式 `(6,nx,ny,nz)` beam-grid 状态上的逐 cell 形式,报告 cell shape/count,不跨 cell 混合、不截断负分量。
3. `scirel.fusion.neutral-reservoir-merge`(`merge_neutral_reservoirs`):保存包 `中性库合并` 的单次局部 reservoir 采样合并(src/fidasim.f90:10343-10392 `merge_reservoirs` 及内联 update_reservoir fill/replace/skip 语义):空目标惰性初始化、双非满顺序追加、满/非满方向交换、双满按 float32 已见记录概率逐槽选择;全部 RNG 记录(初始化 uniform 对、替换槽位/uniform 对、双满逐槽 uniform)由调用方显式提供,内部不抽随机数。
4. `scirel.fusion.neutral-population-state-merge`(`merge_neutral_population_state`,kind task_graph):保存包 `中性库种群合并图` 的源顺序两节点组合(密度加法 → reservoir 合并),两块状态均为独立显式输入,`res2=res1` 局部反馈在 diagnostics 中声明。

## 公共资产裁定(评审发现)

保存包将单节点委托图 `中性库合并图`(单节点调用 `merge_neutral_reservoirs` 并附 diagnostics)声明为独立 TaskGraph。其端口与 operator 合同一一对应;按既有 DCXHalo迭代反馈图 先例(r75 halo-iteration-feedback-sequence 谱系)不移植为独立资产,组合图的 reservoir 节点直接绑定已集成 operator(registered deviation from saved packaging);待出现第二个独立消费者再提升。单 cell 与 grid 两个密度合并按保存包打包保留为两个独立身份(域不同:单 cell vs 全网格)。

## 与现有基线的关系(对照结果)

- 现有集成资产没有种群或 reservoir 合并关系。最近邻 `scirel.fusion.halo-iteration-feedback` 只消费同一源关系的密度更新(标量加法,在反馈守卫内),其文档明确排除 reservoir sampling;本族是缺失的合并关系本身(reservoir 半 + 所有权簿记为新增),记为 `add` 而非既有身份的 variant/composition。
- 下游衔接:已集成 NDMC producer 累积 `nlevels` 一般的种群网格;grid 合并是保存族固定的六能级形式。端到端证人以 `nlevels=6` 组合两个 NDMC marker 批次的种群网格逐 cell 合并;不宣称 general-level 合并能力。

## 源 quirk 逐字保留(回归钉定,非修复)

- 惰性初始化:`W = exp(log(u0)/k)`、`i = k + floor(log(u1)/log(1-W)) + 1`、`n = 1`,仅当 `target_n <= 0`;即使 merge 为 source-empty 也消费 uniform 对。
- 替换更新先乘 `W`,再以**更新后**的 `W` 抽取下一替换 horizon。
- 双满概率按 float32 计算 `p = float32(n1)/float32(n1+n2)`,且仅在 `uniform > p`(严格比较)时选择源槽位。
- 任何非空合并后源状态输出为合并后目标状态广播(res2=res1),非合并前源状态;source-empty 分支目标原样返回。
- 追加遍历在 `n <= k` 时写槽位 `n-1`,`n == i` 时消费替换记录,否则 skip;首个追加会先覆盖目标旧记录再由后续记录占用后续槽位(测试钉定)。

## 登记加固(各带判别回归)

1. reservoir 元数据与容量接受 genuine integer 含 `np.integer`(保存臂 `type(...) is int` 拒绝 `np.int64`),拒绝 bool、`np.bool_` 与整值浮点。
2. `W` 拒绝布尔(保存臂 `isinstance` 接受 `W=True`)。
3. 替换槽位下标必须为 genuine integer(保存臂的整值浮点接受会截断 `7.0`、静默转换 bool)。
4. 密度与 slot/uniform 数组拒绝布尔条目——bool dtype 与混合 object 形式(如 `[True, 1.0]`)一并拒绝(保存臂 `np.asarray(..., dtype=float)` 将 `True` 静默数值化为 1.0)。混合 object 缺口由 r79 冻结前只读预审发现并在冻结前闭合(权重、速度、初始化 uniform、替换 uniform、双满 uniform 全覆盖判别回归)。

## 组合证据

- 23 项直接测试(`tests/operator_contracts/test_neutral_merge_family.py`):四资产保存 probes、源 quirk 钉定、全部加固回归、以及合并两个 NDMC 产出六能级种群网格的端到端证人。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要逐资产记录于 exact documents 与 `build/test-evidence-r79.md`(参考记录,无自动漂移检测)。

## 相对 r78-v2 的增量

- r78-v2: 束中性逐段沉积家族 + NDMC producer,162 资产 dev55
- r79: 中性库合并家族(3 operator + 1 组合图),166 资产 dev56;版本 `0.1.0.dev55` → `0.1.0.dev56`
- 既有 162 份文档机械版本提升;`src/scirel/fusion/__init__.py` 追加四个纯公共导出

## 验证(全部为最终 pwsh 7+ 门禁实测回执,真实退出码已核;详见 `build/test-evidence-r79.md`)

- 源码态全仓(复放根激活):**1657 passed, 43 skipped, 0 failed**,exit code 0(r78-v2 全树 1634,+23)
- 文档校验源码态:**166/166**,`runtime_origin: source`,`examples_executed: true`,exit code 0
- 安装态(干净 venv build/venv-r75-clean,numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1,wheel `--no-index --no-deps` 安装):文档 **166/166**(`runtime_origin: installed`);全树 **1656 passed, 44 skipped, 0 failed**,exit code 0,junit 确认 0 errors;`scirel.__file__` 位于 venv 内
- catalog `build/catalog/r79`:`complete`,declared_total 166,root digest `sha256:a4e7abe9b74f57f797a1a1018d9a38cdd0d7b65fdfd69b62722e3a28917dba64`
- 内部 wheel `scirel-0.1.0.dev56-py3-none-any.whl`,SHA-256 `1a30d6582ac98478790c3712ea0914aabab3918c13a6f73e5249498343df9df6`

## 审核范围:首次审核集合为全部 166 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r78-v2 的快照比较只作开发增量导航辅助。实测回执在冻结后记录于 post-freeze addendum(如有)。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:真实 HDF5 表驱动、NPA/FIDA 权重生产链、MC marker 生产、并行(MPI 秩)reservoir 合并图、中性库生命周期
- 开放专家问题:(1) 本族密度单位沿用调用方解释("source population density");若专家就 r78 未决的 N3 rate-density 纲要作出裁定,本族文档应继承该裁定。(2) grid 合并固定六能级与 NDMC producer `nlevels` 一般网格之间的层级:是否需要 level-general 合并是新能力决策。(3) 许可证状态均为 `pending-human-decision`
