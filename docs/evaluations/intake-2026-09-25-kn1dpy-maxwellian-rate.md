# KN1DPy Maxwellian 速率平均开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包现属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)为空,
本轮未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,
不构成 SciRel 专家认可或来源资格重认。

## 科学关系与行动

原始比较与专家决策请求见[候选文档](../../review_candidates/2026-09-25-kn1dpy-maxwellian-rate/review.md)及其[比较视图](../../review_candidates/2026-09-25-kn1dpy-maxwellian-rate/README.md)。KN1DPy 的 `make_sigmav` Maxwellian 相对速度速率平均(源锚 `KN1DPy/make_sigmav.py:13-57`,保存实现文件 SHA-256 `e006a4ddb49f00d732ba03816fec591bca41d518d6d8df71a2b4985edb1aecb6`)在本轮基线 `465cd8a208579e89cc4ebbd583abad2c218673c1`(r40)的 68 项公共资产与未发布候选池中均无语义重复:最接近的 `bosch-hale-reactivity` 是温度-only 解析聚变反应率参数化,Bessel/动量标度叶是其他量的定义;候选池 52 个 Pleiades 单元及两个附加快照无碰撞速率类资产。按科学合同(输入、模型、输出)判重,非按名称。

开发行动是新增 `scirel.collisions.maxwellian-relative-speed-rate-average`(公共 callable `average_cross_section_over_maxwellian`,keyword-only 九端口),不改接任何来源 TaskGraph;唯一精确科学合同为 [asset document](../../catalog/examples/scirel.collisions.maxwellian-relative-speed-rate-average.json),代码与直接测试分别在 `src/scirel/collisions/maxwellian_relative_speed_rate_average.py` 与 `tests/operator_contracts/test_maxwellian_relative_speed_rate_average.py`。来源单节点消费图 `粒子靶Maxwellian速率系数图` 为恒等组合,其 N1 快照端口/状态/失败策略写入 exact document 并由组合回归保护,不另立 SciRel TaskGraph 资产。

两处有据修复(均写入 exact document 的 failure semantics 与 known_limitations):保存文档声明非有限输入 fail closed 且结果有限,但其实现两者都未检查——NaN 网格点、质量或温度会静默传播;SciRel 后继按参数名拒绝非有限输入,并拒绝不可表示的速率。错误消息改为按参数命名。拒绝域其余保持不变;公式、体积归一化与比例不变性、粒子质量碰撞能量约定逐位保留(常数 `AMU_KG=1.6726231e-27`、`ELEMENTARY_CHARGE_C=1.602177e-19` 为保存源冻结值)。

## 公式核实与双臂对照(独立探针,交付根外临时目录,PYTHONDONTWRITEBYTECODE=1)

- 常数截面两例(40×60、80×120 中点网格):独立 loop-per-energy 实现与保存实现最大相对误差 `0.0`(逐位一致)。
- 线性截面 holdout(`sigma(E)=2e-20+1e-22·E`):最大相对误差 `2.690e-16`。
- 体积权重常数缩放不变性:相对差 `1.204e-16`(归一化吸收常数因子)。
- 静止束极限(E=0,`T_target=T_norm`):`<σv> -> σ·vth·2/√π`,细化 60→480 行误差 `1.55e-4 → 1.49e-5` 单调收敛。
- 冷靶极限(`T_target=0.05 eV`):`<σv> -> σ(E_beam)·v_beam`,相对误差 `3.311e-4`。
- 保存 extraction_report 的历史双臂 source-free 复放(常数截面 7.81861707894196e-17、线性截面 2.4125886194670293e-16)作为来源侧证据一并引用;KN1DPy 严格 D1 资格撤回后,该证据同样只是有界历史比较。

## 开发验证

- 失败回归先行:直接合同测试在新 callable 缺失时 ImportError 失败,实现后 44 passed。
- 环境门控历史复放 `tests/operator_contracts/test_maxwellian_relative_speed_rate_average_l1.py`(变量 `SCIREL_KN1DPY_REVIEW_ROOT`,源文件 SHA-256 绑定):常数/线性截面 rtol 1e-14 复放通过,并含 NaN 修复差分见证(保存实现返回非有限速率,后继拒绝),3 passed。
- `pwsh ./scripts/check.ps1 -Mode affected`:选择新算子直接测试、公共导出、exact document 与计数断言,**941 passed, 46 skipped**。计数断言更新为 69 资产(`test_asset_documentation`、`test_affected_test_selection`、`test_thin_mcp_adapter` fixture)与包级 `__all__` 断言(`test_momentum_scales`);无既有数值断言或容差放宽。
- `python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples`:源码态 **69/69** 通过(含可执行示例)。
- 内部 wheel `scirel-0.1.0.dev19-py3-none-any.whl`(SHA-256 `c18a3bafe88fad22c69f4cce246537ffdc35099db3c40718deb94e2f7f67405d`),含新模块 `scirel/collisions/maxwellian_relative_speed_rate_average.py`。
- 开发 catalog `complete: 69/69`,root digest `sha256:2f9147ae725f0a4c55f0dc64d9c7b3bcc4cefe08c88390378dbe20777b3b5707`。该 builder 输出是开发校验投影,不是可信发布目录。
- 隔离安装态(venv `--system-site-packages` 复用开发机 NumPy/SciPy,`--no-index --no-deps` 安装 wheel,`python -I` 执行):隔离探针确认 `scirel` 解析到 venv `site-packages` 而非源码;安装态公共调用探针通过;安装态直接/复放/相邻算子测试 **100 passed**(44+3+21+32);69 份 exact document 安装态运行时与示例校验通过(`runtime_origin: installed`)。该环境只证明 wheel 与源码隔离,不证明声明依赖可由干净离线 wheelhouse 独立重装。

## 边界与待决

- 本轮不宣称:合格 L1 消费、物理截面模型正确性、调用方网格/体积的物理有效性、来源项目在比较域外的正确性、专家认可、可信晋级或公开发行。
- 许可证状态沿用 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审版说明见 [r41 评审说明](review-version-2026-09-25-r41.md)。
