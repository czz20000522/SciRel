"""Regenerate the nine dissociation successor modules with robust
coefficient extraction (repr round-trip instead of text splice)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tmp_gen_diss_modules import CHANNELS, TEMPLATE  # noqa: E402
from tmp_regen_diss_tests import coeff_literal  # noqa: E402

SRC = ROOT / "src" / "scirel" / "collisions"
for zh_dir, module, callable_name, en_channel, anchor in CHANNELS:
    block = "_COEFFICIENTS = np.array(\n    [\n    " + coeff_literal(zh_dir) + ",\n    ],\n    dtype=float,\n)"
    content = TEMPLATE.format(
        en_channel=en_channel,
        anchor=anchor,
        callable=callable_name,
        coefficients=block,
    )
    (SRC / f"{module}.py").write_text(content, encoding="utf-8", newline="\n")
print("regenerated 9 modules")
