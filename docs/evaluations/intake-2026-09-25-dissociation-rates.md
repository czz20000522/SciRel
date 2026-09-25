# KN1DPy 解离速率族开发整合记录

状态:**隔离开发版本,非可信版、非公开发行**。本记录对照保存的 KN1DPy 提取包;
该包属 `D1待重审历史产物`,其严格 D1 资格已撤回,合格 L1 交付根
(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)在本轮开始与结束均
复核为空,未消费任何合格 L1 输入。所有来源对照只支持有界历史开发比较,不构成
SciRel 专家认可或来源资格重认。原始比较与专家决策请求见
[候选文档](../../review_candidates/2026-09-25-dissociation-rates/review.md)及其
[比较清单](../../review_candidates/2026-09-25-dissociation-rates/README.md)。

## 关系族选择

本批次兑现 r46/r49 缓付清单中的解离速率族:氢分子与其离子的九个电子碰撞
通道速率(H₂ 五叶:H(1s)+H(1s)、H(1s)+H(2s)、H(1s)+H(n=3)、H₂⁺+H(2s)、
H⁺+H(1s);H₂⁺ 四叶:p+p、H⁺+H(1s)、H⁺+H(n=2)、H(1s)+H(n) 解离复合)。对照
r53 基线(`e3f2ebe`,81 资产 dev26)与未发布候选池:无任何解离/复合速率资产,
九个保存叶均为**新增能力**;按科学语义(输入、模型、输出)判重,不按名称。保留
的区分:九叶为兄弟身份不合并——每通道是物理上不同的速率,各有独立冻结系数表。
九叶形状完全统一(temperature-only 九系数对数多项式、源 Horner 序、裁剪
[0.1, 2.01e4] eV、×1e-6),故以共享模板生成模块/测试/文档,系数用
`repr(float(v))` 位精确往返从 SHA-256 绑定的保存实现抽取(规避 r49 COLLRAD
转录错误类),四个生成器脚本纳入 proposal 以供审计。来源树只读:全部导入
`python -B` 且显式 `PYTHONDONTWRITEBYTECODE=1`,本轮对保存树零写入。

## 九项资产与有据修复

统一修复(九叶相同,各保存文档声明而实现未执行):**非正温度拒绝**(保存实现
静默裁剪入域);裁剪端点、Horner 求和序与 ×1e-6 缩放逐位保留。各保存文档另含
"能量必须非负"样板句但无能量端口——后继如实声明 temperature-only 合同,不虚构
能量端口。

资产 82–90(资产 ID、通道与保存实现 SHA-256 见候选清单 README 表):callables
`evaluate_hydrogen2_h1s_h1s_dissociation_rate`、
`evaluate_hydrogen2_h1s_h2s_dissociation_rate`、
`evaluate_hydrogen2_h1s_hn3_dissociation_rate`、
`evaluate_hydrogen2_h2p_h2s_dissociation_rate`、
`evaluate_hydrogen2_p_h1s_dissociation_rate`、
`evaluate_h2_plus_two_proton_dissociation_rate`、
`evaluate_h2_plus_p_h1s_dissociation_rate`、
`evaluate_h2_plus_p_hn2_dissociation_rate`、
`evaluate_h2_plus_h1s_hn_dissociative_recombination_rate`。

## 科学证据(独立探针,PYTHONDONTWRITEBYTECODE=1)

- 失败回归先行以显式序列证明:移除九个新模块后 18 个新测试文件收集期
  **18 errors ImportError**,恢复后 **81 passed**。
- 逐文件测试计数以 `pytest --collect-only` 记录:直接 6×9=54,复放 3×9=27,
  合计 81。
- 独立 oracle:`np.polynomial.polynomial.polyval` 同表重算,rtol 1e-12;裁剪
  端点逐位相等;标量→0-d、非正/非有限拒绝均断言。
- **双臂复放**(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,九个实现文件分别
  SHA-256 绑定):一维/二维网格全部 `assert_array_equal` **逐位复现**;九份
  非正温度修复差分见证(保存实现返回端点裁剪值,后继拒绝)。27 passed。
- 保存包自身证据(各 operator.md 源锚、包级 oracle)作为有界历史对照引用。

## 开发验证(r54 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1209 passed,
  43 skipped**;计数断言 81→90、包级 `__all__` 更新,无既有数值断言弱化。
- 90/90 exact documents 源码态校验通过。
- 内部 wheel `scirel-0.1.0.dev27-py3-none-any.whl`(SHA-256
  `7768b32bbc95bb0b36604bde6d89fd0543deaf656d906d1f2b765f6ce7b00e03`);开发
  catalog `complete: 90/90`,root digest
  `sha256:2399fdbcae4fc8c7e6b0147d964548d3e1556a4803317c21401194e05b99d344`。
- 干净离线 venv(fresh `build/venv-r54-clean`,wheelhouse 与 r31 记录逐哈希
  一致,`--no-index --no-deps --force-reinstall` 安装 wheel,`python -I` 隔离
  探针确认 `scirel` 解析到 venv site-packages):r45 文档化 source-free 子集
  **927 passed, 43 skipped, 0 failed**;全 tests 树 **1206 passed, 46 skipped,
  0 failed**;安装态文档校验 **90/90** 通过(`runtime_origin: installed`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、九个拟合对外部原子物理参考(AMJUEL/HYDHEL、
  Janev-Smith 原始表等)的正确性(`validation_oracle_gap` 残余原样保留)、调用方
  输入的物理有效性、专家认可、可信晋级或公开发行。
- KN1DPy 其余叶节点(壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS
  组装、SIG 矩阵组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`;来源文件无许可证声明。
- 专家需决定的五项问题见候选文档;冻结待审说明见
  [r54 评审说明](review-version-2026-09-25-r54.md)。
