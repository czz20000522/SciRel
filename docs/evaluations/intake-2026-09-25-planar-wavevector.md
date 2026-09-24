# 平面波矢开发整合记录

状态：**隔离开发版本，非可信版、非公开发行**。本记录对照保存的 PDRF/PDRK L1 内容；两项目尚未在本地取得绑定 source、skill、bundle、严格 `full_freeze` 与独立审查的完整 D1 交接回执，因此不能将本切片记为已核验冻结 L1 的正式接纳。

## 科学关系与行动

原始比较见[波矢候选分析](../../review_candidates/2026-09-24-pdr-wavevector/review.md)及其[库存快照](../../review_candidates/2026-09-24-pdr-wavevector/README.md)。PDRF 的平面投影与 PDRK 扫描器只有**有条件重叠**：在实波矢、`cwp > 0`、显式 `k_m_inv = par[0] / cwp` 和角度从度到弧度的映射后，极坐标数值关系可对照。PDRK 的扫描选择、对数开关、可变 `par`、零模长角度输出与负扫描模长不被吸收。PDRF 的归一化输入卡尚无已验证的 `1/m` 转换。

开发行动是新增 `scirel.geometry.planar-wavevector-projection`，不改接任何来源 TaskGraph。唯一精确科学合同为[asset document](../../catalog/examples/scirel.geometry.planar-wavevector-projection.json)；代码和直接测试分别在 `src/scirel/geometry/planar_wavevector.py` 与 `tests/operator_contracts/test_planar_wavevector.py`。该实现要求调用者预先提供 `1/m`，拒绝字符串/布尔值伪装的数值输入，Cartesian 模长使用 `hypot`，故在大分量处有意不同于来源的平方求和溢出。来源投影对照只证明所测实数域上的数值关系，不证明整个 PDRK 算子等价或物理模型正确。

来源标识保留为 PDRF `plasma_k_projection` package `sha256:4bbb3dcd7ced270e1f41405cae7b9c727a4e253c994dfda6021dea2781fd691a` 与 PDRK `wavevector_projection` package `sha256:71b1b7790849f2839b9792d0a401f5ea3fb5ed621097c873f7e037b9a39dfc70`。这两个包摘要是本地候选比较输入，不是 D1 独立冻结批准。反向来源图分别是 PDRF `fluid_dispersion_branch_sweep`，以及 PDRK `kinetic_dispersion_scan`、`pdrk_main_pipeline`；本次未重绑，未来若重绑须另证端口、状态和图测试。

## 开发验证

- 失败回归先确认新 callable 缺失；实现后 `pwsh ./scripts/check.ps1 -Mode affected` 选择该算子、公共导出、exact document 和历史集成边界，共 **36 passed, 2 skipped**。两项 skip 只因日常环境未设置 L1 根目录，不能当作来源对照成功。
- 在设置保存的 L1 根目录并核源文件 SHA-256 后，`test_planar_wavevector_l1.py` **2 passed**。旧候选另有七项更细的区分性比较；本记录不把它们扩大为严格 D1 冻结证据。
- 构建内部 `scirel-0.1.0.dev5-py3-none-any.whl`，SHA-256 为 `c1c1f4d8b865db5a14b5730b5afd94cf045f5a4846400ebd9696d27a5761307d`。在独立虚拟环境中以 `-I` 证明 `scirel.__file__` 位于该环境的 `site-packages`，不导入源码；安装态直接测试 **13 passed, 2 skipped**，15 条 exact documents 的运行时和示例校验通过。
- 内部开发 catalog 为 `partial: 15/63`，root digest `sha256:ffbf9e403a0507c513d6f4b54f12c2808ace7c19454e868cfa0d636abc81b185`。该 builder 输出是开发校验投影，不能交给用户运行时当作可信 release。

以上虚拟环境继承开发机已安装的科学依赖，只验证 SciRel wheel 与源码隔离，不证明声明依赖可由干净离线 wheelhouse 独立安装。公开发行许可证仍待人工决定。专家需审视科学身份、SI 输入约定、数值差异及适用域；第一阶段负责人还需补齐同一 L1 快照的严格冻结交接。当前仓库的逐项 `release` fixture 不能证明整版科学增量获认可，本切片不得调用它晋级可信版。

## 后续 D1 交接（不改写原开发判断）

在上述开发切片冻结后，第一阶段于 2026-09-25 提交独立审查交接。PDRF 的 source/candidate tree 摘要分别为 `55824a96fb3abdcf2ae75b15da853084fad64f603560e8523f494ee9979ffb76` / `c56a5adb17db1e3af020a74d63a04a00eab744c4f52dadba0afa1fb054ba0cb5`，PDRK 分别为 `7ceab1c6383a474ec55095c7ff19316db5c1b739855e495a6b325f0f110b39e4` / `fb84032458e0fd502ca4bdc60df6272b9c8d12cbdeae59c7f889a7fffa29a9d8`。本地候选目录仍为 35 文件/220532 字节与 52 文件/620505 字节，和交接审查的计数一致；`plasma_k_projection` / `wavevector_projection` 整包摘要与本记录上文一致。交接称两份停写候选已通过严格 D1 门禁和独立候选树审查；这关闭本记录原先的来源交接缺口，但**不**批准 SciRel 标准波矢关系或其 `1/m` 映射。原 `06c1122` 待审快照及当时证据保持原样，后续版本另作 successor。

## 后续 PDRK 来源范围更正

第一阶段后续 census 又发现 PDRK 原交接遗漏可执行源码分支，已撤回其当前合格 D1 资格，并把历史字节移到 `D1待重审历史产物/PDRK-20260921-r2`。上文冻结交接段是当时事实，不再作为当前完整来源闭合判断；PDRK 波矢对照仅是历史开发样本的有界映射。PDRF 仍属当前合格 D1 原料。旧 `06c1122` 待审快照不改写，新的 successor 审核应按此更正重新限定证据。
