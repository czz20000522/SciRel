"""Regenerate the nine dissociation test files and modules with robust
coefficient extraction: import the pinned saved module and emit each
coefficient via repr(float(v)), which round-trips bit-exactly."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAVED = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")

sys_path_note = "regen"


def load(zh_dir):
    src = SAVED / zh_dir / "scientific_operator.py"
    spec = importlib.util.spec_from_file_location("saved_" + str(abs(hash(zh_dir))), src)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def coeff_literal(zh_dir):
    module = load(zh_dir)
    values = [float(v) for v in module._COEFFICIENTS]
    return ",\n    ".join(repr(v) for v in values)


from tmp_gen_diss_tests import CHANNELS, DIRECT_TEMPLATE, REPLAY_TEMPLATE, sha256_of, anchor_of  # noqa: E402

TESTS = ROOT / "tests" / "operator_contracts"
for zh_dir, module, callable_name, asset_id, en_channel in CHANNELS:
    coefficients = "[\n    " + coeff_literal(zh_dir) + ",\n]"
    anchor = anchor_of(zh_dir)
    direct = DIRECT_TEMPLATE.format(
        module=module, callable=callable_name, en_channel=en_channel,
        anchor=anchor, coefficients=coefficients,
    )
    replay = REPLAY_TEMPLATE.format(
        zh_dir=zh_dir, module=module, callable=callable_name,
        sha256=sha256_of(zh_dir),
    )
    (TESTS / f"test_{module}.py").write_text(direct, encoding="utf-8", newline="\n")
    (TESTS / f"test_{module}_l1.py").write_text(replay, encoding="utf-8", newline="\n")
print("regenerated 18 test files")
