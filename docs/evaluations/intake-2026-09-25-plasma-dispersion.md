# 等离子体色散函数关系族开发整合

状态：**隔离开发关系，尚未经专家认可或公开发行**。2026-09-25 第一阶段交接称 PDRK、fluidBW 的停写候选目录已通过严格 D1 冻结门禁及独立候选树审查；其 source/candidate tree 摘要、run 与证据上限记录在本次统筹的 `handoffs/extraction.md`。SciRel 的本地结构索引对七个目录读出 265 个 Operator、109 个 TaskGraph、0 个结构 gap，这不构成科学审核。保存的两个直接实现的 SHA-256 分别为 PDRK `b951764f0f4829874444c198dba94006aef000d69b94403915da57d933f2b131`、fluidBW `d16799ad771a5eb16dda2b3d41b40e49564c0fb1435bf086f71aa67d6b54ca16`；SciRel 索引内的整包摘要分别是 `sha256:c2979066d04938388444a221107a913b525de27e7bbf955e8f574b60370d669b` 和 `sha256:20c16c35c03255daa20595a2419bb80fad151a7e624531979be183a54bc2b09f`。项目级候选树摘要与 SciRel 包摘要采用不同清单算法，不混用为同一标识。

## 科学比较与行动

两份 L1 均计算无量纲复宗量的 `w(z)=exp(-z²)erfc(-iz)` 与 `Z(z)=i√π w(z)`，因此**数学关系重合**。但 PDRK 用可选 Weideman 阶数 `N`（默认 16），fluidBW 固定 64；PDRK 默认值在实轴有约 `1e-7` 的截断误差，fluidBW 还返回 `method` 和 `all_purely_imaginary` 实现诊断。这些不是 SciRel 标准函数的科学端口，不能把两份近似实现判为逐位等价或静默迁移其调用方。

SciRel 新增 `scirel.kinetic.plasma-dispersion-function`，用现有 SciPy 的 `wofz` 计算解析关系，返回 `w` 与 `Z`，不暴露来源算法阶数或分支标签。公共合同在[exact document](../../catalog/examples/scirel.kinetic.plasma-dispersion-function.json)，代码和测试分别在 `src/scirel/kinetic/plasma_dispersion.py`、`tests/operator_contracts/test_plasma_dispersion_function.py` 与 `test_plasma_dispersion_function_l1.py`。输入 `z` 必须由调用方按明确热速度/漂移约定预先归一化；PDRK 的 `(ω-kv_s0)/(kv_ts)` 与 fluidBW 的 `ω/(kvt)` 不在算子内互相转换。本次未接入任何来源 TaskGraph，也未声称复现整套动理学色散求解。

## 来源差异与有依据修正

- fluidBW 的 `operator.md` 将 `Z(0)` 写成 `iπ`，但其实现与直接来源回放在原点给出 `i√π`；SciRel 保留正确数学关系并对原点直接断言，不改写冻结 L1。
- PDRK 合同说 `N` 必须是正整数，实际代码 `int(N)` 会静默接受 `1.5`、`True` 或字符串；SciRel 不暴露该来源近似控制。
- 两份来源纯虚分支使用 `exp(y²)*erfc(y)`；在 `30j` 会有上溢乘下溢的非有限结果，SciRel 的 `wofz(30j)` 可有限表示。极深下半平面连解析值也可能超过 complex128 范围，SciRel 对非有限结果抛 `ValueError`，不返回部分数组。
- 这些源码差异是来源近似及实现边界的处置，不构成对两个项目全部科学功能的等价宣称。若未来用户明确需要 Weideman 阶数或来源诊断，可另立有界变体并审查其合同与直接测试。

## 验证与待决

新增直接测试覆盖原点、标量/数组、上下半平面、`30j`、非法输入和不可表示输出。保存 L1 比较在固定源文件摘要下核对 PDRK `N=32` 与 fluidBW `N=64` 的有限样本，分别要求 `w` 绝对误差不超过 `1e-12` 与 `1e-13`；另明确测试 PDRK 默认 `N=16` 与标准函数的非零差异。这些是有界数值对照，不是任意复宗量的来源逐位一致性证明。

专家仍需决定数学身份、允许的数值误差与适用域、来源许可证，以及是否保留来源近似作为独立能力。D1 严格冻结不代替上述 SciRel 科学认可；开发 wheel/catalog 也不得作为公开发行物。

## 后续 PDRK 来源范围更正

第一阶段于 2026-09-25 的后续 source-led census 发现 PDRK 的可执行 `old_version` EM3D/ES3D、`examples/coldplasma/pdrf_SI.m` 和 ES1D 极点阶数分支没有完整逐文件处置，遂撤回其当前合格 D1 交付资格。历史字节已移入 `D1待重审历史产物/PDRK-20260921-r2`，等待新严格冻结；上文原始交接判断仅反映当时证据，不再证明 PDRK 整项目提取闭合。保存实现的有界数值比较仍可作为开发证据，不能称为合格 D1 对照。fluidBW 的当前 D1 资格不受此更正影响；原 `f311a34` 待审快照保持不改，后续版本以本更正为准。
