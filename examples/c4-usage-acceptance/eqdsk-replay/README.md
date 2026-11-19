# 单任务复跑：扩展 EQDSK 的首读、写回和重读

这是对[冻结清单](../tasklist.json)中 `io-eqdsk-roundtrip` 的定向复跑，不是重跑整个 C4。历史 [round2](../round2/tasks/io-eqdsk-roundtrip.json) 和 [closeout](../closeout/tasks/io-eqdsk-roundtrip.json) 的 writer、G-EQDSK reader 都实际抛了 `FileNotFoundError`；扩展 EQDSK 的 reader 未被调用。在 `aaadca04` 的干净分发包上运行原装置也复现了这两次异常。#349 修过局部变量初始化，`tests/io` 有独立的格式和读写测试，但它们都不是这条分发包消费链。

## 根因与判据

合同示例在临时目录中产生文件，示例退出后文件就不在了。原装置把新路径放进签名没有的 `path`，参数重建丢掉它，writer 实际收到已过期的 `filename`；G-EQDSK 读者也重用了过期的文件名。即使第一处成功，原装置比较的也是调用参数（`data`、`filename`），不是首读的字段。

[当前装置](../closeout/checks/batch2.py) 在示例的真实调用点捕获输入字节，不改数值。每次在新的空目录还原首读输入，使用真实 `filename` 将首读结果写到另一文件，writer 正常返回且新文件非空才重读。G-EQDSK 用自己合同的输入，**不**读取扩展方言的写出文件。两次解析之间比较键、形状、字符串、有限数值；`rtol=1e-9, atol=0` 来自冻结清单，不从实测拟合。`changed` 记录精确值发生变化的字段，`mismatches` 记录超出预算等差异。

逐键比对是回答这个夹具的“有没有掉字段/变数值”，**不等于下游业务需要逐个命名这些输出**，也不证明物理正确、现场文件兼容、或其余 C4 任务通过。字段名判据仍按原 `check_fields` 独立报告：读回成功不能证明返回键集等于包装名 `mapping`，文件副作用也不是名为 `file` 的返回键。`run.py --task` 的退出码只代表回执读回；结果看 `criteria` 和 `package_sufficient`，不能只看退出码。

## 已观测的结果

包源 `aaadca04` 的[原始单任务回执](aaadca04.json)保留了 6 次正常返回。扩展 EQDSK 的首读输入与写出都是 630 B，SHA-256 相同；夹具 22 个键无增删，头、坐标、剖面和网格无变化，最大相对偏差为 0（非零参考值）。额外用 `EQDSK(fname="roundtrip.eqdsk")` 打开写出文件，只取 `title` 和 `psi`，读得填充至 48 字符的 `MANUAL EXAMPLE` 与 `[[1, 2], [3, 4]]`；这是对象的实际消费证据，而不是冻结判据，也不是 22 个键都有业务需求的证明。原来的空构造和字段名判据保留，`package_sufficient` **仍为 false**。装置 `selfcheck.py` 的 22 项自检通过，包括残件抑制和变异敏感性。这些不是发布档门禁证据。

### #420 合入后的冻结包

[冻结回执](c8faa8e7.json)来自包源 `c8faa8e7`（wheel SHA-256 `2ea25bbd8d8050b11772c6f87b16b115f2b7690439424685fe036145b7c5db1d`），由装置 `485147df` 在空运行目录中、使用该包的独立解释器执行。6 次真实调用全部正常返回，输入和写出文件仍为相同的 630 字节；对象实际读取的 `title` 和 `psi` 与上一包相同。装置自检再次 22/22 通过。

| 判据 | 状态 | 实际观测 |
|---|---|---|
| `fields_first_read`、`fields_read` | fail、fail | 两次都直接返回字段字典（22 个键），没有名为 `mapping` 的包装键。 |
| `fields_write` | fail | writer 写出文件，Python 返回 `None`，不是合同名 `file` 对应的返回值。 |
| `fields_geqdsk` | fail | 标准方言的独立示例直接返回 `psirz`、`r` 等键，不是单键 `mapping`。 |
| `fields` | fail | 保留的 `EQDSK()` 空构造没有键；附加的有文件构造观测不替换此判据。 |
| `roundtrip`、`budget` | pass、pass | 22 个夹具键无增删、变值或形状变化；非零参考最大相对偏差为 0。 |
| `readback` | pass | 重新打开本轮回执，确认首读、写出和对同一写出路径的重读均被记录。 |

故本轮是 **3 个判据通过、5 个字段判据失败，`package_sufficient=false`**；没有把文件写成功记作字段合同达标。

## 复现（与其他 worktree 的独占发布时间错开）

从干净的包源提交构建；如需重放旧包，可分别在包源与装置提交准备包和装置。下面的路径都在当前 checkout，先选一个不存在的运行目录，以免写进历史回执。

```sh
set -eu
p=.runtime/eqdsk-replay-$(git rev-parse --short HEAD)
test ! -e "$p"
python3 scripts/dev.py prepare
python3 scripts/dev.py run uv build --wheel --out-dir "$p/wheel"
python3 scripts/dev.py run python -B scripts/build_pure_delivery.py \
  --wheel "$p"/wheel/*.whl --output "$p/delivery"
python3 scripts/dev.py run uv venv --python 3.14.7 "$p/consumer"
python3 scripts/dev.py run uv pip install --python "$p/consumer/bin/python" \
  "$p"/delivery/wheel/*.whl -r "$p/delivery/runtime-requirements.txt"

# 消费者只得到包、隔离 venv、题面和装置，不复制源码、测试或历史结果。
h=examples/c4-usage-acceptance
r="$p/replay"
mkdir "$r" "$r/closeout"
cp "$h/tasklist.json" "$r/"
cp "$h/closeout/"{run,harness,selfcheck,audits}.py "$r/closeout/"
cp -R "$h/closeout/checks" "$r/closeout/"
export SCIREL_PACKAGE_ROOT="$PWD/$p/delivery"
python3 scripts/dev.py run "$p/consumer/bin/python" -IB "$r/closeout/run.py" --task io-eqdsk-roundtrip
python3 scripts/dev.py run "$p/consumer/bin/python" -IB "$r/closeout/selfcheck.py"
```

单任务输出在新 `replay/closeout/tasks/io-eqdsk-roundtrip.json`；其中包含包源 revision、wheel/snapshot SHA-256、实际导入位置、逐次调用、输入和写出文件的指纹、比较和重新打开回执的结果。自检故意让 writer 留下文件再抛错，并破坏零值、键和形状，检查这些情况不能拿到往返通过。
