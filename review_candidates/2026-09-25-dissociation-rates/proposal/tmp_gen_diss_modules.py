"""Generate the nine dissociation-rate successor modules.

Each module reproduces the saved implementation's arithmetic verbatim (the
``_COEFFICIENTS`` literal is spliced from the saved source text, and the
function body is the saved body with exactly one inserted check: a
nonpositive-temperature rejection that the saved document declares but its
implementation did not enforce).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "scirel" / "collisions"
SAVED = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")

CHANNELS = [
    ("分子氢电子碰撞解离H1sH1s速率", "hydrogen2_h1s_h1s_dissociation_rate",
     "evaluate_hydrogen2_h1s_h1s_dissociation_rate",
     "H2 + e -> H(1s) + H(1s) + e",
     "KN1DPy/sigma/sigmav_h1s_h1s_hh.py:5-27, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, caller KN1DPy/kinetic_h2.py:938"),
    ("分子氢电子碰撞解离H1sH2s速率", "hydrogen2_h1s_h2s_dissociation_rate",
     "evaluate_hydrogen2_h1s_h2s_dissociation_rate",
     "H2 + e -> H(1s) + H(2s) + e",
     "KN1DPy/sigma/sigmav_h1s_h2s_hh.py:5-27, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, caller KN1DPy/kinetic_h2.py:963"),
    ("分子氢电子碰撞解离H1sHn3速率", "hydrogen2_h1s_hn3_dissociation_rate",
     "evaluate_hydrogen2_h1s_hn3_dissociation_rate",
     "H2 + e -> H(1s) + H(n=3) + e",
     "KN1DPy/sigma/sigmav_h1s_hn3_hh.py:5-27, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, callers KN1DPy/kinetic_h2.py:974 and KN1DPy/kinetic_h2.py:988-993"),
    ("分子氢电子碰撞解离H2pH2s速率", "hydrogen2_h2p_h2s_dissociation_rate",
     "evaluate_hydrogen2_h2p_h2s_dissociation_rate",
     "H2 + e -> H2+ + H(2s) channel",
     "KN1DPy/sigma/sigmav_h2p_h2s_hh.py:5-35, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, caller KN1DPy/kinetic_h2.py:971"),
    ("分子氢电子碰撞解离pH1s速率", "hydrogen2_p_h1s_dissociation_rate",
     "evaluate_hydrogen2_p_h1s_dissociation_rate",
     "H2 + e -> H+ + H(1s) + 2e channel",
     "KN1DPy/sigma/sigmav_p_h1s_hh.py:5-27, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, caller KN1DPy/kinetic_h2.py:965-968"),
    ("分子氢离子双质子解离速率", "h2_plus_two_proton_dissociation_rate",
     "evaluate_h2_plus_two_proton_dissociation_rate",
     "H2+ + e -> p + p channel",
     "KN1DPy/kinetic_h2.py:977-983"),
    ("分子氢离子pH1s解离速率", "h2_plus_p_h1s_dissociation_rate",
     "evaluate_h2_plus_p_h1s_dissociation_rate",
     "H2+ + e -> H+ + H(1s) + e",
     "KN1DPy/sigma/sigmav_p_h1s_hp.py:5-35, callers KN1DPy/kinetic_h2.py:976-990, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10"),
    ("分子氢离子pHn2解离速率", "h2_plus_p_hn2_dissociation_rate",
     "evaluate_h2_plus_p_hn2_dissociation_rate",
     "H2+ + e -> H+ + H(n=2) + e",
     "KN1DPy/sigma/sigmav_p_hn2_hp.py:5-35, callers KN1DPy/kinetic_h2.py:976-990, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10"),
    ("分子氢离子H1sHn解离复合速率", "h2_plus_h1s_hn_dissociative_recombination_rate",
     "evaluate_h2_plus_h1s_hn_dissociative_recombination_rate",
     "H2+ + e -> H(1s) + H(n) dissociative recombination",
     "KN1DPy/sigma/sigmav_h1s_hn_hp.py:5-35, callers KN1DPy/kinetic_h2.py:976-986, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10"),
]

TEMPLATE = '''"""KN1DPy {en_channel} electron-impact rate coefficient.

One leaf recovered from the saved KN1DPy dissociation-rate slice (source
anchor {anchor}), integrated as
:func:`{callable}`:

the {en_channel} electron-impact rate coefficient in ``m^3/s`` as a
temperature-only nine-coefficient logarithmic polynomial -- the temperature in
eV, evaluated with the saved source's Horner loop on the clipped domain
``[0.1, 2.01e4] eV`` and scaled by ``1e-6``.

**The evaluation is the saved source's, exactly.**  The temperature is
sequentially clipped to ``[0.1, 2.01e4] eV``, the polynomial is accumulated in
the source's Horner order, and the result is ``exp(log_rate) * 1e-6``.  The
bounded fit domain keeps the exponential representable for every accepted
input.

**One repair relative to the saved implementation, documented.**  The saved
document declares a positive temperature, but its implementation silently
clipped a nonpositive temperature into the fit domain; this module rejects
it.  The rejection domain is otherwise unchanged: the same finite check the
saved implementation already performed, the same clipping of in-domain values
and the same arithmetic, bit for bit.

Evidence ceiling: this module establishes the fit against an independent
``polyval`` evaluation of the same coefficient table, the source Horner order
by exact equality, the input and failure contracts, the repair, and -- in the
environment-gated replay test -- exact agreement with the saved KN1DPy
implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external atomic-physics reference: the saved package records that residual as
``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "{callable}",
]

{coefficients}


def {callable}(temperature_ev):
    """Return the source rate coefficient in m^3/s for the {en_channel} channel.

    Parameters
    ----------
    temperature_ev
        Electron temperatures in eV, scalar or array; must be finite and
        strictly positive.  In-domain values above or below the fit range are
        clipped to ``[0.1, 2.01e4] eV``, the saved source's declared behavior.

    Returns
    -------
    numpy.ndarray
        Rate coefficients in ``m^3/s`` with the input's shape.  Finite and
        strictly positive for every accepted input.

    Raises
    ------
    ValueError
        If ``temperature_ev`` contains a non-finite or nonpositive value.
    """
    temperature = np.asarray(temperature_ev, dtype=float)
    if not np.all(np.isfinite(temperature)):
        raise ValueError("temperature_ev must be finite")
    if bool(np.any(temperature <= 0.0)):
        raise ValueError("temperature_ev must be positive")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    log_temperature = np.log(clipped)
    log_rate = np.full_like(log_temperature, _COEFFICIENTS[-1], dtype=float)
    for coefficient in _COEFFICIENTS[-2::-1]:
        log_rate = log_rate * log_temperature + coefficient
    return np.exp(log_rate) * 1.0e-6
'''


def splice_coefficients(zh_dir):
    text = (SAVED / zh_dir / "scientific_operator.py").read_text(encoding="utf-8")
    start = text.index("_COEFFICIENTS")
    end = text.index("dtype=float,\n)", start) + len("dtype=float,\n)")
    return text[start:end].rstrip()


def main():
    for zh_dir, module, callable_name, en_channel, anchor in CHANNELS:
        content = TEMPLATE.format(
            en_channel=en_channel,
            anchor=anchor,
            callable=callable_name,
            coefficients=splice_coefficients(zh_dir),
        )
        target = SRC / f"{module}.py"
        target.write_text(content, encoding="utf-8", newline="\n")
        print(f"written {target.name}")


if __name__ == "__main__":
    main()
