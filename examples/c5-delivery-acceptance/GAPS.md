# C5 缺口清单

一个**只拿得到交付包**（`catalog/`、三个 usage skill、wheel、`runtime.json`、两份 requirements）的消费者，在三个物理任务里撞到的边界。每条都写两件事：**我怎么验证它缺失**，以及**我做了什么妥协**。

分级口径：

- **阻塞** —— 包里根本没有这个能力，任务无法只靠包完成；
- **影响可信度** —— 能算出一个数，但这个数的可信范围包内定不下来；
- **体验** —— 能用，但检索、参数、错误信息要绕；
- **流程** —— 打包、校验、入库环节的风险。

"包里没有"不等于"不在范围内"。前两类都是能力边界的真实证据，是 C0 诚实边界的输入，不能改写成"这个我们不提供"。

实测环境：包 `source_revision 435cc9a1`、`asset_count 249`、wheel sha256 `4c64938e…`、隔离 venv 里 `validate_installed_wheel` PASS（见 [receipt.json](receipt.json)）。

---

## 阻塞

### B1　安全因子 q 与磁剪切：完全没有合同

**验证**：`search --q 'safety factor'` 与 `search --q 'magnetic shear'` 都返回 `no_candidates`（不是空 items，是明确的无命中），并附 closest_terms。用索引复核：249 条资产里 **0 个**的 `symbol` 或 `capability` 名含 `safety`/`shear`。`scirel.io.read-geqdsk` 只是把 g-file 里**附带的** q 表读进 `mapping`，没有任何算子从磁面几何算 `q(ψ)`、算 `s=(r/q)dq/dr`，也没有对给定平衡求 `q(R,Z)` 分布。

**妥协**：三个任务全部避开 q 相关物理——撕裂模/NTM 稳定性、`q=m/n` 有理面判据、bootstrap 与 q 剖面的相容性，我一条都没做。用户真问"这个平衡的边界 q 和剪切是多少"，包内的答案是"没有这个能力"，而这三个字必须由人说出来，不能让检索的 `no_candidates` 自己扮演结论。

### B2　磁镜比压 R_m、损失锥角、镜点位置：没有算子

**验证**：12 份 mirror 合同**全部**把损失锥边界当**输入**——`solve_loss_cone_spectrum(xi_tp, …)` 的 `xi_tp` 就是 "loss-cone pitch-cosine endpoint"。没有一份接收磁场剖面并返回 `B_max/B_min`、`θ_loss` 或 `z_m`。最接近的 `scirel.mirror.grid-mirror-kinetic-closure` 只在两片命名平面上插值调用者给的 `b_t`，且 `applicability.excluded` 原文写着 "A general R-Z equilibrium solve, magnetic-field construction…"。

**妥协**：`R_m = 3.0`、`θ_loss = 35.2644°`、`z_m = 0.212132 m`、积分出的镜点 0.2121320213 m——这些全是我用 NumPy 写的，算子只吃了下游的 `ξ_tp = 1/√3`。**真正的风险不是多写几行，而是纠错面消失了**：`ξ_tp` 是输入，一个算错的镜比照样能得到一个自洽、精确到 1e-15、边界残差 5e-13 的谱，我任务 A 的 C1/C2 会全绿。包里没有任何东西能发现"你喂进去的损失锥边界是错的"。这不是"少一个便利函数"，是这条链上少了一环而无任何提醒。

### B3　没有三维坐标变换（环向角）

**验证**：包里只有 `scirel.sampling.meridional-polar-forward` 与 `-inverse` 这一对**二维子午面**变换。`search --q 'cartesian cylindrical'` 命中的是 grid-mapping、矩形插值、flux-surface 平均，都不是 `(x,y,z)↔(R,φ,Z)`。

**妥协**：任务 B 只在二维子午面内做往返。任何带环向角的题目（三点不共面、环向位移、场线沿 φ 缠绕、环向模数）消费者得自己写那一腿，我直接没做——所以这份清单对三维几何的结论是"未测"，不是"可用"。

### B4　从平衡求解到 mirror 域输入：没有合同级交接声明

**验证**：`scirel.equilibrium.compute-equilibrium` 只返回一个 `EquilibriumResult`，其 `outputs.units` 字面是 **`source-unspecified`**，`shape` 写 `psi/plas_currents R.shape`，`applicability.excluded` 含 "Physical equilibrium correctness"、"Force-balance residual"。而 mirror 域要的是 `b_t`（T）网格 + `psi`（"caller-consistent Wb or Wb/rad"）+ 两片 plug 平面。两端之间**没有任何合同**声明字段、单位、符号约定的对应关系；`psi` 的 Wb 与 Wb/rad 之别在 mirror 侧明说是调用者责任。

**妥协**：我没有走这条链，没用平衡结果驱动镜域计算。因此我对这条交接的判断只到"合同没写"，没有到"接不起来"。

---

## 影响可信度

### C1　非整数模式没有误差 oracle

`solve_loss_cone_spectrum(1/√3, 3)` 返回的度是 `[2.0000, 7.1379, 12.2495]`——只有整数根那一条有闭式（Legendre `P_2`）。合同自己写 "Non-integer degrees have no closed-form oracle here"。所以我能给整数模的偏差（8.9e-16）、能给端点残差（5.3e-13），**给不出非整数模式离真值多远**。

**妥协**：任务 A 只对整数模声明精度；非整数模式我只报"内部自洽"，没写成"精确"。

### C2　输运闭合是经验拟合，返回的数没有误差带

`scirel.neoclassical.bootstrap-current` 是 Sauter 1999 / Redl 2021 的解析拟合，合同写明 "not experimentally calibrated here"、"no … full-transport physics qualification"。我算出 `j_parallel` 高达 `-3.04e7 A/m²`，量纲与四个标度指数全部命中，但这只证明**代数与量纲自洽**，不证明这个数在真实装置上偏差多少。

**妥协**：结果只报数、报单位、报"经验拟合"，不给置信区间；任务 C 的结论限定为"量纲一致性通过"。

### C3　没有导数、雅可比或不确定度

`search --q 'gradient sensitivity'`、`--q 'uncertainty covariance'` → 都是 `no_candidates`；`--q 'jacobian derivative'` 只命中 `orthonormal-modal-basis`（与求导无关）。敏感性分析只能消费者自己做有限差分，而合同没有声明数值噪声水平，**步长选多大没有依据**——选大选小都可能编出一个假的导数。

**妥协**：本次三个任务都没做敏感性/误差传播。

### C4　平衡输出的单位是 `source-unspecified`

见 B4。一旦用 `EquilibriumResult` 往下算，"量纲自洽"这一关就无法用合同验证——没有单位就没有可对照的量。

**妥协**：任务 C 刻意只用 neoclassical 域（单位齐全）做量纲题，绕开 equilibrium 输出。

### C5　检索完备性未声明，一次命中只是候选

`runtime.json` 自己写：`completeness: unknown`、`scientific_applicability: not_assessed`、`incomplete_status: retrieval_incomplete`。`match` 只说明索引词命中；`no_candidates` 不证明能力不存在——B1 的结论是我读索引和合同之后下的，不是检索替我下的。

**妥协**：每个任务我都用 2–3 种措辞交叉检索，再逐条读 `identity`/`model`/`geometry`/`applicability` 才决定用哪个资产。这个"人工确认"环节包内无法自动化。

---

## 体验

### D1　中文检索恒为零，尽管索引里带 `title_zh`

`search --q '磁镜比压'` → `no_candidates`、0 条；而 `capability-index.json` 每条资产都带 `title_zh` 字段。合同正文以英文为主，skill 也直说 "long phrases or other languages often return nothing"。

**妥协**：全部改用英文关键词。中文用户第一次检索会得到"没有这个能力"的假象——这一点对中文用户的误导成本，比"多试两次"高得多。

### D2　检索是词面 AND，没有同义词

`search --q 'mirror ratio'` 命中 6 条，**没有一条真的算镜比**（B2 的根因之一）：它们命中 `mirror` 这个词，而 `ratio` 落在别处。词面 AND 无法表达"镜比 = B_max/B_min"。

**妥协**：读合同 `identity`/`model` 逐条排除，再下结论。三条候选的合同加起来读了约 40 KB。

### D3　`describe` 的返回形状与 skill 描述不一致

skill 写 "`describe`: catalog facts and `runtime`"，并在上文说命中在 `result.items`、零命中建议在 `result.gap`。实际 `describe` **没有** `result` 层，字段全在顶层（`asset_count`、`commands`、`filters`、`retrieval`、`runtime`、`schemas`）。照 skill 写 `d["result"]` 会 KeyError。

**妥协**：先 dump 全文看键名再写代码。

### D4　单条 `get` 很大，没有按段取子集

`scirel.closures.reduced-hall-drift` 的合同 34,875 B、`scirel.mirror.grid-mirror-kinetic-closure` 33 KB 级，而 `get` 只能整份取。skill 的建议是重定向到文件。

**妥协**：全部落盘后用 Python 读字段——这也是我不想在终端里读的原因（会被截断）。

### D5　零命中的 `gap` 建议对物理近义无用

`safety factor` 的 `closest_terms` 给出 `scirel.physics.dilution`（只共用了 "factor" 一词）和 `scirel.numerics.build-basis`。这类建议在"能力真的不存在"时会把消费者引向无关资产，反而掩盖了"该说没有"。

**妥协**：把 `gap.closest_terms` 当作"再试一个词的提示"，不当作候选。这也说明 `no_candidates` 必须由人/agent 读合同确认后才能升级为"缺失"。

---

## 流程

### E1　交付包没有校验入口，我手写了清单自校验

仓库有 `validate_extraction_package.py`（extraction kit）、`validate_installed_wheel.py`（装好的 wheel），**没有**校验"包本身"的脚本：没人检查成员集合、`runtime.json` 的 274 条 sha256、合同数与索引条数是否一致。我用一次性 Python 片段把 274 条逐条重算了一遍（0 处不符、0 个多余文件），把它写成了本目录的 [verify_package_manifest.py](verify_package_manifest.py)，这样这一项至少可复跑。

**妥协**：校验器的边界仍是"我自己写的脚本"，不是仓库门禁的一部分；它绿了也不代表别的包没问题。

### E2　打包脚本能造 zip，却从不调用

`scripts/build_pure_delivery.py` 定义了 `archive(directory, target)`，但 `main()` 只调 `build()`——CLI 永远只产出一个目录，要发给别人得自己 zip 一遍，而 zip 的压缩参数、时间戳、是否含 `runtime.json` 都没有统一规定。

**妥协**：我交付的是目录 + sha256，没有造 zip；"同一个包"在我的记录里等于"同一批字节的 sha256"，不依赖于任何归档格式。

### E3　新证据目录对 `test_scope` 是 fail-closed 的

`python3 scripts/dev.py run python -B scripts/test_scope.py --changed examples/c5-delivery-acceptance/tasks/…/solve.py` 直接 `FAIL-CLOSED: at least one changed path has no deterministic scope`，要求跑全量。`examples/**/*.md` 能映射到 docs 层，`.py`/`.json` 没有映射。

**妥协**：我只跑了 `ruff check` 与 `ruff format --check`（都绿），没有跑全量检查——全量是 lead 的 gate，不是我这里能替代的。所以这份记录的"检查状态"要如实读成"lint 通过，全量未跑"。

### E4　产物放哪没有规定，放错会随 worktree 一起消失

打包要求源树干净，所以必须在临时 worktree 里构建；但 `.runtime/` 被 gitignore，worktree 一删，放在**它的** `.runtime/` 里的包和回执就一起没了。我把产物放在 **clone 根**的 `.runtime/c5/`（被忽略、但与 worktree 生命周期无关），README 里写死了路径。

**妥协**：真正的交付证据仍是 `.runtime/` 里的运行产物，只有回执进了 git；换一个人复跑要重新打包。

### E5　"只用包校验包"做不到：校验器在仓库里

`validate_installed_wheel.py` 是仓库脚本，不在包内。消费者想自证"我装的这个 wheel 就是包里那个"，除了手算 sha256 没有别的路。严格说"只用这个包"只能到"sha256 对上"为止。

**妥协**：我用 worktree 里的校验器跑（它调用的是装好的 wheel 与其 dist-info，不碰 `src/`），并在 [receipt.json](receipt.json) 里写明校验器来自仓库而非包。这是本次记录里最弱的一环：一个外部消费者复现不了我的 PASS。

---

## 一句话总结

三个任务里 **1 个**（磁镜）只靠包完不成——缺的不是便利函数，而是把"镜比→损失锥边界"这一环，而缺了这一环，下游算得再准也没人发现输入错了；**2 个**（坐标往返、量纲自洽）能只靠包完成，且精度到机器精度。真正该写进能力边界的阻塞项是 **q / 磁剪切**、**镜比与镜点**、**三维坐标变换**、**平衡→镜域的交接声明**，这四条都不是"以后再说"，是包内确实没有。
