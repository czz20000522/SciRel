# SciRel Johnson-Hinnov 氢辐射诊断族 r59

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发布。本版是 r58(`2d3a89ccae09b77b4182c1a9d7861da77cdb9ce2`,快照 `build/verification/review-2026-09-25-r58-jh-degree-correction`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:三项新任务图(组合已有资产)

r57 缓付的辐射诊断组合批落地为 `scirel.diagnostics` 下三个 task graph:

1. `scirel.diagnostics.hydrogen-jh-lyman-alpha-emission`
   (`solve_hydrogen_jh_lyman_alpha_emission`;依赖 hydrogen-jh-r-coefficient、
   hydrogen-saha-equilibrium-population);
2. `scirel.diagnostics.hydrogen-jh-balmer-alpha-emission`
   (`solve_hydrogen_jh_balmer_alpha_emission`;同前两项依赖);
3. `scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion`
   (`solve_hydrogen_jh_balmer_alpha_ground_state_inversion`;依赖
   hydrogen-jh-r/s/alpha-coefficient 与 hydrogen-saha-equilibrium-population)。

源锚:`KN1DPy/jh_related/lyman_alpha.py:42-64`、`balmer_alpha.py:40-64`、
`N0_from_balmer_alpha.py:12-70`(取自保存包自身抽取记录)。保存组合的冻结
常数(`1.602177e-19`、`13.6057 * (0.25 - 1/9)` eV)与运算次序逐位保留;无修复。
载荷生产器(`create_jh_bscoef.py`)继续缓付:系数数据资产准入仍是开放的 r57
专家决定。域选 `diagnostics`(谱线发射/反演诊断);保存端口名保留为图输入端口。

## 声明的组合域收窄(r57 专家问题 #4 的处理)

组合域取被绑定资产合同交集:密度与温度 `(0, 1e32)`(r56 Saha 资产声明域;
保存辐射 callable 接受任意正有限值),`n0` 两臂同限 `< 1e32`。共享域上输出
与保存组合逐位相同(复放验证);`≥1e32` 时本图 fail closed 而保存臂返回
数值——该分歧由前向臂专门复放测试逐臂见证。

## 预审修正两处(冻结前只读预审发现,已回修)

1. **载荷八字段精确合同**:初稿只校验各分支消费的字段;已修正为三图在求值
   前经新私有支持模块 `scirel.diagnostics._jh_payload_validation` 的
   `validate_jh_payload` 执行保存的精确字段合同(字段集含未消费字段、节点、
   order 4、77 系数几何、全字段有限),错误消息与保存一致。该合同**刻意**
   不放入 `scirel._validation`:该支持模块被旧流程准入账本逐字节内容锁定
   (LF SHA-256 `08d251…4ee`),改动会破坏既有锁;`_validation.py` 本轮
   字节零变化,账本零变化。双臂反例(Lyman 删 `A_Balmer`、Balmer/反演删
   `A_Lyman`)在复放测试逐臂钉死。
2. **输出仅做有限性门控(来源对等)**:初稿拒绝非正光子率,而保存分支只
   检查有限性——`A[0]=0` 返回零(无发射),负 `A[0]` 返回负值。已修正为
   来源对等并在 exact document 明示;零系数情形双臂逐位钉死。反演臂恢复的
   光子率因观测发射率被校验为严格正而保持严格正,与保存一致。

两处修正均为本批新增断言的修正,未弱化任何既有数值断言。

## 变更清单

- 新增 `src/scirel/diagnostics/hydrogen_jh_{lyman_alpha_emission,balmer_alpha_emission,balmer_alpha_ground_state_inversion}.py` 与支持模块 `src/scirel/diagnostics/_jh_payload_validation.py`。
- 新增三个 exact document(kind=task_graph,diagnostics 域首批图)+ 其余 96 份机械 `implementation_version` 提升;版本 `0.1.0.dev30` → `0.1.0.dev31`。
- 新增六个测试文件(3 直接 + 3 复放,`tests/graph_contracts/hydrogen_jh_*/`)及各自 `task_graph.yaml`。
- `src/scirel/diagnostics/__init__.py`、`src/scirel/__init__.py` 导出;
  `tests/_review_bindings.py` 追加 4 条 operator 绑定(纯增量);
  `tests/test_asset_documentation.py`、`tests/test_affected_test_selection.py`、
  `tests/test_thin_mcp_adapter.py` 计数断言 96→99(图数 11→14)。
- 新增候选三件套 `review_candidates/2026-09-25-jh-radiation/`、本记录与
  `docs/evaluations/intake-2026-09-25-jh-radiation.md`、index 新增 batch r59。
- `provenance/admitted-assets.json`、`src/scirel/_validation.py`、
  `src/scirel/_composition.py`:**字节零变化**(临时生成器脚本已从 tracked
  树移除,属工程清理,无运行依赖)。

## 科学证据

- 公式分解先于编码:由 SciRel 资产等价片段按保存运算次序重组,对保存实现
  逐位核对后才落码;Lyman/Balmer 光子率、发射率与反演六字段逐位成立。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 6+5+5=16,复放
  4+4+3=11,合计 27。
- 独立 oracle:被绑定 SciRel 资产独立重算(逐位)、独立 FITPACK 路径
  (`RectBivariateSpline.ev`)、`_review_bindings` 资产装载见证、经前向
  Balmer 图的 n0 往返恢复、s/alpha 密度语义分裂见证。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,保存实现文件
  SHA-256 `253cda22…` 绑定):三种 profile 全部 `assert_array_equal` 逐位
  复现;拒绝行为、`≥1e32` 域收窄分歧、零系数返回零值逐臂见证。

## 验证(含 shell 记录)

- **shell 环境**:本轮早中期测试由 Git Bash 执行(`python -B`,显式
  `PYTHONDONTWRITEBYTECODE=1`,显式 `PYTHONPATH`/`SCIREL_KN1DPY_REVIEW_ROOT`);
  冻结前按执行规范切换到 pwsh 7+ 复跑关键门禁。已通过的科学/安装测试未因
  shell 形式本身重跑;下述为 pwsh 7 复跑记录。
- `pwsh ./scripts/check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):
  **1301 passed, 43 skipped, 0 failed**(r58 1274,+27;skip 计数不变)。
- 99/99 exact documents 源码态校验通过(`--check-runtime --execute-examples`,
  `runtime_origin: source`,`examples_executed: true`);安装态
  (`--installed-runtime`)**99/99** 同过。
- 内部 wheel `scirel-0.1.0.dev31-py3-none-any.whl`(SHA-256
  `ba5b35976bc16202eea8a8f59b5e1c866b0d9f180d32f9aa9ea6a538718b20e7`);开发
  catalog `complete: 99/99`,root digest
  `sha256:4bbd3063301977efc1c28cd5cbc21893038239250ceedbaeba8ab39fc89199ee`。
- 干净离线 venv(fresh `build/venv-r59-clean`,本地 wheelhouse 安装依赖,
  `--no-index --no-deps --force-reinstall` 安装 wheel,`python -I` 隔离探针
  确认 under-prefix):r45 文档化 source-free 子集 **914 passed, 148 skipped,
  0 failed**;全 tests 树 **1193 passed, 151 skipped, 0 failed**。
  (以上两条为 Git Bash 记录的安装态计数;pwsh 7 复跑安装态子集同计数,
  见下。)

## 边界与待决

- 不宣称:合格 L1 消费、系数表与 Einstein 表对外部原子物理参考的正确性
  (`validation_oracle_gap` 原样保留)、调用方输入的物理有效性、专家认可、
  可信晋级或公开发行。
- 开放专家问题新增:Lyman 发射率能量因子(保存的 n=3→2 能量)是否为预期
  发布合同,或应由后继修复(会改变发射率输出、不影响光子率、需新证据)。
  r57/r58 的密度哨兵覆盖、标签-次数、两种载荷形式、系数数据资产准入等
  问题原样保留;Saha 域边界以声明交集域方式在本批落地,最终认可待专家。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS
  组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖
  全部 99 项资产。
