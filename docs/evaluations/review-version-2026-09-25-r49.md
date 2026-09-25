# SciRel 原子氢碰撞数据族整合 r49

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根(`D:/Users/26569/Desktop/归档_项目/codefusion/最小闭环压测环境`)本轮开始、来源纠正与结束均复核为空,未消费任何合格 L1 输入。本版是 r48(`dbb4385b2ec428c04c8706a484694d598ad14412`,快照 `build/verification/review-2026-09-25-r48-representability`)的 successor;既有快照原样保留。

## 科学增量(三项新增资产,KN1DPy 原子氢碰撞数据族)

r46 缓付的"电荷交换速率系数等叶节点"批次按证据兑现。对照 r48 基线与未发布候选池,三个保存叶均为新增能力;两 CX 叶保持姊妹关系不合并(速率系数拟合不是截面的 Maxwellian 平均,平均关系仍由 r41 资产承担,组合测试覆盖截面叶作为其 `cross_section_m2` 端口),COLLRAD 叶为电子撞击过程。

1. **`scirel.collisions.atomic-hydrogen-charge-exchange-cross-section`**(`evaluate_atomic_hydrogen_charge_exchange_cross_section`):源锚 `KN1DPy/sigma/sigma_cx_h0.py:7-32`(实现 SHA-256 `af55e393c0e7510a0c1734eabc2a635374c1dfe2ec8dcc3ae87386772a80b099`)。Janev 九系数对数多项式与 Freeman–Jones 解析分支,源裁剪逐位保留。修复:负能量拒绝、标量分支选择器(保存文档声明而实现未执行)。
2. **`scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient`**(`evaluate_atomic_hydrogen_charge_exchange_rate`):源锚 `KN1DPy/sigma/sigmav_cx_h0.py:8-95`(实现 SHA-256 `9a0037c238cc9fc99eabfa17984368d954c56ef9aa651e47967b5b1c273a1bfa`,ledger N25)。9×9 双变量对数多项式,源求和顺序逐位保留。修复:非正温度与负能量拒绝。
3. **`scirel.collisions.collrad-h0-ionization-rate`**(`evaluate_collrad_h0_ionization_rate`):源锚 `KN1DPy/collrad_sigmav_ion_h0.py:16-217`(实现 SHA-256 `2cd665e788e1444d60a4d7ca4b0e95fd76fd651b8a12653f7969aba8b9939bf1`)。冻结 15×60 表 log(rate) 双线性插值、端点裁剪与非降序配对坐标合同保留。修复:等形输入与保形输出(保存实现一律展平)。COLLRAD 表以机械抽取校准,`np.array_equal` 逐位一致;手转录的 9 处差异被逐位比较发现并全部消除。

## 来源只读纠正(2026-09-26)

本轮早期探针无 `-B` 导入保存实现,在 COLLRAD 保存目录写入一个 `__pycache__` 字节码缓存(2026-09-26 01:00:59 +08:00)。已可恢复隔离至 `build/quarantine/2026-09-26-collrad-saved-operator-pyc/`(pyc SHA-256 `c1b099d36acc5a65f1cbf0796cee6b148d9bb0ab8cdbb8f71bf95407671cdbd5`,含 record.md);移动前后保存 `scientific_operator.py` SHA-256 均为 `2cd665e7…`,源文件逐位未变;其余三个早期 pyc 未触碰。此后所有 import/pytest 一律 `python -B` 且显式 `PYTHONDONTWRITEBYTECODE=1`,来源树无新写入。

## 科学证据

- 独立 oracle:`polyval2d` 速率拟合、几何均值中点与网格锚点、闭式重算双分支,rtol 1e-12/1e-15;裁剪端点逐位相等。
- 双臂复放(环境门控,`SCIREL_KN1DPY_REVIEW_ROOT`,三个实现文件分别 SHA-256 绑定):全部 `assert_array_equal` 逐位复现,含四份修复差分见证;16 passed。
- 组合链:截面叶直接喂 `average_cross_section_over_maxwellian`,产有限正速率。
- 保存包 ledger `ACCEPT_OPERATOR` ×3 与 COLLRAD source-runtime 数据集验证(9 分区,max_rel 1.45e-14)作为有界历史对照。

## 验证

- 失败回归先行(3 errors ImportError);直接 + 复放 **37 passed**。
- `check.ps1 -Mode full`(源码态全仓,L1 复放根已配置):**1059 passed, 43 skipped**;计数断言 71→74、包级 `__all__` 更新,无既有数值断言或容差弱化(速率 oracle 测试避开双极端角的注释见测试文件;该角由 SHA 绑定复放逐位钉死)。
- 74/74 文档源码态与干净离线 venv(`--no-index` wheelhouse,`python -I`,安装态 `--installed-runtime`,`runtime_origin: installed`)校验通过。
- 干净安装态 tests 全树 **1054 passed, 43 skipped, 5 failed**:5 项均为环境绑定(旧 admitted 构建器嵌套 wheel 构建 ×2、release-environment 专用 python 探测 ×2、git-unicode 分类 ×1),在源码态全量门禁中全部通过,与本轮资产无关。
- 内部 wheel `scirel-0.1.0.dev24-py3-none-any.whl`,SHA-256 `a0c665a7d2920650fce832c448c49d4c866260daec0cba0102dd60e3e56c95a0`;开发 catalog `complete: 74/74`,root digest `sha256:030f8a3704c5388e8d08d005ff8067129cb3f998926c37f7a9e0c5ce64974b90`。

## 边界与待决

- 不宣称:合格 L1 消费、三个拟合或 COLLRAD 表对外部原子物理参考的正确性(`validation_oracle_gap` 残余原样保留)、调用方输入的物理有效性、专家认可、可信晋级或公开发行。
- 保存链其余叶节点(自适应网格、跨网格插值、分子 H2 全族、壁面/源序列、BoltzmannRHS 组装等)继续缓付,待后续按证据分批评估。
- 许可证状态均为 `pending-human-decision`。无可信基线,首次专家审核仍覆盖全部 74 项资产。
