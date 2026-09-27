# SciRel FIDASIM DCX/HALO 迭代反馈家族 r76

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r75-v2(`2b922fb`,`0.1.0.dev50`,151 资产,快照 `build/verification/review-2026-09-27-r75-nbi-source-geometry-v2`)的 successor;既有快照(r75-v1/v2 及更早)原样保留。合格 L1 交付根在本轮开始与结束均复核为空(0 项),未消费任何合格 L1 输入。FIDASIM 保存包位于兄弟主仓库 checkout `D:/software/PyCharm 2025.3.3/workspace/SciRel/build/verification/neutral-harness-baseline-v3/inputs/l1/FIDASIM`(读取零写入),只支持 provisional 有界历史开发比较。最终科学 HEAD `60804c4`。

## 性质:一项新 operator + 一项有界显式反馈序列 task_graph(N3 neutral_population_transport)

本批推进 r75 缓付清单中的 "DCX 谱线状态" 项:其种群迭代反馈核心在保存包中已完整且确定性,可独立整合;而 DCX/CX 初态与光子修正仍依赖未提取的六能级 colrad 核心,继续缓付。

1. `scirel.fusion.halo-iteration-feedback`(`advance_halo_iteration_feedback`):halo 种群迭代的一轮反馈边界——密度增长守卫(`current/previous > 1` 在更新 previous/merge/seed 之前退出)、`merge_neutral_populations` 密度合并(加法顺序按 `src/fidasim.f90:10484-10500`)、`seed_dcx` 份额、`int(source_budget * seed_dcx)` 的 Fortran 截断 marker 数;seed 退出阈 `seed_dcx < 0.01`,等号继续。全部状态为调用方显式密度,不读取 reservoir、HDF5、RNG 或源运行时。
2. `scirel.fusion.halo-iteration-feedback-sequence`(`advance_halo_iteration_feedback_sequence`,kind task_graph):保存包 `DCXHalo迭代反馈序列图` 的组合——按源顺序复用单轮反馈算子,强制 requested marker budget 的源递推(首轮 base budget,其后各轮 `next_halo_marker_count`),序列必须恰好在源停止分支结束。反馈按 AGENTS.md 显式声明:状态(previous/merged 对)、顺序、停止分支、迭代上限(调用方序列长度)。MC marker、plasma、track、colrad、reservoir、MPI、HDF5 均在图外。

## 判重结论

- 对基线:无 HALO 种群迭代反馈或种群合并递推资产。KN1DPy 的 `generation-accumulation-update`/`generation-density-reduction` 是中性输运世代归约,`outer-seed-convergence`/`kn1d-outer-convergence` 是求解器种子收敛迭代——关系、谓词与状态语义均不同,不合并。
- 对未发布候选池:无重叠。
- 保存包的单步委托图 `DCXHalo迭代反馈图` 未作为独立资产移植:其端口与算子合同一一对应、无组合内容;决定(含其摘要)记录在序列图 exact document 中。

## 登记的分歧与加固

- **显式有界反馈**:状态、顺序、停止分支、迭代上限全部声明;越界(停止后仍有输入/序列结束仍继续)fail closed,不外推。
- **登记加固**(带判别见证):real-scalar 类型检查(保存臂把字符串经 float() 转换)、有限 ratio/seed/merged 输出、有限且可表示的双精度 marker 乘积 `budget*seed`(保存臂静默返回 Inf 或在 `int(Inf)` 内抛裸 OverflowError)。
- **精确整数预算保存**:int 条目任意量级保持全精度(2^53+1 无漂移复现);float 条目仅在有限且双精度下恰为整数时接受——2^53+1 以 float 给出时无法与其精确 base 匹配,drift fail closed(数值边界已写入 exact document)。bool 条目逐元素拒绝(保存臂经 float64 转换接受)。
- **源 quirk 逐字保留**:增长退出次序(前于 previous/merge/seed 更新,previous 保持不变)、增长分支的 None 投影(非补零)、0.01 等号边界、合并加法顺序、Fortran 非负截断。

## 组合证据

- 13 项直接测试:保存 probe 复现(0.559 seed 案例与 marker 22、ratio=1 继续、0.01 边界、增长退出与 None 投影、五轮序列与 4 continue/1 seed stop 分支计数)、逐轮对单轮算子直调的闭式重算、budget 递推 drift、停止后继续、未终止序列、大整数保存、bool 拒绝、上列溢出加固。
- 无独立复放文件:FIDASIM 保存包以包级 oracle 为验证目标;保存实现内容摘要逐资产记录于 exact documents 与 `build/test-evidence-r76.md`(参考记录,无自动漂移检测)。
- 预冻结评审:三个合同案例(budget*seed OverflowError、bool budget 接受、>2^53 伪漂移)均先红后修,记录于 `60804c4` 与测试文件。

## 相对 r75-v2 的增量

- r75-v2: NBI 源面几何家族(2 operator + 1 task_graph)+ 证据-only 后继,151 资产 dev50
- r76: DCX/HALO 迭代反馈家族(1 operator + 1 有界序列 task_graph),153 资产 dev51;版本 `0.1.0.dev50` → `0.1.0.dev51`
- 全部 151 份既有文档仅机械版本提升;`src/scirel/fusion/__init__.py` 两项纯公共导出追加

## 验证(全部为实测回执,子进程 returncode 已核;详见 `build/test-evidence-r76.md`)

- 源码态全仓(复放根激活):**1587 passed, 43 skipped, 0 failed**,returncode 0(r75 全树 1574,+13)
- 文档校验源码态:**153/153**,`runtime_origin: source`,`examples_executed: true`
- 安装态(干净 venv,自装 numpy 2.5.3 / scipy 1.18.1 / pytest 9.1.1 + setuptools 84.0.0,wheel `--no-index --no-deps`,`-I`):文档 **153/153**(`runtime_origin: installed`,示例执行通过);全树回执见 evidence 文件
- catalog `build/catalog/r76`:`complete: 153/153`,root digest `sha256:9e81738fd810bc1c0a15bc854377b0cc6e1b29278b3e615458d2eee4849f2970`(评审修正后于最终 HEAD 重建)
- 内部 wheel `scirel-0.1.0.dev51-py3-none-any.whl`,SHA-256 `bc6bce8b89ddbf720fbd002fabd838cca86f8a7c0ed53f355f4875a3b74b764a`(最终 HEAD 重建)

## 审核范围:首次审核集合为全部 153 份 exact documents

当前没有可信基线:无可信版时不传比较快照,首审集合为全部文档。与 r75-v2 的快照比较只作开发增量导航辅助。实测回执在冻结后记录于 post-freeze addendum。

## 边界与待决

- 不宣称合格 L1 消费、外部物理正确性、专家认可、可信晋级、公开发行
- 继续缓付:DCX/CX 初态与光子快离子修正(依赖 colrad 核心)、NBI 权重生产链(NPA/FIDA 谱,MPI 门包 + LOS/Doppler 几何)、多 cell 种群合并与 MC marker 生产
- 保存包登记的运行时注意事项(供专家评估,非本算子行为变化):halo/dcx 生成路径在默认 8MB 栈下对大网格有 unbounded-stack SIGSEGV 观测,需 `ulimit -s unlimited` + `OMP_STACKSIZE=1G`;详见保存包 operator.md 专家评审节
- 开放专家问题:0.01 seed 阈值的物理依据、双精度 marker 计数的精度边界是否需要显式变体、增长守卫与合并次序的专家确认
- 许可证状态均为 `pending-human-decision`
