# C5 交付包验收

这是 #C5「打出一个真实的对外交付包并独立验证它」的可复跑记录。它包含三样东西：

1. [receipt.json](receipt.json) —— 打出来的包是什么、装进隔离环境后校验通过的回执（wheel 与包内 `runtime.json` 的 sha256 逐字相同）；
2. [tasks/](tasks/) —— 三个**只用这个包**完成的物理任务，每个一份 `solve.py` 与一份 `solve.result.json`；
3. [GAPS.md](GAPS.md) —— 分级缺口清单，包括包里**完全没有**的能力。

包本体和 wheel **不进仓库**：`build_pure_delivery.py` 的产物有 6.8 MB，wheel 有 925 KB。回执里写 sha256 与完整命令，任何人从同一提交重打一遍就能逐字节比对。放进 git 的只有回执、任务与结论。

## 为什么放在 `examples/`

`examples/` 是仓库里唯一「不随包分发、只用来检验流程」的目录（见 [../README.md](../README.md)）。C5 的题面与答案必须对消费者不可见，否则「独立消费者只拿新包」这个前提就不成立。放这里既不进包，也不会被 `scripts/build_pure_delivery.py` 收集。

## 从零复跑

全部命令在 clone 根目录执行。工具链用仓库自己的 `dev.py`，解释器和 uv 缓存在被忽略的 `.runtime/` 下。

```sh
# 0. 干净的临时 worktree（避免把本地协调文件带进包）
git fetch origin
git worktree add .worktrees/c5 -b agent/c5-package origin/main
cd .worktrees/c5
python3 scripts/dev.py prepare

# 1. 打出 wheel 与交付包
python3 scripts/dev.py run uv build --wheel --out-dir .runtime/c5/wheel
python3 scripts/dev.py run python -B scripts/build_pure_delivery.py \
  --wheel .runtime/c5/wheel/scirel-0.0.0-py3-none-any.whl \
  --output .runtime/c5/scirel-delivery-435cc9a1
```

期望（与 [receipt.json](receipt.json) 一致）：

| 项 | 值 |
| --- | --- |
| wheel | `scirel-0.0.0-py3-none-any.whl`, 925017 B |
| `wheel_sha256` = `artifact.sha256` | `4c64938e782db200775eaae92b35e883bc779d1e97b56ed108a894348ed4ed85` |
| `runtime.json.snapshot_sha256` | `7a6268653983b92dadab6e714b48550657c4088d6d128b6bf398012efc8671bc` |
| `source_revision` | `435cc9a1630fd001eb7d5bc34d1a4e85f6096c46` |
| `asset_count` | 249 |

包内合同数 = 249，与 `runtime.json.asset_count` 与源树 `catalog/examples/` 的 249 三者一致。注意包内目录叫 `catalog/contracts/`，**没有** `catalog/examples/`；导出时改了名。

```sh
# 2. 隔离 venv，只装包里的 wheel 与它自己的 requirements
UV_PYTHON_INSTALL_DIR=$PWD/.runtime/python UV_CACHE_DIR=$PWD/.runtime/uv-cache \
  uv venv --seed --python 3.14.7 .runtime/c5/venv-consumer
UV_PYTHON_INSTALL_DIR=$PWD/.runtime/python UV_CACHE_DIR=$PWD/.runtime/uv-cache \
  uv pip install --python .runtime/c5/venv-consumer/bin/python \
  .runtime/c5/scirel-delivery-435cc9a1/wheel/scirel-0.0.0-py3-none-any.whl \
  -r .runtime/c5/scirel-delivery-435cc9a1/runtime-requirements.txt

# 3. 校验（注意：不是 validate_extraction_package.py）
.runtime/c5/venv-consumer/bin/python -I .worktrees/c5/scripts/validate_installed_wheel.py \
  --expected-python 3.14 \
  --wheel .runtime/c5/scirel-delivery-435cc9a1/wheel/scirel-0.0.0-py3-none-any.whl \
  --catalog-root .worktrees/c5 \
  --source-revision 435cc9a1630fd001eb7d5bc34d1a4e85f6096c46 \
  --output .runtime/c5/installed-wheel-validation.json
```

回执判据：`status: PASS`、`errors: []`、`artifact.sha256` 等于 `runtime.json.runtime.wheel_sha256`、`package.in_source_tree: false`（说明装的是 wheel 而不是源码树）、`runtime.is_virtualenv: true`、`runtime.external_site_paths: []`。

**不要**用 `scripts/validate_extraction_package.py` 校验这个包：它校验的是 extraction kit 的布局，成员集合不同，对交付包会报一批 `structure: ... missing`，且没有 `stage=` 与 `RESULT SHA256`。用错命令得到的红，不是包的红。

```sh
# 3b. 包内清单自校验：runtime.json 的 274 条 sha256 逐字节重算
python3 examples/c5-delivery-acceptance/verify_package_manifest.py \
  --package .runtime/c5/scirel-delivery-435cc9a1
```

期望 `status: PASS`、`entries_verified: 274`、`contracts: 249`、`asset_count: 249`、无多余文件。仓库没有针对交付包本身的校验器（只有 extraction kit 与已装 wheel 两个），这个脚本只补那一格，不替代第 3 步。

```sh
# 4. 三个消费者任务（只读包内 catalog/ 与三个 usage skill）
#    在 clone 根目录执行；脚本放在本 worktree 里，所以路径带上 .worktrees/c5。
SCIREL_PACKAGE_ROOT=$PWD/.runtime/c5/scirel-delivery-435cc9a1 \
  .runtime/c5/venv-consumer/bin/python -I \
  .worktrees/c5/examples/c5-delivery-acceptance/tasks/mirror-ratio-mirror-point/solve.py
# 其余两个同理：geometry-coordinate-roundtrip、transport-closure-dimensions
```

每个脚本把自己的结果写到同目录的 `solve.result.json`。

## 三个任务

| 任务 | 用到的资产 | `package_sufficient` | 一句话结论 |
| --- | --- | --- | --- |
| [mirror-ratio-mirror-point](tasks/mirror-ratio-mirror-point/solve.py) | `scirel.mirror.loss-cone-spectrum` | **false** | 损失锥角度谱算子本身精确到 1e-15，但镜比 R_m、损失锥角、镜点位置**包里没有算子**，是消费者自己写的 |
| [geometry-coordinate-roundtrip](tasks/geometry-coordinate-roundtrip/solve.py) | `scirel.sampling.meridional-polar-forward`、`-inverse` | true | 位置与矢量往返误差 ≤ 4.5e-16，范数守恒，"θ 从 +Z 量向 +ρ"这个约定被判别算例确认 |
| [transport-closure-dimensions](tasks/transport-closure-dimensions/solve.py) | `scirel.neoclassical.bootstrap-coefficients`、`scirel.neoclassical.bootstrap-current` | true | 量纲自洽（Pa/(T·m) = A/m²）、两个通量约定等价、四个标度指数全部命中 |

每个任务的判据都在脚本顶部**先写死**，再运行；容差写在结果里，没有一条是看到结果后放宽的。`mirror-ratio-mirror-point` 的第一次运行里 C3/C4（我自己的 RK4 轨道积分）是红的，原因是步长取成了 `1e-6 s`，一次就越过了整个镜场——那是我的算例错，不是算子错；修正步长并让积分在塞面处停止后转绿。原始失败没有从记录里删除，说明写在脚本的 docstring 与该任务的 `solve.result.json` 的 note 里。

## 这份记录不证明什么

- 不证明任何算子的**物理正确性**。`validate_installed_wheel` 的绿说明产物能装、能 import、公开面对得上 catalog；科学评审在 `catalog/review/`。
- 不证明检索完备。`runtime.json` 自己声明 `completeness: unknown`、`scientific_applicability: not_assessed`。
- 不证明消费者任务可推广到 249 份资产。三个任务是有选择的，覆盖的是三个方向，不是覆盖率。
- `validate_installed_wheel` 跑在 macOS/arm64 上；跨设备结论仍要 Linux/amd64 抽查，那是另一件事。
