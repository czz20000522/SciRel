# KN1DPy Johnson-Hinnov 系数 B 样条族次数约定勘误记录(r58)

状态:**隔离开发版本,非可信版、非公开发行**。本批次是 r57 的**描述勘误
successor,无数值变化**:三个 Johnson-Hinnov 资产的全部数值输出与 r57 逐位
相同。合格 L1 交付根本轮未消费任何合格 L1 输入;保存树零写入
(`python -B` 且显式 `PYTHONDONTWRITEBYTECODE=1`);r57 冻结快照
(`build/verification/review-2026-09-25-r57-jh-coefficients/`)原样保留。

## 缺陷与独立验证

独立只读评审(Codex)发现:r57 的科学描述把执行面称为"三次/cubic/source
cubic order 4",而实现把值 4 传给 scipy 的 FITPACK `bisplev` 作
`kx=ky`,scipy 文档明确 `kx`/`ky` 是**次数(degree)**——执行面是四次
(quartic)面。本轮按三条独立证据复核确认:

1. **库文档**:安装的 scipy 中 `RectBivariateSpline` 文档
   "kx, ky : Degrees of the bivariate spline. Default is 3";
   `bisplev` 的 `tck` 含"the degree of the spline"。
2. **系数计数算术**:打包载荷几何(TKnot=16、DKnot=12、order=4、77 系数)
   在 degree 读法下 `(16-5)*(12-5)=77` 精确闭合;order(=degree+1)读法需
   `12*8=96`,不闭合。保存校验合同本身只在 degree 读法下自洽。
3. **数值见证**:独立 numpy Cox-de Boor 张量积求值(不用 scipy)在度 4
   下复现 `bisplev(kx=ky=4)` 至 ≤7e-15,含两个端点。

保存源自己的"cubic"标签是意图阶数陈述,不改变执行次数;矛盾源自保存包
自身的描述并被 r57 逐字继承。

## 变更与不变更

变更(仅描述):三个模块 docstring、三个 exact document
(summary/relation/definition/model/boundary/assumptions + 新增 degree
见证 scope 项 + 标签-次数差异 known-limitation)、三个直接测试文件的
docstring,以及每个直接文件各一条新见证测试
`test_the_executed_surface_is_degree_four_under_fitpacks_degree_convention`
(独立 Cox-de Boor 复现,rtol 1e-9;r/alpha 含右端点哨兵密度坐标)。

不变更:任何可执行算术、任何校验合同、任何错误消息、任何既有数值断言、
r/alpha 密度哨兵覆盖行为、s 消费密度行为;以及 r57 范围的证据文档
(`review-version-2026-09-25-r57.md`、`intake-2026-09-25-jh-coefficients.md`、
`build/test-evidence-r57.md`、r57 候选三件套及其 index 条目)——其原始字节
仍是 r57 快照的记录,由本 successor 取代而非静默改写。

处置:**描述勘误(审核材料与公共合同文本返工),非科学变更**;三个身份、
签名、无修复立场不变;标签-次数差异新增为开放专家评审问题。

## 开发验证(r58 当前状态)

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1274 passed,
  43 skipped**(r57 1271,+3 见证;skip 计数不变)。逐文件计数
  `pytest --collect-only`:直接 8+6+7=21,复放 4+4+4=12,合计 33。
- 96/96 exact documents 源码态校验通过(`--check-runtime
  --execute-examples`,`runtime_origin: source`,`examples_executed: true`)。
- 内部 wheel `scirel-0.1.0.dev30-py3-none-any.whl`(SHA-256
  `05504b0064a1917f6bf324cb20c3ca6af7cb8c2f59cdfadee73f505ba8131c4a`);开发
  catalog `complete: 96/96`,root digest
  `sha256:a082e641ebbed52a4ed2e871774549b933fb9e831fef056c0b109b917d172f60`。
- 干净离线 venv(fresh `build/venv-r58-clean`,`--no-index --no-deps
  --force-reinstall`,`python -I` 隔离探针确认 under-prefix):r45 文档化
  source-free 子集 **992 passed, 43 skipped, 0 failed**;全 tests 树
  **1271 passed, 46 skipped, 0 failed**;安装态文档校验 **96/96**
  (`runtime_origin: installed`,`examples_executed: true`)。

## 边界与待决

- 本轮不宣称:合格 L1 消费、系数表对外部原子物理参考的正确性、调用方输入
  的物理有效性、专家认可、可信晋级或公开发行。
- 开放专家问题新增第 1 项(标签-次数):预期关系是执行的四次面(本轮逐位
  保留)还是应由后继修复为真正的三次面(会改变输出、使 r57 复放对照失配、
  需新证据)。r57 的密度哨兵覆盖、两种载荷形式、系数数据资产准入等问题原
  样保留。
- 版本 `0.1.0.dev29` → `0.1.0.dev30`(docstring 属 wheel 字节);许可证
  状态均 `pending-human-decision`。冻结待审说明见
  [r58 评审说明](review-version-2026-09-25-r58.md)。
