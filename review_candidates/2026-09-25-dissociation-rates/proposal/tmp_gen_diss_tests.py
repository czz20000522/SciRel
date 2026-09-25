"""Generate the nine dissociation-rate direct + replay test files.

Run from the repository root.  The tests are uniform because the nine saved
leaves share one relation shape: a temperature-only nine-coefficient
logarithmic polynomial (source Horner order), clipped to [0.1, 2.01e4] eV,
scaled by 1e-6 to m^3/s.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests" / "operator_contracts"

CHANNELS = [
    # (dir_name, module, callable, asset_id, en_channel)
    ("分子氢电子碰撞解离H1sH1s速率", "hydrogen2_h1s_h1s_dissociation_rate",
     "evaluate_hydrogen2_h1s_h1s_dissociation_rate",
     "scirel.collisions.h2-dissociation-h1s-h1s-rate-coefficient",
     "H2 + e -> H(1s) + H(1s) + e"),
    ("分子氢电子碰撞解离H1sH2s速率", "hydrogen2_h1s_h2s_dissociation_rate",
     "evaluate_hydrogen2_h1s_h2s_dissociation_rate",
     "scirel.collisions.h2-dissociation-h1s-h2s-rate-coefficient",
     "H2 + e -> H(1s) + H(2s) + e"),
    ("分子氢电子碰撞解离H1sHn3速率", "hydrogen2_h1s_hn3_dissociation_rate",
     "evaluate_hydrogen2_h1s_hn3_dissociation_rate",
     "scirel.collisions.h2-dissociation-h1s-hn3-rate-coefficient",
     "H2 + e -> H(1s) + H(n=3) + e"),
    ("分子氢电子碰撞解离H2pH2s速率", "hydrogen2_h2p_h2s_dissociation_rate",
     "evaluate_hydrogen2_h2p_h2s_dissociation_rate",
     "scirel.collisions.h2-dissociation-h2p-h2s-rate-coefficient",
     "H2 + e -> H2+ + H(2s) channel"),
    ("分子氢电子碰撞解离pH1s速率", "hydrogen2_p_h1s_dissociation_rate",
     "evaluate_hydrogen2_p_h1s_dissociation_rate",
     "scirel.collisions.h2-dissociation-p-h1s-rate-coefficient",
     "H2 + e -> H+ + H(1s) + 2e channel"),
    ("分子氢离子双质子解离速率", "h2_plus_two_proton_dissociation_rate",
     "evaluate_h2_plus_two_proton_dissociation_rate",
     "scirel.collisions.h2-plus-two-proton-dissociation-rate-coefficient",
     "H2+ + e -> p + p channel"),
    ("分子氢离子pH1s解离速率", "h2_plus_p_h1s_dissociation_rate",
     "evaluate_h2_plus_p_h1s_dissociation_rate",
     "scirel.collisions.h2-plus-p-h1s-dissociation-rate-coefficient",
     "H2+ + e -> H+ + H(1s) + e"),
    ("分子氢离子pHn2解离速率", "h2_plus_p_hn2_dissociation_rate",
     "evaluate_h2_plus_p_hn2_dissociation_rate",
     "scirel.collisions.h2-plus-p-hn2-dissociation-rate-coefficient",
     "H2+ + e -> H+ + H(n=2) + e"),
    ("分子氢离子H1sHn解离复合速率", "h2_plus_h1s_hn_dissociative_recombination_rate",
     "evaluate_h2_plus_h1s_hn_dissociative_recombination_rate",
     "scirel.collisions.h2-plus-h1s-hn-dissociative-recombination-rate-coefficient",
     "H2+ + e -> H(1s) + H(n) dissociative recombination"),
]

DIRECT_TEMPLATE = '''"""Direct contract tests for ``scirel.collisions.{module}``.

The saved KN1DPy leaf (source anchor ``{anchor}``) fits the {en_channel}
electron-impact rate coefficient as a temperature-only nine-coefficient
logarithmic polynomial, evaluated in the source's Horner order after clipping
the temperature to ``[0.1, 2.01e4] eV`` and scaling by ``1e-6`` to ``m^3/s``.
The tests assert the fit against an independent ``polyval`` evaluation, the
domain clipping, and the fail-closed contracts.  One documented repair
relative to the saved implementation is exercised: a nonpositive temperature
is rejected (the saved document declares a positive temperature but its
implementation silently clipped it into the fit domain).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import {callable}

COEFFICIENTS = np.array(
    {coefficients},
    dtype=float,
)


def independent_oracle(temperature):
    clipped = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    return np.exp(
        np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)
    ) * 1.0e-6


def test_fit_matches_independent_oracle():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4, 5.0])
    actual = {callable}(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-12, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_oracle():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    np.testing.assert_allclose(
        {callable}(temperature),
        independent_oracle(temperature),
        rtol=1e-12,
        atol=0.0,
    )


def test_scalar_input_returns_zero_dimensional_result():
    result = {callable}(np.asarray(12.5))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_domain_clipping_matches_the_oracle():
    temperature = np.array([0.01, 2.01e4, 5.0e4])
    actual = {callable}(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-12, atol=0.0)


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="temperature_ev"):
        {callable}(np.array([1.0, -5.0]))
    with pytest.raises(ValueError, match="temperature_ev"):
        {callable}(np.array([1.0, 0.0]))


def test_nonfinite_temperature_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        {callable}([1.0, np.nan])
'''

REPLAY_TEMPLATE = '''"""Bounded historical replay against the saved KN1DPy implementation, when present.

The saved operator bundle ``KN1DPy-631d0bf1/operators/{zh_dir}`` sits in the
re-review archive: KN1DPy's strict D1 qualification has been withdrawn, so
this replay is bounded historical development evidence about the arithmetic,
not qualified-L1 provenance and not expert approval.  The tests are skipped
unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root, and the saved
implementation file is pinned by SHA-256 so a different byte stream can never
masquerade as the compared arm.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import {callable}

SOURCE_OPERATOR_SHA256 = "{sha256}"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "{zh_dir}" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {{source}}"
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_OPERATOR_SHA256
    ), f"saved operator bytes drifted from the compared arm: {{source}}"
    spec = importlib.util.spec_from_file_location("kn1dpy_{module}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_saved_fit_is_reproduced_exactly():
    source = _source_operator()
    temperature = np.array([0.1, 0.3, 1.0, 5.0, 50.0, 500.0, 5.0e3, 2.01e4, 4.0e4])
    np.testing.assert_array_equal(
        {callable}(temperature),
        source.{callable}(temperature),
    )


def test_the_saved_two_dimensional_profile_is_reproduced_exactly():
    source = _source_operator()
    temperature = np.logspace(-1, 4, 12).reshape(4, 3)
    np.testing.assert_array_equal(
        {callable}(temperature),
        source.{callable}(temperature),
    )


def test_the_saved_implementation_accepts_a_nonpositive_temperature_this_asset_rejects():
    """The documented repair: the saved implementation clipped it into the fit."""
    source = _source_operator()
    saved = source.{callable}(np.array([-5.0]))
    np.testing.assert_allclose(
        saved,
        source.{callable}(np.array([0.1])),
        rtol=0.0,
        atol=0.0,
    )
    with pytest.raises(ValueError):
        {callable}(np.array([-5.0]))
'''


def coefficients_of(zh_dir):
    saved = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")
    text = (saved / zh_dir / "scientific_operator.py").read_text(encoding="utf-8")
    start = text.index("_COEFFICIENTS = np.array(")
    end = text.index("dtype=float,\n)", start) + len("dtype=float,\n)")
    block = text[start:end]
    inner = block[block.index("[") : block.rindex("]") + 1]
    return ",\n    ".join(line.strip() for line in inner.strip().splitlines())


def sha256_of(zh_dir):
    import hashlib

    saved = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")
    data = (saved / zh_dir / "scientific_operator.py").read_bytes()
    return hashlib.sha256(data).hexdigest()


def anchor_of(zh_dir):
    saved = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")
    md = (saved / zh_dir / "operator.md").read_text(encoding="utf-8")
    for line in md.splitlines():
        if "原始材料锚点" in line:
            return line.split("：", 1)[1].strip()
    raise AssertionError(zh_dir)


def main():
    written = 0
    for zh_dir, module, callable_name, asset_id, en_channel in CHANNELS:
        coefficients = coefficients_of(zh_dir)
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
        written += 2
    print(f"written {written} test files")


if __name__ == "__main__":
    main()
