# SciRel KN1DPy 跨网格分布插值 r62

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。本版是 r61d(`4c1236b592cd29e34d50901b131d3748af23d2f2`,快照 `build/verification/review-2026-09-27-r61d-evidence-disclosure`)的 successor;既有快照原样保留。合格 L1 交付根本轮复核为空,未消费任何合格 L1 输入。

## 性质:一项新 operator(跨网格分布插值)

`scirel.kinetic.cross-mesh-distribution-interpolation`
(`interp_distribution_across_mesh`;源锚 `KN1DPy/interp_fvrvxx.py`,
消费点 `kn1d.py:439、475-476` 的 N5 H↔H2 外层 handoff;保存实现文件
SHA-256 `c93f491369b36e237c35c10528a82af9f33de2db730f9a3a8054dace6dca5a43`)。

4-D cell-overlap volume weights 把分布从 mesh_a 速度空间转移到 mesh_b,
x 空间线性插值,可选保存的 AN/BN 矩校正循环,密度重缩放。保存 formal
operator 无 cache/w_new 分支,与 stateless port 逐位一致;原始源的 cache
lifecycle 不在保存 formal 包中,cache-state parity 不在本轮声明范围。

## 声明的域收紧(r62 预审)

1. **六轴单调性 + 最少 2 节点**:保存臂只检查 vr_a/vr_b 单调性;
   x_a/x_b/vx_a/vx_b 单调性和最少节点数未验证(单节点 vx_a 在校正分支
   触发 raw IndexError)。本 asset 对六轴均做校验,named ValueError。
2. **Tnorm 有限性**:保存臂只检查 Tnorm <= 0,NaN/inf 通过;本 asset
   要求 finite and positive。
3. **合法域内逐位一致**;声明域外的收紧由回归测试钉死。

## 变更清单

- 新增 `src/scirel/kinetic/cross_mesh_distribution_interpolation.py` 与导出。
- 新增 1 份 exact document + 其余 112 份机械 `implementation_version` 提升;`0.1.0.dev34` → `0.1.0.dev35`。
- 新增 2 个测试文件(`test_cross_mesh_distribution.py` 7 direct + `test_cross_mesh_distribution_l1.py` 3 replay)。
- 新增候选三件套 `review_candidates/2026-09-27-mesh-seam/`、index batch r62(11 条)。
- `provenance/admitted-assets.json`、`src/scirel/_validation.py`、
  `src/scirel/_composition.py`:字节零变化。

## 科学证据

- 独立解析梯形环面积(`pi*(edges[1:]^2 - edges[:-1]^2)`)作为 oracle,
  与实现分离,任一方的错误都会暴露为 mismatch。
- 矩目标断言:mesh_b 上的密度矩等于 mesh_a 密度 profile 插值到 mesh_b
  x 节点(rtol 1e-9);vx 对称输入的轴向流速为零(atol 1e-12)。
- 双臂复放(环境门控,SHA-256 绑定):两种 correct 分支、两组 mesh 尺寸、
  重复调用,全部 `assert_array_equal` 逐位复现;拒绝行为双臂一致。

## 验证(全部 pwsh 7.6.6)

- 源码态全仓:**1381 passed, 43 skipped, 0 failed**(r61d 1371,+10;log line `1381 passed, 43 skipped, 7 warnings in 203.25s`)。
- 113/113 文档源码态与安装态校验通过,含示例执行。
- 干净 venv `build/venv-r61-clean`:安装态全树 **1256 passed, 168 skipped, 0 failed**(log line `1256 passed, 168 skipped, 7 warnings in 172.55s`)。
- catalog `build/catalog/r61c`:`complete: 113/113`,root digest
  `sha256:7229960b5a4717158ab23e839299f8f9c857fa6f653c2480fb46c8578ef14563`。
- 内部 wheel `scirel-0.1.0.dev35-py3-none-any.whl`,SHA-256
  `a44ff74918465bf33bc6c5910a7e6d715d0e7a02e92f1b17f5220150b0b46e45`。

## 边界与待决

- 不宣称:合格 L1 消费、对外部物理参考的正确性、专家认可、可信晋级、公开发行。
- r61 同路径覆盖/删除事件已在 r61d 证据中披露;路径纪律已修正(本快照在全新路径)。
- 许可证状态均为 `pending-human-decision`。
