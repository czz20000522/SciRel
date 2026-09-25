"""Generate the nine dissociation-rate exact documents."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tmp_gen_diss_tests import CHANNELS  # noqa: E402
from tmp_regen_diss_tests import sha256_of  # noqa: E402

OUT = ROOT / "catalog" / "examples"

SUMMARY = (
    "The {en} electron-impact rate coefficient in m^3/s as a temperature-only "
    "nine-coefficient logarithmic polynomial in log(T), evaluated exactly in the saved "
    "source's Horner order after clipping the temperature to [0.1, 2.01e4] eV. A "
    "nonpositive temperature is rejected, which the saved implementation did not check "
    "although its own document declared a positive temperature."
)

DOC = {
    "schema": "scirel.asset-document.v1",
    "kind": "operator",
    "taxonomy": ["collisions", "rate-coefficient", "dissociation", "hydrogen", "tabulated-fit"],
    "identity": {
        "relation": "the {en} electron-impact rate coefficient as a temperature-only logarithmic polynomial",
        "direction": "electron temperature -> rate coefficient per sample",
        "definition": "The temperature is clipped to [0.1, 2.01e4] eV. The polynomial is accumulated in the saved source's Horner order as log_rate = sum(a[i] * log(T)^i), and the result is exp(log_rate) * 1e-6 in m^3/s. The bounded fit domain keeps the exponential representable for every accepted input.",
        "model": "a nine-coefficient temperature-only logarithmic polynomial fit; not a Maxwellian integral over a cross section",
        "geometry": "none; a scalar material function of electron temperature",
        "coordinates": "electron temperature in eV; output rate coefficient in m^3/s",
        "boundary": "the temperature must be finite and strictly positive; in-domain values outside the fit range clip to [0.1, 2.01e4] eV; the output is finite and strictly positive for every accepted input",
        "assumptions": [
            "The nine-coefficient table is the saved source's frozen table and the Horner order is the saved source's, preserved so that replay is bit-exact.",
            "This is a fit evaluation, not a Maxwellian integral over a cross section; it is distinct from scirel.collisions.maxwellian-relative-speed-rate-average.",
            "No external atomic-physics reference is bound: the saved package records that residual as validation_oracle_gap."
        ]
    },
    "inputs": [
        {
            "name": "temperature_ev",
            "description": "Electron temperature of the Maxwellian electron population.",
            "units": "eV",
            "shape": "any (scalar or array)",
            "dtype": "real array-like",
            "required": True,
            "constraints": "Finite and strictly positive. In-domain values outside [0.1, 2.01e4] eV are clipped to that range."
        }
    ],
    "outputs": [
        {
            "name": "rate_m3_s",
            "description": "Electron-impact rate coefficient, one value per temperature sample.",
            "units": "m^3/s",
            "shape": "same as temperature_ev",
            "dtype": "float64 array",
            "required": True,
            "constraints": "Finite and strictly positive for every accepted input."
        }
    ],
    "applicability": {
        "preconditions": [
            "The caller accepts the saved source's clipping convention: temperatures outside [0.1, 2.01e4] eV silently return the fit evaluated at the range endpoint."
        ],
        "supported": [
            "{en} electron-impact rate coefficients on the saved fit within (or clamped to) its declared temperature range.",
            "Scalar and array evaluation of any shape, including zero-dimensional inputs.",
            "Rejecting nonpositive temperatures, which the saved implementation silently clipped into the fit domain."
        ],
        "excluded": [
            "Velocity-mesh Maxwellian averaging of a cross section: use scirel.collisions.maxwellian-relative-speed-rate-average, a different relation.",
            "Other dissociation, recombination or charge-exchange channels: separate sibling assets, not variants of this relation.",
            "Plasma state, neutral transport or source terms: caller-owned.",
            "A rate model validated against an external atomic-physics reference; none is bound."
        ]
    },
    "failure_semantics": {
        "invalid_input": "Raises ValueError with a message naming the quantity when temperature_ev contains a non-finite or nonpositive value.",
        "runtime_failure": "Not reachable on the declared domain: the clipped fit keeps the exponential representable, so the result is finite and strictly positive for every accepted input. No iteration, no state and no partial results.",
        "nonconvergence": "Not applicable; the relation has no iteration or feedback.",
        "partial_results": "Never returned; a rejected call produces no rate."
    },
    "provenance": {
        "source_kinds": [
            "saved L1 operator document and implementation",
            "independent polyval reevaluation of the saved coefficients",
            "environment-gated historical replay test",
            "scientific regression tests"
        ],
        "public_references": [],
        "license_status": "pending-human-decision"
    },
    "version": {
        "implementation_version": "0.1.0.dev27",
        "dependencies": []
    },
    "example": {
        "description": "Evaluate the fit on a temperature grid, confirm the endpoint clipping, and confirm that a nonpositive temperature is rejected.",
        "expected": "Finite strictly positive rate coefficients in m^3/s on the grid; values outside the fit range equal the endpoint-clamped values exactly; ValueError naming temperature_ev for a nonpositive temperature."
    },
    "verification": {
        "scope": [
            "That the fit equals an independent numpy.polynomial.polynomial.polyval evaluation of the same frozen coefficient table on in-domain and endpoint-clamped grids to a relative tolerance of 1e-12.",
            "The source Horner order: exact bit-level equality with the saved KN1DPy implementation, pinned by SHA-256, on one- and two-dimensional temperature grids.",
            "The input contract: finite and strictly positive temperature, with messages naming the quantity. The nonpositive-temperature rejection is a documented repair: the saved implementation silently clipped it into the fit domain although its document declared a positive temperature.",
            "Repair witness in the environment-gated replay: the saved implementation returns the endpoint-clamped value for a nonpositive temperature where this asset rejects it; ordinary in-domain values are reproduced exactly. This replay is environment-gated and is historical development evidence, not qualified-L1 provenance."
        ],
        "evidence_ceiling": "The maintained tests establish the fit against an in-file independent polyval evaluation, the source Horner order by exact equality, the clipping, and the full input and failure contracts including the documented repair. The environment-gated replay establishes exact agreement with the saved KN1DPy implementation on the compared grids only. No test establishes the fit against an external atomic-physics reference: the saved package records that residual as validation_oracle_gap. KN1DPy's strict D1 qualification is withdrawn; the saved bundle supports bounded historical development comparison only. Expert recognition, version-level trust and distribution licensing remain pending.",
        "known_limitations": [
            "The fit is not validated against an external atomic-physics reference; the saved package's own validation gap carries over unchanged.",
            "Temperatures outside [0.1, 2.01e4] eV silently return the endpoint-clamped fit; this is the saved source's declared clipping convention, not an error.",
            "This is a fit evaluation, not a Maxwellian integral; it is distinct from scirel.collisions.maxwellian-relative-speed-rate-average.",
            "The nonpositive-temperature rejection is a documented development repair, not source behavior: a caller migrating from the saved implementation sees a ValueError where it previously saw the endpoint-clamped fit.",
            "The saved bundle sits in the re-review archive and KN1DPy's strict D1 qualification is withdrawn; the historical replay evidence cannot be upgraded to qualified-L1 provenance without a new strict freeze and independent review of the source project.",
            "Public distribution licensing remains pending a human decision."
        ]
    }
}

EXAMPLE_CODE = (
    "import numpy as np\n"
    "from scirel.collisions import {callable}\n\n"
    "temperature = np.array([0.1, 1.0, 10.0, 100.0, 1.0e3, 2.01e4])\n"
    "rate = {callable}(temperature)\n"
    "assert rate.shape == temperature.shape\n"
    "assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)\n"
    "clipped = {callable}(np.array([0.01, 2.01e4, 5.0e4]))\n"
    "edge = {callable}(np.array([0.1, 2.01e4, 2.01e4]))\n"
    "assert clipped[0] == edge[0] and clipped[1] == edge[1] and clipped[2] == edge[2]\n"
    "try:\n"
    "    {callable}(np.array([1.0, -5.0]))\n"
    "except ValueError as error:\n"
    "    assert 'temperature_ev' in str(error)\n"
    "else:\n"
    "    raise AssertionError('a nonpositive temperature must be rejected')"
)


def main():
    for zh_dir, module, callable_name, asset_id, en_channel in CHANNELS:
        doc = json.loads(json.dumps(DOC))  # deep copy
        doc["asset_id"] = asset_id
        doc["title"] = {"en": en_channel + " rate coefficient", "zh": zh_dir}
        doc["summary"] = SUMMARY.format(en=en_channel)
        doc["identity"] = {k: (v.format(en=en_channel) if isinstance(v, str) else v) for k, v in doc["identity"].items()}
        doc["applicability"] = {
            "preconditions": doc["applicability"]["preconditions"],
            "supported": [s.format(en=en_channel) for s in doc["applicability"]["supported"]],
            "excluded": doc["applicability"]["excluded"],
        }
        doc["aliases"] = [module, en_channel]
        doc["provenance"] = {
            "lineage_summary": (
                "Development integration from the saved KN1DPy dissociation-rate slice, "
                f"package {zh_dir}, source anchor {anchor_of(zh_dir)} (saved implementation "
                f"file SHA-256 {sha256_of(zh_dir)}). The saved source's Horner loop, clipping "
                "domain and 1e-6 scaling are preserved bit for bit. One documented repair "
                "relative to the saved implementation, whose own document declares the "
                "contract: a nonpositive temperature is rejected instead of being silently "
                "clipped into the fit domain. KN1DPy's strict D1 qualification has been "
                "withdrawn and the bundle sits in the re-review archive, so all of this is "
                "bounded historical development comparison, not qualified-L1 provenance and "
                "not expert approval."
            ),
            **doc["provenance"],
        }
        doc["public_api"] = {
            "python": {
                "module": f"scirel.collisions.{module}",
                "symbol": callable_name,
                "signature": f"{callable_name}(temperature_ev)",
            }
        }
        doc["example"]["code"] = EXAMPLE_CODE.format(callable=callable_name)
        doc["verification"]["tests"] = [
            f"tests/operator_contracts/test_{module}.py",
            f"tests/operator_contracts/test_{module}_l1.py",
        ]
        target = OUT / f"{asset_id}.json"
        target.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"written {target.name}")


def anchor_of(zh_dir):
    saved = Path("D:/Users/26569/Desktop/归档_项目/codefusion/D1待重审历史产物/KN1DPy-631d0bf1/operators")
    md = (saved / zh_dir / "operator.md").read_text(encoding="utf-8")
    for line in md.splitlines():
        if "原始材料锚点" in line:
            return line.split("：", 1)[1].strip()
    raise AssertionError(zh_dir)


if __name__ == "__main__":
    main()
