"""最小纵向切片：一次 SciReL 公开函数调用，可直接粘进 shell 运行。

在 CodeFusion 的 sandbox 里按顺序跑：

    python <分发包根>/tools/query.py --root <分发包根> describe   # 取 snapshot/wheel 的 pin
    python -m pip install <分发包根>/wheel/<wheel>
    python minimal_scirel_call.py --out result.json

退出码 0 表示拿到结果并写盘；非 0 表示失败，stderr 说清原因。
不重试、不降级、不把失败折成默认值——这是 SciReL 侧 fail-closed 合同的要求。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from scirel.kinetic import assemble_neutral_total_collision_frequency


def main() -> int:
    parser = argparse.ArgumentParser(description="最小 SciReL 调用，写一份结果交付物。")
    parser.add_argument("--out", type=Path, required=True, help="结果文件路径")
    args = parser.parse_args()

    alpha = assemble_neutral_total_collision_frequency(
        [1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], np.ones((2, 2, 2))
    )
    args.out.write_text(
        json.dumps({"alpha_m_inv": np.asarray(alpha).tolist()}, indent=2), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
