# SciRel 速度空间族可表示性合同修复 r48

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根仍为空,KN1DPy 保存包仅为 provisional 历史对照。本版是 r47 v2(`c69e1dec0d06cdd6104dded0982a974b1f43246c`,快照 `build/verification/review-2026-09-25-r47-contract-fix-v2`)的 successor;r47 v2 与更早快照原样保留。

## 反例核验(先精确验证实际行为,不预设结论)与修复

1. **quadrature 测度下溢为精确零**:`vr=[0.0, 1e-200], vx=[-1.0, 1.0]` 全部满足有限/非负/严格递增输入约束,但面的平方 `(0.5e-200)² ≈ 2.5e-401` 在 float64 下溢为 0,`radial_measure`、`radial_four_pi_measure`、`volume` 全为精确零——违反 exact document 的 strictly-positive 输出承诺(r47 只检查 isfinite)。修复:测度、four-pi 测度、dvx、体积四组承诺严格正的输出增加下溢检查,任一 `≤ 0` 即按 `ValueError("the quadrature <field> underflows to zero for these finite inputs")` 拒绝。
2. **seed 归一化分母下溢**:`1×1` 网格配 `volume=1e-320`、其余输入正常有限:加权分母相对 raw seed 次正常下溢,相除后 distribution 溢出为 **inf**——违反 finite/strictly-positive 承诺。修复:归一化后检查 distribution 全有限且严格正,否则 `ValueError("the normalized seed distribution is not representable for these finite inputs")`,归一化计算纳入 `errstate`。
3. **seed 归一化分母溢出**(monitor 假设的第二形态,按实核验):两单元 `volume=1.7e308` 使加权 raw-seed 求和确定性溢出,相除后 distribution **塌缩为精确零**、加权和为 0 而非 1——同样 fail closed。另核验了一个"部分溢出"情形(2×3 全 1.7e308 体积):实测分布为正次正规值且加权和 ≈1−6e-16,**未**违反文档承诺(机制依赖求和顺序,脆弱但不违约),故不为其虚构拒绝,只由上述结果级检查兜底。未扩大到无根据的全局规则。

失败回归先行:3 项新回归先失败后通过(下溢测度、分母下溢 inf、分母溢出零化)。正网格来源 parity 保持(双臂复放 9 passed 不变);普通输入数值逐位不变。

## 验证

- `tests/operator_contracts/test_cylindrical_velocity_quadrature.py` + `test_shifted_maxwellian_seed.py`:**57 passed**(54 既有 + 3 新)。
- `check.ps1 -Mode full`(最终字节,源码态全仓):**1013 passed, 52 skipped**。
- 71/71 文档源码态与干净离线 venv(`--no-index` wheelhouse,`python -I`)安装态校验通过;干净安装态 source-free 套件 **740 passed, 43 skipped**(L1 根已配置,复放真实运行)。
- 内部 wheel `scirel-0.1.0.dev23-py3-none-any.whl`,SHA-256 `7180bdbfb99c58ac8eef319ee86bbd9ee45318b6327f877788646820d4b37d3f`;开发 catalog `complete: 71/71`,root digest `sha256:1a811277db234a9ac88732ee461f2e6dcaa672a36d47fef8367e13bea75f5b35`。

## 边界

严格正测度/有限归一化的合同现在由结果级检查真实成立,不依赖调用方网格的"合理"量级;但网格与体积的物理有效性仍是调用方责任。合格 L1 根仍为空,KN1DPy 仍为 provisional;许可证、可信晋级、公开发行未完成;无可信基线,首次专家审核仍覆盖全部 71 项资产。
