# SciRel Johnson-Hinnov 系数次数约定勘误 r58

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r57(`f98bf5baab4c2aa8123d5d4896aa987ee40eda44`,快照 `build/verification/review-2026-09-25-r57-jh-coefficients`)的 successor;既有快照原样保留。合格 L1 交付根本轮未消费任何合格 L1 输入。

## 性质:描述勘误,无数值变化

独立只读评审发现并经本轮三线独立验证:r57 把三个 Johnson-Hinnov 资产的执行面描述为"三次/cubic/source cubic order 4",而实现把值 4 传给 scipy FITPACK `bisplev` 作 `kx=ky`,scipy 文档定义 `kx`/`ky` 为样条**次数(degree)**——执行面是四次(quartic)面。证据:(1) 安装 scipy 的 `RectBivariateSpline`/`bisplev` 文档;(2) 打包载荷几何的 77 系数计数只在 degree 读法下闭合((16-5)*(12-5)=77;order 读法需 96);(3) 独立 numpy Cox-de Boor 度 4 求值复现 `bisplev` 至 ≤7e-15(含端点)。保存源的"cubic"标签是意图阶数陈述,不改变执行次数。

三个资产身份、签名、校验合同、错误消息、r/alpha 密度哨兵覆盖、s 消费密度均不变;全部数值输出与 r57 逐位相同,r57 复放对照仍有效。r57 范围证据文档与候选三件套原始字节保留(由本 successor 取代,不静默改写)。

## 变更清单

- `src/scirel/collisions/hydrogen_jh_{r,s,alpha}_coefficient.py`:docstring 表述(代码不变)。
- 三个 exact document:summary/relation/definition/model/boundary/assumptions 措辞 + 新增 degree 见证 scope 项 + 标签-次数差异 known-limitation。
- 三个直接测试文件:docstring 措辞 + 各一条新见证测试 `test_the_executed_surface_is_degree_four_under_fitpacks_degree_convention`(独立 Cox-de Boor,rtol 1e-9;r/alpha 含右端点哨兵坐标)。
- 其余 93 个 exact document 仅机械 `implementation_version` 提升;版本 `0.1.0.dev29` → `0.1.0.dev30`(docstring 属 wheel 字节)。

## 科学证据

- 逐文件测试计数以 `pytest --collect-only` 记录:直接 8+6+7=21,复放 4+4+4=12,合计 33(r57 30,+3 见证);复放测试字节与计数不变。
- 独立见证:无 scipy 的 numpy Cox-de Boor 张量积求值在度 4 下复现模块输出(rtol 1e-9),含 r/alpha 右端点哨兵密度坐标与 alpha +0.25 构造偏移。
- r57 的双臂 SHA-256 复放对照继续全部通过(比较臂字节未变)。

## 验证

- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1274 passed, 43 skipped**。
- 96/96 文档源码态与干净离线 venv 安装态(`--installed-runtime`)校验通过,均执行示例。
- 干净离线 venv(fresh `build/venv-r58-clean`):r45 文档化 source-free 子集 **992 passed, 43 skipped, 0 failed**;全 tests 树 **1271 passed, 46 skipped, 0 failed**。
- 内部 wheel `scirel-0.1.0.dev30-py3-none-any.whl`,SHA-256 `05504b0064a1917f6bf324cb20c3ca6af7cb8c2f59cdfadee73f505ba8131c4a`;开发 catalog `complete: 96/96`,root digest `sha256:a082e641ebbed52a4ed2e871774549b933fb9e831fef056c0b109b917d172f60`。

## 边界与待决

- 不宣称:合格 L1 消费、系数表对外部原子物理参考的正确性(`validation_oracle_gap` 原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- 开放专家问题:预期关系是执行的四次面(本轮逐位保留)还是修复为真正三次面(会改变输出、使 r57 复放失配、需新证据);r57 的密度哨兵覆盖、两种载荷形式、系数数据资产准入、包内 Saha 域边界差异等问题原样保留。
- KN1DPy 其余叶节点(辐射诊断组合批、壁面/源序列、自适应网格、跨网格插值、BoltzmannRHS 组装、SIG 矩阵组装等)继续缓付。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 96 项资产。
