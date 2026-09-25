# SciRel 安装态验证修复 r50

状态:开发期冻结待审(`pending_unapproved`),不是领域专家认可、可信版本或公开发行。合格 L1 交付根开始与结束均复核为空。本版是 r49(`0035e9e3a0de143a8492fb3e5a0d3f418c2733f2`,快照 `build/verification/review-2026-09-25-r49-atomic-h-collision-data`)的 successor;科学代码零变更,`0.1.0.dev24` 版本不变,内部 wheel 与 catalog 字节复用 r49(r47 docs/script-only 先例,复用声明见下)。

## 背景与缺口

r49 的干净 venv 记录取的是**全 tests 树**运行(1054 passed / 5 failed),且 `pyproject.toml` 的 pytest `pythonpath = ["src", "tests"]` 在默认调用下会把源码放进导入路径——不能据此宣称 source-free 科学测试通过。本轮按 r45 已记录的确证方法补齐:独立 venv、`--no-index --no-deps` 安装 dev24 wheel、`SCIREL_INSTALLED_RUNTIME=1`、`python -I -B -m pytest -o pythonpath= -p no:cacheprovider`、conftest 断言 `scirel.__file__` 位于 `sys.prefix` 下。

## 五项工程测试的定性

初判五项失败,深挖后实为**三个真实缺陷(修复)+ 一个被遮蔽的前提缺陷(修复)+ 两个命名阻塞(skip)**:

1. `tests/test_affected_test_selection.py::test_unicode_graph_evidence_path...`——`select()` 以 locale 默认编码解码 selector 子进程输出;`python -I`(-E)忽略 `PYTHONUTF8` 后父进程按 GBK 解码子进程的 UTF-8 输出,reader 线程崩溃,`json.loads(None)`。修复:显式 `encoding="utf-8", errors="replace"`。selector 脚本自身编码卫生已核(全部显式 UTF-8)。
2-3. `tests/test_release_environment.py` 两项——`subprocess.run(..., encoding="utf-8")` 硬编码,pwsh 本地化错误流含 GBK 字节(0xa1),UTF-8 reader 线程崩溃使 stderr 为 None。修复:加 `errors="replace"`(英文断言文本为 ASCII,替换后仍可匹配)。
4-5. `tests/test_admitted_distribution_builder.py` 两项 wheel 构建——`pip._vendor.pyproject_hooks...BackendUnavailable: Cannot import 'setuptools.build_meta'`:干净 venv 无 setuptools(r31 记录的依赖 wheelhouse 不含 setuptools wheel,冻结哈希集不得更改),嵌套 PEP 517 构建无法启动。按命名阻塞 skip(`skipif find_spec("setuptools") is None` + reason),非静默放宽。
6. (遮蔽项)`tests/test_asset_documentation.py::test_installed_runtime_mode_rejects_the_source_checkout`——其守卫仅在 `scirel` 解析到源码 checkout 时可触发;安装态全树运行中前提不成立(此前从未在安装态跑过该测试故未暴露)。修复:前提不满足时显式 skip 并注明守卫仅在源码态行使。

## 验证(两种环境,最终字节)

- **源码态全量门禁** `check.ps1 -Mode full`(L1 复放根已配置):**1059 passed, 43 skipped**,与 r49 数字一致——修复不改变源码态行为(skip 仅在安装态触发)。
- **干净离线 venv**(fresh `build/venv-r50-clean`,`include-system-site-packages=false`,wheelhouse 与 r31 记录逐哈希一致,`--no-index --no-deps` 安装 dev24 wheel):隔离探针确认 `scirel` 解析到 `site-packages`;**r45 文档化 source-free 子集**(operator_contracts + graph_contracts + framework_compositions + test_library_composition + test_public_surface,`SCIREL_INSTALLED_RUNTIME=1`,`-o pythonpath=`):**777 passed, 43 skipped, 0 failed**(43 项 skip 全为未配置历史 L1 路径的环境门控用例,真实 skip 不计通过)。
- **干净 venv 全 tests 树**:`**1056 passed, 46 skipped, 0 failed**`(46 = 43 环境门控 + 2 setuptools 命名阻塞 skip + 1 源码守卫 skip)。
- 安装态文档校验(`--installed-runtime`):**74/74** 通过,`runtime_origin: installed`。

## 产物与复用声明

- wheel `scirel-0.1.0.dev24-py3-none-any.whl` SHA-256 `a0c665a7d2920650fce832c448c49d4c866260daec0cba0102dd60e3e56c95a0` 与 catalog root `sha256:030f8a3704c5388e8d08d005ff8067129cb3f998926c37f7a9e0c5ce64974b90` **逐字节复用 r49 冻结值**:r50 只改 `tests/` 下四个测试文件,wheel 仅打包 `src/scirel`(逐字节未变),catalog 输入未变;freeze 的 wheel==committed-source 校验照常执行。r49 快照原样保留,其 manifest/test-evidence 中"5 failed"的全树记录由本说明更正,不改写 r49 字节。
- 变更文件:`tests/test_affected_test_selection.py`、`tests/test_release_environment.py`、`tests/test_admitted_distribution_builder.py`、`tests/test_asset_documentation.py`、本说明、test-evidence。

## 边界与待决

- 不宣称:合格 L1 消费、科学增量(r50 无科学变更)、专家认可、可信晋级或公开发行。
- setuptools 依赖阻塞保留为显式 skip;若未来需要闭合,须以独立决策扩充 wheelhouse 并重录哈希,不属于本轮。
- 许可证 `pending-human-decision`;无可信基线,首次专家审核仍覆盖全部 74 项资产。
