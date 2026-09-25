# SciRel 干净离线安装验证 r45

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根仍为空,KN1DPy 保存包仅为 provisional 历史对照。本版是 r44(`fd2e9981adb1b5606173318d2429814e0d02444d`,快照 `build/verification/review-2026-09-25-r44-review-scope-failopen-fix`)的 successor;既有各快照原样保留。

## 本轮增量(纯验证,无任何科学/工程代码变化)

r42 轮的安装态验证(101 passed)使用 `--system-site-packages` venv 复用宿主科学依赖,留下一个明确证据缺口:当前 69 资产尚未在不继承宿主科学依赖的环境做 source-free 验证。本轮按 r31 首选快照(`build/review-version-20260925-45c1b76/test-evidence.md`)记录的本机 wheelhouse 与方法补齐,未修改任何 `src/scirel`、exact document、测试断言、wheel 或 catalog 字节:

- **环境**:Python 3.14.3,`python -m venv build/clean-dev20-venv` 产生 `include-system-site-packages = false` 的全新隔离目录。
- **安装**:`pip install --no-index --find-links build/dependency-wheelhouse <dev20 wheel> "pytest>=7"` 退出 0,安装 SciRel 0.1.0.dev20、NumPy 2.5.3、SciPy 1.18.1、pytest 9.1.1 及 pytest 依赖;wheelhouse 的 8 个 wheel SHA-256 与 r31 冻结证据记录逐项一致。
- **隔离探针**(`python -I`):`scirel`、`numpy`、`scipy` 均解析到 `build/clean-dev20-venv/Lib/site-packages`,无任何包解析到仓库 `src` 或宿主 site-packages。
- **source-free 科学/组合/公共入口套件**(`SCIREL_INSTALLED_RUNTIME=1`、`PYTHONDONTWRITEBYTECODE=1`、`python -I -m pytest -q -o pythonpath= -p no:cacheprovider tests/operator_contracts tests/graph_contracts tests/framework_compositions tests/test_library_composition.py tests/test_public_surface.py`,测试文件读自仓库、包加载自 wheel):**674 passed, 46 skipped**。46 项 skip 全部是未配置历史 L1 路径的环境门控用例(含 KN1DPy 复放 3 项),保持真实 skipped,不算通过。
- **exact document 安装态校验**:`--installed-runtime` 对 **69/69** 份文档通过运行时签名与可执行示例检查(`runtime_origin: installed`)。
- **用户验收**:`python -I examples/user_acceptance.py --wheel <dev20 wheel> --output build/clean-dev20-acceptance` 三项任务(green_field_synthesis、quasineutral_profile、pressure_state_and_residual)全部通过;报告核对 wheel SHA-256 `0e85f236526b6b664d44a177b7a0a42f87d52613f2024e73d10c6eceecf9aa11` 与 83 个已安装 SciRel Python 文件;报告 SHA-256 `646ff36337b976c639e4243240d9bEB34D4134F4BE24F34D873737F38EA9D6E4`。输出极值:极向场 `0.0011919294762389654 T`、平行压强 `4.88 Pa`、垂直压强 `6.38 Pa`、Picard 磁通残差 `0.0008247102878123478`。
- **来源提交差异与复用声明**:dev20 wheel 与 catalog 由 `813c45f` 构建并在 r42/r43/r44 跨纯文档与脚本提交字节复用(`scripts/` 与 `docs/` 不入 wheel);本轮冻结由 freeze 校验 wheel 模块与本提交 `src/scirel` 逐模块一致。r42 轮的源码态门禁 `942 passed、46 skipped` 与 `--system-site-packages` 安装态 `101 passed` 仍对未变运行代码有效,本轮不重跑源码态套件。

## 边界

wheelhouse 下载阶段使用开发机本地代理,本验证只证明 `--no-index` 安装后 wheel 在不继承宿主科学依赖的环境可运行;不证明完全离线的发布链路、跨平台行为、L1 源码 parity、科学认可、许可证、可信晋级或公开发行。46 项 skip 的历史 L1 对照(含 KN1DPy provisional 复放)不在本环境范围内。`scripts/review_scope.py` 的 r43→r44 归属修复属工具层,不在 wheel 内。
