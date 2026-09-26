"""One-off generator for the three r63 transport-step exact documents.
Run once, then delete from the tracked tree before freezing."""
import json
from pathlib import Path

OUT = Path("catalog/examples")
DEV = "0.1.0.dev36"

LINEAGE = (
    "Development integration from the saved KN1DPy {package} package, source anchor {anchor}, "
    "as recorded by the saved bundle's own provenance section. Saved implementation file "
    "SHA-256 {sha}. The saved formal implementation is ported verbatim and reproduced bit for "
    "bit on the declared legal domain; no repair is claimed. KN1DPy's strict D1 qualification "
    "has been withdrawn and the bundle sits in the re-review archive, so all of this is "
    "bounded historical development comparison, not qualified-L1 provenance and not expert "
    "approval."
)
CEILING = (
    "The maintained tests establish the relation against independent recomputation with the "
    "same frozen constants and operation order, the documented fail-closed contracts, and -- "
    "in the environment-gated replay test -- bit-identical agreement with the saved KN1DPy "
    "implementation pinned by SHA-256, including rejection-behavior agreement. That replay is "
    "historical development evidence, not qualified-L1 provenance."
)
LIMITS = [
    "The saved bundle sits in the re-review archive and KN1DPy's strict D1 qualification is "
    "withdrawn; the historical replay evidence cannot be upgraded to qualified-L1 provenance "
    "without a new strict freeze and independent review of the source project.",
    "Public distribution licensing remains pending a human decision.",
]
PROV = {
    "source_kinds": [
        "saved L1 operator document and implementation",
        "independent recomputation witness",
        "environment-gated historical replay test",
        "scientific regression tests",
    ],
    "public_references": [],
    "license_status": "pending-human-decision",
}


def _port(name, desc, units, shape, dtype, cons, req=True, default=None):
    d = {"name": name, "description": desc, "units": units, "shape": shape,
         "dtype": dtype, "required": req, "constraints": cons}
    if not req:
        d["default"] = default
    return d


DOCS = []

DOCS.append({
    "schema": "scirel.asset-document.v1",
    "asset_id": "scirel.kinetic.neutral-upwind-transport-coefficients",
    "kind": "operator",
    "title": {"en": "Neutral upwind spatial transport coefficients", "zh": "中性上风空间推进系数"},
    "summary": "Assemble the source forward/backward trapezoidal transport coefficients Ak/Bk/Fk/Ck/Dk/Gk from spatial nodes, velocity axis, collision frequency and source distribution.",
    "taxonomy": ["kinetic", "neutral-transport", "upwind-scheme", "coefficients"],
    "aliases": ["assemble_neutral_upwind_transport_coefficients"],
    "identity": {
        "relation": "source forward/backward trapezoidal transport coefficients for bidirectional neutral propagation",
        "direction": "spatial nodes, velocity axis, collision frequency, source -> Ak/Bk/Fk/Ck/Dk/Gk + branch indices",
        "definition": "Forward branch (positive vx): Ak = (2*vx - dx*alpha_k)/(2*vx + dx*alpha_{k+1}), Bk = dx/(2*vx + dx*alpha_{k+1}), Fk = dx*(source_{k+1}+source_k)/(2*vx + dx*alpha_{k+1}). Backward branch (negative vx): Ck/Dk/Gk analogous.",
        "model": "the saved formal implementation's first-order upwind trapezoidal discretization",
        "geometry": "one spatial dimension with two velocity branches (positive/negative vx)",
        "coordinates": "x in m; vx and collision frequency in the source's own discrete units; the dimensional convention is source-defined and not independently calibrated",
        "boundary": "x strictly increasing with >= 2 nodes, vx one-dimensional with no zero node, alpha/source finite 3-D aligned shapes, alpha nonnegative, vx must contain both positive and negative branches",
        "assumptions": [
            "The saved first-order upwind scheme is the published contract; no higher-order or conservative correction is applied.",
            "The vx axis must contain both positive and negative branches; a zero node is rejected.",
        ],
    },
    "inputs": [
        _port("x_m", "Spatial nodes.", "m", "[nx]", "real array-like", "Finite, strictly increasing, at least two nodes."),
        _port("vx", "Velocity axis.", "normalized speed", "[nvx]", "real array-like", "Finite one-dimensional; no zero nodes; must contain both positive and negative branches."),
        _port("collision_frequency_s_inv", "Collision frequency field.", "s^-1", "[nvr,nvx,nx]", "real array-like", "Finite and nonnegative, shape (nvr,nvx,nx)."),
        _port("source_distribution", "Source distribution field.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite, same shape as collision_frequency_s_inv."),
    ],
    "outputs": [_port("coefficients", "The transport coefficient mapping.", "mixed", "mapping", "mapping of [nvr,nvx,nx] float64 arrays and two index arrays",
        "Exactly Ak, Bk, Fk, Ck, Dk, Gk (each [nvr,nvx,nx]), positive_vx_indices, negative_vx_indices.")],
    "applicability": {
        "preconditions": ["x strictly increasing >= 2 nodes; vx no zero, both branches present; alpha/source finite aligned 3-D."],
        "supported": ["Forward/backward trapezoidal transport coefficients for H and H2 neutral generation propagation."],
        "excluded": ["Higher-order schemes; nonuniform velocity-axis weighting; conservative flux correction."],
    },
    "failure_semantics": {
        "invalid_input": "Raises ValueError when x is not strictly increasing (>= 2 nodes), vx has a zero node or lacks a branch, alpha/source are not finite aligned 3-D, or alpha has negative entries.",
        "runtime_failure": "Not applicable; coefficient assembly is a deterministic arithmetic step.",
        "nonconvergence": "Not applicable.",
        "partial_results": "Never returned; a rejected call produces no result.",
    },
    "provenance": {"lineage_summary": LINEAGE.format(
        package="中性上风空间推进系数", anchor="KN1DPy/kinetic_h.py:1170-1249",
        sha="b7b2979415f82d64fb9f963d1c6e531a9ff6353b8d93e209d3370b34db721bf2"), **PROV},
    "public_api": {"python": {
        "module": "scirel.kinetic.upwind_transport_coefficients",
        "symbol": "assemble_neutral_upwind_transport_coefficients",
        "signature": "assemble_neutral_upwind_transport_coefficients(x_m, vx, collision_frequency_s_inv, source_distribution)",
    }},
    "version": {"implementation_version": DEV, "dependencies": []},
    "example": {
        "description": "Assemble coefficients on a small mesh and confirm branch separation.",
        "code": "import numpy as np\nfrom scirel.kinetic import assemble_neutral_upwind_transport_coefficients\nx = np.linspace(0, 1, 3)\nvx = np.array([-1.0, 1.0])\nalpha = np.ones((2, 2, 3))\nsource = np.ones((2, 2, 3))\nr = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)\nassert r['Ak'].shape == (2, 2, 3)\nassert np.all(r['Ak'][:, 0, :] == 0.0)  # vx[0]=-1 is negative\nassert np.all(r['Ck'][:, 1, :] == 0.0)  # vx[1]=+1 is positive",
        "expected": "Coefficient mapping with correct branch separation.",
    },
    "verification": {
        "scope": [
            "Forward-step consistency: Ak matches the closed-form (2*vx - dx*alpha_k)/(2*vx + dx*alpha_{k+1}) on the positive branch.",
            "Branch separation: Ak/Bk/Fk are zero on the negative branch; Ck/Dk/Gk zero on the positive branch.",
            "Input and failure contracts.",
            "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256.",
        ],
        "tests": ["tests/operator_contracts/test_transport_step.py", "tests/operator_contracts/test_transport_step_l1.py"],
        "evidence_ceiling": CEILING,
        "known_limitations": LIMITS,
    },
})

DOCS.append({
    "schema": "scirel.asset-document.v1",
    "asset_id": "scirel.kinetic.neutral-generation-propagation",
    "kind": "operator",
    "title": {"en": "Neutral generation propagation", "zh": "中性代际空间传播"},
    "summary": "Propagate one neutral generation (first-flight or scattered) bidirectionally through the spatial grid using the saved upwind transport coefficients.",
    "taxonomy": ["kinetic", "neutral-transport", "propagation", "generation"],
    "aliases": ["propagate_neutral_generation"],
    "identity": {
        "relation": "bidirectional spatial propagation of one neutral generation using saved transport coefficients",
        "direction": "vx, Ak/Bk/Fk/Ck/Dk/Gk, generation_kind, incoming_boundary or scattered_source -> generation distribution",
        "definition": "first_flight: forward from boundary on positive vx, backward on negative vx, no source terms. scattered: forward/backward with source terms Bk/Fk (positive) and Dk/Gk (negative).",
        "model": "the saved formal implementation's bidirectional first-order upwind propagation",
        "geometry": "one spatial dimension, two velocity branches",
        "coordinates": "vx and generation in the source's own discrete units; the dimensional convention is source-defined",
        "boundary": "vx one-dimensional with both positive and negative branches; six coefficient fields finite aligned 3-D; generation_kind in {first_flight, scattered}; first_flight requires incoming_boundary; scattered requires scattered_source_distribution",
        "assumptions": [
            "The saved first-order upwind propagation is the published contract.",
            "The two generation kinds are mutually exclusive: first_flight uses incoming_boundary, scattered uses scattered_source_distribution.",
        ],
    },
    "inputs": [
        _port("vx", "Velocity axis.", "normalized speed", "[nvx]", "real array-like", "Finite one-dimensional with both positive and negative branches."),
        _port("Ak", "Forward diagonal coefficient.", "dimensionless", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("Bk", "Forward source coefficient (first-flight).", "dimensionless", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("Fk", "Forward source term.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("Ck", "Backward diagonal coefficient.", "dimensionless", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("Dk", "Backward source coefficient (scattered).", "dimensionless", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("Gk", "Backward source term.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("generation_kind", "The generation branch selector.", "dimensionless", "scalar", "string scalar", "Exactly 'first_flight' or 'scattered'."),
        _port("incoming_boundary", "The incoming boundary distribution (first_flight only).", "source-discrete", "[nvr,nvx]", "real array-like", "Required for first_flight; must be finite and aligned; must be None for scattered.", req=False, default=None),
        _port("scattered_source_distribution", "The scattered source distribution (scattered only).", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Required for scattered; must be finite and aligned; must be None for first_flight.", req=False, default=None),
    ],
    "outputs": [_port("generation", "The propagated generation distribution.", "source-discrete", "[nvr,nvx,nx]", "float64 array", "Finite.")],
    "applicability": {
        "preconditions": ["Six finite aligned coefficient fields; vx with both branches; exactly one of incoming_boundary (first_flight) or scattered_source_distribution (scattered)."],
        "supported": ["First-flight and scattered neutral generation propagation for H and H2 transport."],
        "excluded": ["Higher-order propagation schemes; multi-species coupling."],
    },
    "failure_semantics": {
        "invalid_input": "Raises ValueError when vx lacks branches, coefficient fields are not finite aligned 3-D, generation_kind is invalid, or the wrong source/boundary is supplied.",
        "runtime_failure": "Not applicable; propagation is a deterministic recurrence.",
        "nonconvergence": "Not applicable.",
        "partial_results": "Never returned; a rejected call produces no result.",
    },
    "provenance": {"lineage_summary": LINEAGE.format(
        package="中性代际空间传播", anchor="KN1DPy/kinetic_h.py:1260-1275; kinetic_h2.py:1385-1415",
        sha="9d24a06959b37deaa142857bf75bb545c1bedcdbd9ec54f721c62387698c1a13"), **PROV},
    "public_api": {"python": {
        "module": "scirel.kinetic.neutral_generation_propagation",
        "symbol": "propagate_neutral_generation",
        "signature": "propagate_neutral_generation(vx, Ak, Bk, Fk, Ck, Dk, Gk, generation_kind, incoming_boundary=None, scattered_source_distribution=None)",
    }},
    "version": {"implementation_version": DEV, "dependencies": []},
    "example": {
        "description": "Propagate a first-flight generation from a uniform boundary.",
        "code": "import numpy as np\nfrom scirel.kinetic import assemble_neutral_upwind_transport_coefficients, propagate_neutral_generation\nx = np.linspace(0, 1, 3)\nvx = np.array([-1.0, 1.0])\nalpha = np.ones((2, 2, 3))\nsource = np.ones((2, 2, 3))\nr = assemble_neutral_upwind_transport_coefficients(x, vx, alpha, source)\nboundary = np.ones((2, 2))\ngen = propagate_neutral_generation(vx, r['Ak'], r['Bk'], r['Fk'], r['Ck'], r['Dk'], r['Gk'], generation_kind='first_flight', incoming_boundary=boundary)\nassert gen.shape == (2, 2, 3)\nassert np.all(np.isfinite(gen))",
        "expected": "A finite generation distribution with the expected shape.",
    },
    "verification": {
        "scope": [
            "That first_flight forward propagation matches the saved coefficient recurrence.",
            "That scattered backward propagation matches the saved coefficient recurrence.",
            "The generation_kind and source/boundary exclusivity failure contracts.",
            "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256, on both generation kinds.",
        ],
        "tests": ["tests/operator_contracts/test_transport_step.py", "tests/operator_contracts/test_transport_step_l1.py"],
        "evidence_ceiling": CEILING,
        "known_limitations": LIMITS,
    },
})

DOCS.append({
    "schema": "scirel.asset-document.v1",
    "asset_id": "scirel.kinetic.neutral-boltzmann-rhs",
    "kind": "operator",
    "title": {"en": "Neutral Boltzmann RHS assembly", "zh": "中性BoltzmannRHS组装"},
    "summary": "Assemble the explicit neutral Boltzmann RHS: Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall) from the source terms, collision frequency, and total distribution.",
    "taxonomy": ["kinetic", "neutral-transport", "boltzmann-rhs", "diagnostics"],
    "aliases": ["assemble_neutral_boltzmann_rhs"],
    "identity": {
        "relation": "Vth*(S + Beta_CX - alpha_c*f + OmegaM + Swall) on a shared 3-D mesh",
        "direction": "thermal speed plus six aligned 3-D fields -> Boltzmann RHS",
        "definition": "The saved signed sum: rhs = Vth * (coeff_source + charge_exchange_source_sum - collision_frequency * total_distribution + elastic_source_sum + wall_source_sum).",
        "model": "the saved formal implementation's explicit Boltzmann RHS assembly",
        "geometry": "two velocity dimensions over one spatial axis",
        "coordinates": "thermal speed m/s; all fields in the source's discrete units",
        "boundary": "thermal speed finite and positive; all six fields finite 3-D arrays with one common shape",
        "assumptions": [
            "The saved signed sum is the published contract; the sign convention (alpha_c*f subtracted) is preserved.",
            "The caller owns the individual source/frequency fields; this asset only assembles.",
        ],
    },
    "inputs": [
        _port("thermal_speed_m_s", "The thermal speed.", "m/s", "scalar", "real scalar", "Finite and strictly positive."),
        _port("coefficient_source_distribution", "The coefficient source term.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("charge_exchange_source_sum", "The CX source sum.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("collision_frequency_s_inv", "The collision frequency field.", "s^-1", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("total_distribution", "The total distribution.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("elastic_source_sum", "The elastic source sum.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
        _port("wall_source_sum", "The wall source sum.", "source-discrete", "[nvr,nvx,nx]", "real array-like", "Finite 3-D."),
    ],
    "outputs": [_port("rhs", "The Boltzmann RHS.", "source-discrete m/s", "[nvr,nvx,nx]", "float64 array", "Finite.")],
    "applicability": {
        "preconditions": ["Thermal speed finite positive; all six fields finite aligned 3-D."],
        "supported": ["Boltzmann RHS assembly for H and H2 neutral transport diagnostics."],
        "excluded": ["Implicit or nonlinear Boltzmann solvers; external collision models."],
    },
    "failure_semantics": {
        "invalid_input": "Raises ValueError when the thermal speed is not finite and positive, any field is non-finite, or the fields do not share one common 3-D shape.",
        "runtime_failure": "Not applicable; RHS assembly is a deterministic signed sum.",
        "nonconvergence": "Not applicable.",
        "partial_results": "Never returned; a rejected call produces no result.",
    },
    "provenance": {"lineage_summary": LINEAGE.format(
        package="中性BoltzmannRHS组装", anchor="KN1DPy/kinetic_h.py:1636-1646; kinetic_h2.py:1794-1803",
        sha="fc47ee0a4c5ad0668844cc0ca30bf6ba4b3fc3530e8ca393e60642d8cf9e95fa"), **PROV},
    "public_api": {"python": {
        "module": "scirel.kinetic.neutral_boltzmann_rhs",
        "symbol": "assemble_neutral_boltzmann_rhs",
        "signature": "assemble_neutral_boltzmann_rhs(thermal_speed_m_s, coefficient_source_distribution, charge_exchange_source_sum, collision_frequency_s_inv, total_distribution, elastic_source_sum, wall_source_sum)",
    }},
    "version": {"implementation_version": DEV, "dependencies": []},
    "example": {
        "description": "Assemble the Boltzmann RHS from uniform unit fields.",
        "code": "import numpy as np\nfrom scirel.kinetic import assemble_neutral_boltzmann_rhs\nones = np.ones((1, 1, 1))\nr = assemble_neutral_boltzmann_rhs(5000.0, ones, ones, ones, ones, ones, ones)\n# Vth * (1 + 1 - 1*1 + 1 + 1) = 5000 * 3\nassert r['rhs'][0, 0, 0] == 15000.0\ntry:\n    assemble_neutral_boltzmann_rhs(float('nan'), ones, ones, ones, ones, ones, ones)\nexcept ValueError as error:\n    assert 'positive and finite' in str(error)\nelse:\n    raise AssertionError('NaN thermal speed must be rejected')",
        "expected": "The signed sum times Vth; NaN thermal speed is rejected.",
    },
    "verification": {
        "scope": [
            "That the RHS equals an independent signed-sum recomputation times Vth, bit for bit.",
            "The thermal-speed finiteness and field shape/finiteness failure contracts.",
            "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256.",
        ],
        "tests": ["tests/operator_contracts/test_transport_step.py", "tests/operator_contracts/test_transport_step_l1.py"],
        "evidence_ceiling": CEILING,
        "known_limitations": LIMITS,
    },
})


def main():
    for doc in DOCS:
        target = OUT / f"{doc['asset_id']}.json"
        if target.exists():
            raise FileExistsError(f"refusing to overwrite: {target}")
        target.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n",
            encoding="utf-8", newline="\n",
        )
        print("written", target.name)


if __name__ == "__main__":
    main()
