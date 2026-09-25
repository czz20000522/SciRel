# SciRel KN1DPy Maxwellian 速率平均整合 r41

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。当前合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)为空,本轮未消费任何合格 L1 输入。

本轮相对 r40(`465cd8a208579e89cc4ebbd583abad2c218673c1`)的科学增量是**一项新增公共资产**:

- `scirel.collisions.maxwellian-relative-speed-rate-average`(operator,公共 callable `average_cross_section_over_maxwellian`):按保存的 KN1DPy `make_sigmav` 切片(`make_sigmav.py:13-57`)整合的显式网格 Maxwellian 相对速度速率平均;能量分辨 `<σv>`,碰撞能量按来源约定使用粒子质量(非约化质量)。新增直接回归 44 项(独立公式对照、静止束/冷靶解析极限、体积缩放不变性、输入/失败/组合合同)、环境门控历史复放 3 项(源文件 SHA-256 绑定,`SCIREL_KN1DPY_REVIEW_ROOT`)与一份 exact document。公共导出经 `scirel.collisions` 与根命名空间发布。
- 来源单节点消费图 `粒子靶Maxwellian速率系数图` 为恒等组合,不另立 TaskGraph 资产;其端口/状态/失败策略由 exact document 与组合回归表达。

两处有据修复已写入 exact document:保存实现未执行的"非有限输入 fail closed"与"结果有限"合同在本后继中成立(拒绝域其余不变),错误消息按参数命名。来源对照一律为**有界历史开发证据**——KN1DPy 严格 D1 资格已撤回,保存包属 `D1待重审历史产物`;双臂复放(常数/线性截面,独立实现相对差 0 / 2.7e-16,保存 extraction_report 7.8e-17 / 2.4e-16)不构成来源资格重认。

其余 68 份 exact document 仅机械更新 `implementation_version`(`0.1.0.dev18` → `0.1.0.dev19`,与重建的内部 wheel 绑定),不产生新的科学证据;测试基线仅更新资产计数断言(68→69)、`collisions.__all__` 精确断言与一个 fixture 的 `declared_total`,无任何数值断言或容差放宽。

验证证据:失败回归先行;`check.ps1 -Mode affected` **941 passed, 46 skipped**;69 份文档源码态与安装态(`python -I` 隔离 venv)运行时/示例校验均通过;安装态直接/复放/相邻算子测试 100 passed;内部 wheel `scirel-0.1.0.dev19-py3-none-any.whl` SHA-256 `c18a3bafe88fad22c69f4cce246537ffdc35099db3c40718deb94e2f7f67405d`;开发 catalog `complete: 69/69`,root digest `sha256:2f9147ae725f0a4c55f0dc64d9c7b3bcc4cefe08c88390378dbe20777b3b5707`。确切快照绑定见冻结清单;科学差异与专家待决五项见[候选文档](../../review_candidates/2026-09-25-kn1dpy-maxwellian-rate/review.md)与[整合记录](intake-2026-09-25-kn1dpy-maxwellian-rate.md)。

无可信基线,首次专家审核仍覆盖全部 69 项资产;不能把本项增量当作唯一审核范围。测试通过、文档校验、catalog/wheel 构建与冻结都不构成科学认可;专家需决定新资产身份、两处修复、碰撞能量约定、单节点图处置与来源证据边界。
