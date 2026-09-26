# KN1DPy Johnson-Hinnov 氢辐射诊断族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始时
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-jh-radiation/review.md)及其
[比较清单](../../review_candidates/2026-09-25-jh-radiation/README.md)。

## 关系族选择

本批次整合保存包 `原子氢JH-r系数B样条评价` 中 r57 缓付的三个辐射诊断关系
(`evaluate_lyman_alpha`、`evaluate_balmer_alpha`、
`invert_balmer_alpha_to_ground_state`,源锚 `lyman_alpha.py:42-64`、
`balmer_alpha.py:40-64`、`N0_from_balmer_alpha.py:12-70`,取自保存包自身抽取
记录)。对照 r58 基线(`2d3a89c`,96 资产 dev30)与未发布候选池:基线与池中
均无"由人口与系数资产组合的氢谱线发射/反演"类资产,三个保存关系均为
**新增能力**,按科学语义判重。三者为既有 SciRel 资产的任务图组合(r57 JH
r/s/alpha 系数 + r56 Saha 人口),即 r57 缓付说明中的"组合批次"。载荷生产器
(`create_jh_bscoef.py`)继续缓付:物化打包系数数据,准如数据资产是独立的专家
决定。域选择 `diagnostics`(谱线发射与反演诊断,非碰撞系数);保存端口名
(`density_m3`、`temperature_ev`、`n0_m3`、`balmer_alpha_w_m3`、`jh_payload`、
`no_null`)保留为图输入端口。来源树只读:全部导入 `python -B` 且显式
`PYTHONDONTWRITEBYTECODE=1`,本轮对保存树零写入。保存实现文件 SHA-256
`253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344`。

## 三项资产(全部无修复,组合已有资产)

1. **`scirel.diagnostics.hydrogen-jh-lyman-alpha-emission`**
   (`solve_hydrogen_jh_lyman_alpha_emission`):光子率
   `A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2` 与发射率(冻结因子
   `13.6057 * (0.25 - 1/9)` eV),保存运算次序逐位保留。保存实现把同一能量
   因子用于两条谱线(Lyman 发射率带 n=3→2 能量),**开放专家问题**记录,
   不修复。
2. **`scirel.diagnostics.hydrogen-jh-balmer-alpha-emission`**
   (`solve_hydrogen_jh_balmer_alpha_emission`):level-3 通道与 `A_Balmer[0]`,
   同上逐位保留。
3. **`scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion`**
   (`solve_hydrogen_jh_balmer_alpha_ground_state_inversion`):六字段反演
   (r03/r13/s/alpha + Saha 1/3),保存运算次序逐位保留;s/alpha 密度语义
   分裂随之进入返回的电离/复合源项,与保存一致。

## 声明的域收窄(r57 专家问题 #4 的处理)

组合域取被绑定资产合同交集:密度与温度 `(0, 1e32)`(r56 Saha 资产声明域;
保存辐射 callable 接受任意正有限值),`n0` 两臂同限 `< 1e32`。共享域上输出
与保存组合逐位相同(复放验证);`≥1e32` 时本图 fail closed 而保存臂返回
数值——该分歧由每条前向臂的专门复放测试见证。

## 预审修正两处(冻结前,只读预审发现)

1. **载荷八字段精确合同**:初稿只校验各分支消费的字段,删除未消费字段
   (如 Lyman 臂的 `A_Balmer`)会被错误接受,而保存 `_validate_payload`
   拒绝。已修正:三图在求值前经共享 `scirel._validation.validate_jh_payload`
   执行保存的精确字段合同(字段集、节点、order 4、77 系数几何、全字段有限),
   错误消息与保存一致;r57 s 资产内的同合同副本未改动。双臂反例(Lyman 删
   `A_Balmer`、Balmer/反演删 `A_Lyman`)在复放测试逐臂钉死。
2. **输出仅做有限性门控(来源对等)**:初稿拒绝了非正光子率,而保存分支只
   检查有限性——`A[0]=0` 返回零(无发射),负 `A[0]` 返回负值。已修正为
   来源对等,exact document 明示该语义与符号责任在调用方数据;零系数情形在
   双臂逐位钉死。反演臂因观测发射率被校验为严格正,恢复的光子率保持严格正,
   与保存一致。

两处修正均为本批新增断言的修正,未弱化任何既有数值断言。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 公式分解先于编码验证:由 SciRel 资产等价片段按保存运算次序重组,对保存
  实现逐位核对(`assert_array_equal`)后才落码;Lyman/Balmer 光子率、发射率
  与反演六字段全部逐位成立。
- 失败回归先行:移除三个新模块后六个新测试文件收集期 ImportError,恢复后
  全部通过。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 6+5+5=16,复放
  4+4+3=11,合计 27。
- 独立 oracle:被绑定 SciRel 资产的独立重算(逐位)、独立 FITPACK 路径
  (`RectBivariateSpline.ev`)、`_review_bindings` 资产装载见证(依赖确实
  经声明绑定注入)、经前向 Balmer 图的 n0 往返恢复、s/alpha 密度语义分裂
  见证(alpha 系数密度无关、复合项随密度平方缩放、s 系数消费密度)。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,保存实现文件
  SHA-256 绑定):打包系数载荷上 Lyman/Balmer 三种 profile、反演六字段全部
  `assert_array_equal` 逐位复现;拒绝行为(no_null、n0 域、非正发射率、
  载荷缺陷)双臂一致;`≥1e32` 域收窄分歧逐臂见证;零系数返回零值双臂见证。

## 开发验证(r59 当前状态)

见 [r59 评审说明](review-version-2026-09-25-r59.md) 的验证节;版本
`0.1.0.dev30` → `0.1.0.dev31`(新增 wheel 承载字节)。许可证状态均为
`pending-human-decision`。

## 边界与待决

- 本轮不宣称:合格 L1 消费、系数表与 Einstein 表对外部原子物理参考的正确性
  (`validation_oracle_gap` 原样保留)、调用方输入的物理有效性、专家认可、
  可信晋级或公开发行。
- 开放专家问题新增:Lyman 发射率能量因子(保存的 n=3→2 能量)是否为预期
  发布合同。r57 的密度哨兵覆盖、标签-次数、两种载荷形式、系数数据资产准入
  等问题原样保留;Saha 域边界问题以"声明交集域"方式在本批落地,最终认可
  待专家。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS
  组装、SIG 矩阵组装等)继续缓付。
