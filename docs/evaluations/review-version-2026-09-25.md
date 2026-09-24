# 首次开发版本科学审核说明

状态：**待审材料，尚不满足可信版本晋级或公开发行**。本说明随确切 Git 提交、内部 wheel、开发 catalog 和测试证据冻结；专家意见必须引用该确切版本。任何实质修改都形成 successor，不改写原快照。

## 审核基线与范围

SciRel 尚无经专家认可的可信版本。因此，首次可信版本审核的科学范围是本开发版本的全部公共科学资产，而不是与上一开发提交的代码 diff。当前资产索引有 **63 个公共资产（51 个 Operator、12 个 TaskGraph）**；`catalog/examples` 只有 **15 个**有效的 `scirel.asset-document.v1` 文档，开发 catalog 明确为 `partial: 15/63`。其余 **48 个**资产尚无可用于该版本审核的 exact document，不能凭历史来源台账或函数名补齐，也不能借本次冻结宣称已获科学认可。

上一开发提交 `f3a03fa` 到本切片的新增科学关系是 `scirel.geometry.planar-wavevector-projection`。这项开发增量及 PDRF/PDRK 来源比较、适用域和未吸收功能见[平面波矢整合记录](intake-2026-09-25-planar-wavevector.md)。本切片没有重绑来源 TaskGraph，故新增算子的反向依赖为空；现有 12 个 TaskGraph 作为首次基线仍需按各自科学合同与组合证据审核。`f3a03fa` 仅是开发比较点，**不是可信审核基线**。

## 可核查材料

- 文档：`catalog/examples/*.json` 中的 15 份 exact documents，冻结清单与逐文件摘要由待审 manifest 绑定。
- 代码和测试：manifest 的 Git commit/tree 绑定 `src/scirel`、`tests/operator_contracts`、`tests/graph_contracts`、`tests/framework_compositions` 及公共 API。波矢直接测试和保存 L1 比较分别为 `tests/operator_contracts/test_planar_wavevector.py`、`tests/operator_contracts/test_planar_wavevector_l1.py`。
- 来源：PDRF/PDRK 的本地候选包摘要与边界见平面波矢整合记录。尚缺绑定 source、skill、bundle 的严格 D1 冻结记录与独立审查回执，因此该增量目前只能作为临时开发实验输入。
- 工程验证：首个开发切片的 `pwsh ./scripts/check.ps1 -Mode affected` 为 82 passed、2 skipped；设置 `SCIREL_L1_ROOT` 后来源比较 2 passed；加入待审快照验证后的全仓 `-Mode affected` 自动升级为全套，结果为 796 passed、2 skipped。隔离安装的内容等价开发 wheel 为 13 passed、2 skipped，15 份文档的安装态运行时与示例校验通过。wheel 隔离于 SciRel 源码，但使用开发机已有科学依赖，不证明离线依赖闭包。

## 专家待决与阻断

1. 对 63 个资产建立可审核的 exact document、来源及直接/组合科学证据；现有 48 份缺口阻断首次整版认可。
2. 对新增波矢关系确认科学身份、`1/m` 输入约定、数值边界及与 PDRF/PDRK 的有条件重叠；严格 D1 交接到达后核对同一来源快照。
3. 对 12 个 TaskGraph 的依赖闭包、输入输出和物理组合逐项审视；自动测试成功不等于物理正确。
4. 许可证与公开发行条件尚未裁决。旧逐项 `approved` workflow 不授权整版可信；`scripts/check.ps1 -Mode release` 保持阻断。

专家可以请求补证、返工或排除资产。部分认可不能在当前仍含未认可内容的快照上直接贴可信标签；需先形成经过复验的新版本，再审其相对该首次待审版本及未来可信基线的确切差异。
