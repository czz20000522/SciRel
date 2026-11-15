"""Manually reproduce independent A/B research; never imported by pytest.

Run through scripts/dev.py. This reads only sibling tracked inputs and writes
exclusively to a new directory under the current checkout's .runtime.
"""

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import mpmath as mp


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def pair(value):
    return mp.mpc(mp.mpf(value[0]), mp.mpf(value[1]))


def entries(record):
    values = {
        f"{k}[{i},{j}]": pair(record[k][i][j])
        for k in ("K", "D")
        for i in range(3)
        for j in range(3)
    }
    return values | {k: pair(record[k]) for k in ("detK", "detD")}


def text(value):
    return mp.nstr(value, 160, strip_zeros=False)


def compare(low, high):
    # At least the original 180/200 parse dps, and 320 for the successor.
    with mp.workdps(320):
        a, b = entries(low), entries(high)
        errors = {k: abs(a[k] - b[k]) / max(1, abs(b[k])) for k in a}
        return {
            "scaled_differences": {k: text(v) for k, v in errors.items()},
            "pass": max(errors.values()) <= mp.mpf("1e-70"),
        }


def normalize_A(record):
    data = record["high_precision"]
    return dict(
        id=record["case_id"],
        dps=record["dps"],
        N=record["N"],
        K=data["K"],
        D=data["D"],
        detK=data["det_K"],
        detD=data["det_D"],
    )


def normalize_B(record):
    def p(z):
        return [z["re"], z["im"]]

    return dict(
        id=record["id"],
        dps=record["computed_dps"],
        N=record["harmonic_cutoff"],
        K=[[p(v) for v in row] for row in record["K"]],
        D=[[p(v) for v in row] for row in record["D"]],
        detK=p(record["detK"]),
        detD=p(record["detD"]),
    )


def check_input_identity(inputs, model):
    def verify(value, identity):
        if isinstance(identity, dict) and "hex" in identity:
            assert float(value).hex() == identity["hex"]
            assert Fraction(float(value)) == Fraction(
                int(identity["numerator"]), int(identity["denominator"])
            )
        elif isinstance(identity, dict):
            for k, v in identity.items():
                if k != "id":
                    verify(value[k], v)
                else:
                    assert value[k] == v
        elif isinstance(identity, list):
            assert len(value) == len(identity)
            for v, i in zip(value, identity, strict=True):
                verify(v, i)

    verify(inputs, inputs["binary64_exact_identity"])
    rows = model["first4_literal_rows"]
    for row, identities in zip(rows, model["full8_binary64_identities"][:4], strict=True):
        for value, identity in zip(row, identities, strict=True):
            verify(float(value), identity)


def observe():
    reference = read("reference.json")
    a = {r["id"]: r for r in reference["A_original"]["cases"]}
    a["small-kz"] = reference["A_small_kz_successor"]["case"]
    results = {}
    with mp.workdps(320):
        for b in reference["B"]["cases"]:
            av, bv = entries(a[b["id"]]), entries(b)
            results[b["id"]] = {}
            for k in av:
                delta = bv[k] - av[k]
                results[b["id"]][k] = dict(
                    re=text(delta.real),
                    im=text(delta.imag),
                    absolute=text(abs(delta)),
                    scaled=text(abs(delta) / max(1, abs(av[k]))),
                )
    return {
        "meaning": "B-A model discrepancy; no acceptance threshold or root/damping guarantee",
        "A_selection": "original fifteen plus separately frozen small-kz successor",
        "auxiliary": "detK is diagnostic only, outside the 19-value product-B budget",
        "cases": results,
    }


def regenerate(output, inputs, model):
    # These modules contain only independently written mathematical formulas.
    import maxwellian_reference as physical
    import pole_reference as numerical

    def save(name, value):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")

    saved = read("reference.json")
    final = {name: {c["id"]: c for c in saved[name]["cases"]} for name in ("A_original", "B")}
    summary = {}
    for name in ("A_original", "B", "A_small_kz_successor"):
        precision = (200, 280) if name == "A_small_kz_successor" else (100, 160)
        cases = [
            c for c in inputs["cases"] if name != "A_small_kz_successor" or c["id"] == "small-kz"
        ]
        summary[name] = []
        for case in cases:
            cutoffs = [None] if case["kx"] == [0.0, 0.0] else [96, 128]
            variants = {}
            for dps in precision:
                with mp.workdps(dps):
                    if name == "B":
                        primary = [
                            (numerical.complex_input(r[:2]), numerical.complex_input(r[2:]))
                            for r in model["first4_literal_rows"]
                        ]
                        poles = primary + [(mp.conj(b), -mp.conj(c)) for b, c in primary]
                        states = [
                            numerical.prepare_species(case, sp, inputs["constants"], dps)
                            for sp in case["species"]
                        ]
                    for N in cutoffs:
                        if name == "B":
                            raw = numerical.evaluate_variant(
                                case, inputs["constants"], states, poles, N, dps
                            )
                            value = normalize_B(raw)
                            for species in raw["species"]:
                                for identity in species["gamma_identities"]:
                                    v, e = (
                                        numerical.parse(identity[k]) for k in ("actual", "expected")
                                    )
                                    assert abs(v - e) / max(1, abs(e)) <= mp.mpf("1e-70")
                        else:
                            raw = physical.calculate(case, inputs["constants"], dps, N)
                            value = normalize_A(raw)
                            for identity in raw["bessel_identity_checks"]:
                                assert all(
                                    mp.mpf(v) <= mp.mpf("1e-70") for v in identity["scaled_diffs"]
                                )
                        save(f"{name}-{case['id']}-{dps}-{N}.json", raw)
                        variants[dps, N] = value
            checks = [
                compare(variants[precision[0], N], variants[precision[1], N]) for N in cutoffs
            ]
            if len(cutoffs) == 2:
                checks += [compare(variants[dps, 96], variants[dps, 128]) for dps in precision]
            expected = (
                saved[name]["case"] if name == "A_small_kz_successor" else final[name][case["id"]]
            )
            stored_check = compare(variants[precision[1], cutoffs[-1]], expected)
            summary[name].append(
                dict(
                    id=case["id"],
                    comparisons=checks,
                    converged=all(c["pass"] for c in checks),
                    stored_reference_comparison=stored_check,
                )
            )
    save("convergence.json", summary)
    # Original A must still report its historical block, separately from its
    # successor and B. A future arithmetic/toolchain change requires review.
    assert sum(c["converged"] for c in summary["A_original"]) == 15
    assert not next(c for c in summary["A_original"] if c["id"] == "small-kz")["converged"]
    assert all(c["converged"] for c in summary["B"] + summary["A_small_kz_successor"])
    assert all(
        c["stored_reference_comparison"]["pass"] for group in summary.values() for c in group
    )
    print("A_original: REFERENCE_BLOCK 15/16; B: 16/16; A successor: 4 variants converged")
    return 2  # Preserve the original study's block; this is not a product failure.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--observe", action="store_true", help="only recompute saved B-A differences"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(REPO / ".runtime"):
        parser.error("output must be a NEW directory under this checkout's .runtime")
    output.mkdir(parents=True, exist_ok=False)
    freeze = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(HERE.iterdir())
        if p.is_file()
    }
    (output / "input-sha256.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    inputs, model = read("inputs.json"), read("poles.json")
    check_input_identity(inputs, model)
    if args.observe:
        (output / "B-minus-A.json").write_text(
            json.dumps(observe(), indent=2) + "\n", encoding="utf-8"
        )
        return 0
    return regenerate(output, inputs, model)


if __name__ == "__main__":
    raise SystemExit(main())
