"""Generate the three JH radiation task-graph exact documents (r59 batch).

Writes scirel.asset-document.v1 documents with the same serializer the r57
documents use. Run once from the repository root:
    python -B scripts/tmp_gen_jh_radiation_docs.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("catalog/examples")
DEV_VERSION = "0.1.0.dev30"
SAVED_SHA = "253cda226c553cd5cd560914a6474b4b3572262b63aad61c76f91df8bafb6344"

R_DEP = "scirel.collisions.hydrogen-jh-r-coefficient"
S_DEP = "scirel.collisions.hydrogen-jh-s-coefficient"
A_DEP = "scirel.collisions.hydrogen-jh-alpha-coefficient"
SAHA_DEP = "scirel.kinetic.hydrogen-saha-equilibrium-population"

COMPOSED_DOMAIN = (
    "**The composed domain is the intersection of the bound assets' contracts, and it is "
    "narrower than the saved composition.** The saved radiation callable admits any positive "
    "finite electron density and temperature; the bound r56 Saha asset enforces its documented "
    "< 1e32 scientific-domain limit, so this graph declares density and temperature in "
    "(0, 1e32). The neutral density n0 is bounded < 1e32 by the saved contract itself. On the "
    "shared domain the outputs are bit-identical to the saved composition (environment-gated "
    "replay); above 1e32 this graph fails closed where the saved composition would return a "
    "value. This declared narrowing is the r57 open expert question about the saved package's "
    "internal Saha copy (positive finite only) versus the integrated r56 Saha asset (positive "
    "finite below 1e32)."
)

PRODUCER_DEFERRAL = (
    "The packaged payload producer (source anchor create_jh_bscoef.py:11-248) is deferred: it "
    "materializes coefficient data, and admitting that data as a SciRel artifact is the "
    "still-open r57 expert decision. The jh_payload therefore stays caller-supplied here, "
    "exactly like the r57 coefficient assets, and no table physics is claimed."
)

EVIDENCE_CEILING = (
    "The maintained tests establish the composition against independent recomputation from the "
    "bound SciRel assets and an independent FITPACK re-evaluation of the r spline, the frozen "
    "constants and operation order, and the full composed-domain input and failure contracts. "
    "The environment-gated replay establishes exact bit-level agreement with the saved KN1DPy "
    "composition on the packaged coefficient payload and the compared rejections only. No test "
    "establishes the coefficient table or the Einstein coefficients against an external "
    "atomic-physics reference: the saved package records that residual as validation_oracle_gap. "
    "KN1DPy's strict D1 qualification is withdrawn; the saved bundle supports bounded historical "
    "development comparison only. Expert recognition, version-level trust and distribution "
    "licensing remain pending."
)

LINEAGE = (
    "Development integration composed from already-integrated SciRel assets: the r57 "
    "Johnson-Hinnov coefficient assets and the r56 Saha population asset. The relation itself "
    "is recovered from the saved KN1DPy {package} package, source anchor {anchor}, as recorded "
    "by the saved bundle's own extraction report (the raw source tree was not re-read; the "
    "anchor is the saved candidate's). Saved implementation file SHA-256 {sha}. The saved "
    "composition's frozen constants and operation order are preserved bit for bit; no repair is "
    "claimed. The packaged payload producer is deferred because admitting the coefficient data "
    "as a SciRel artifact is an open expert decision. KN1DPy's strict D1 qualification has been "
    "withdrawn and the bundle sits in the re-review archive, so all of this is bounded "
    "historical development comparison, not qualified-L1 provenance and not expert approval."
)

PROVENANCE_BASE = {
    "source_kinds": [
        "saved L1 operator document and implementation",
        "composition of already-integrated SciRel assets",
        "independent FITPACK reevaluation of the same spline",
        "environment-gated historical replay test",
        "scientific regression tests",
    ],
    "public_references": [],
    "license_status": "pending-human-decision",
}

COMMON_KNOWN_LIMITATIONS = [
    "The output gate is finiteness-only, exactly as saved: a caller-supplied Einstein coefficient of zero "
    "returns zero photon rate and emissivity (no emission) and a negative one returns negative values; "
    "sign and scale of the line are the caller's data responsibility.",
    "The composed domain narrows the saved composition: density and temperature must stay below "
    "1e32 because the bound r56 Saha asset enforces its documented limit, while the saved "
    "radiation callable admits any positive finite values (only n0 is bounded on the saved "
    "arm). The narrowing is declared and witnessed by the replay tests.",
    "The asset evaluates caller-supplied coefficient and Einstein tables; it does not certify "
    "any table's physics (validation_oracle_gap).",
    "The saved bundle sits in the re-review archive and KN1DPy's strict D1 qualification is "
    "withdrawn; the historical replay evidence cannot be upgraded to qualified-L1 provenance "
    "without a new strict freeze and independent review of the source project.",
    "Public distribution licensing remains pending a human decision.",
]

PROFILE_VALIDATION_NODE = {
    "id": "profile_validation",
    "kind": "controlled_glue",
    "description": "Validate the composed-domain profile contract and expose the paired arrays and branch selector.",
    "inputs": ["density_m3", "temperature_ev", "n0_m3", "no_null"],
    "outputs": ["density", "temperature", "n0", "no_null"],
}

def _payload_extraction_node(extra):
    return {
        "id": "payload_field_extraction",
        "kind": "controlled_glue",
        "description": "Extract the read-only payload fields consumed by the bound assets.",
        "inputs": ["jh_payload"],
        "outputs": ["density_knots", "temperature_knots", "spline_order", "log_r_bscoef", extra],
    }

def _level_selection_node(line_level):
    return {
        "id": "channel_level_selection",
        "kind": "controlled_glue",
        "description": "Fix the saved ion-channel and principal-level selectors of the composition.",
        "inputs": [],
        "outputs": ["ion_channel_0", "ion_channel_1", "principal_level_1", f"principal_level_{line_level}"],
    }

def _r_node(node_id, channel, level):
    return {
        "id": node_id,
        "kind": "operator",
        "asset_id": R_DEP,
        "description": f"Evaluate the r coefficient for ion channel {channel}, principal level {level}.",
        "inputs": [
            "density", "temperature", f"ion_channel_{channel}", f"principal_level_{level}",
            "density_knots", "temperature_knots", "spline_order", "log_r_bscoef", "no_null",
        ],
        "outputs": [f"r{channel}{level}"],
    }

def _saha_node(level):
    return {
        "id": f"saha_level_{level}",
        "kind": "operator",
        "asset_id": SAHA_DEP,
        "description": f"Evaluate the Saha equilibrium population of principal level {level}.",
        "inputs": ["density", "temperature", f"principal_level_{level}"],
        "outputs": [f"saha{level}"],
    }

def _input_port(name, description, units, shape, dtype, constraints, required=True, default=None):
    port = {
        "name": name,
        "description": description,
        "units": units,
        "shape": shape,
        "dtype": dtype,
        "required": required,
        "constraints": constraints,
    }
    if not required:
        port["default"] = default
    return port

PROFILE_PORTS = [
    _input_port(
        "density_m3",
        "Electron densities; consumed by the Saha populations and validated by the bound r asset.",
        "m^-3", "[n]", "real array-like",
        "A non-empty one-dimensional array, finite and strictly positive and below 1e32 (the bound Saha asset's domain limit), paired with the temperatures.",
    ),
    _input_port(
        "temperature_ev",
        "Electron temperatures; clipped to the temperature-knot range by the bound assets.",
        "eV", "[n]", "real array-like",
        "A one-dimensional array of the same shape, finite and strictly positive and below 1e32.",
    ),
    _input_port(
        "n0_m3",
        "Ground-state neutral densities entering the excited-population correction term.",
        "m^-3", "[n]", "real array-like",
        "A one-dimensional array of the same shape, finite and strictly positive and below the 1e32 source null sentinel.",
    ),
    _input_port(
        "jh_payload",
        "The read-only Johnson-Hinnov coefficient payload mapping with the exact fields DKnot, TKnot, order, LogR_BSCoef, LogS_BSCoef, LogAlpha_BSCoef, A_Lyman, A_Balmer.",
        "mixed (knots, coefficient tensors, Einstein coefficients)", "mapping",
        "mapping of arrays and an integer",
        "Validated by this graph against the saved exact eight-field contract (the complete field set including fields the branch does not numerically consume, one-dimensional non-decreasing finite knots, order field 4 consumed by FITPACK as the spline degree describing exactly 77 coefficients, every field finite) before any evaluation; never mutated.",
    ),
    _input_port(
        "no_null",
        "The source branch selector passed through to the bound assets.",
        "dimensionless", "scalar", "integer scalar",
        "Only the source-complete no_null=1 branch is admitted; any other value fails closed.",
        required=False, default=1,
    ),
]

def _edge(src_node, src_port, dst_node, dst_port, description, condition, transform, required=True):
    return {
        "from": {"node": src_node, "port": src_port},
        "to": {"node": dst_node, "port": dst_port},
        "description": description,
        "condition": condition,
        "transform": transform,
        "kind": "data",
        "required": required,
    }

def _emission_edges(level2):
    edges = [
        _edge("$input", "density_m3", "profile_validation", "density_m3", "Caller electron-density profile.", "Always.", "Identity after finiteness, positivity and the 1e32 composed-domain check."),
        _edge("$input", "temperature_ev", "profile_validation", "temperature_ev", "Caller electron-temperature profile.", "Always.", "Identity after the same profile validation."),
        _edge("$input", "n0_m3", "profile_validation", "n0_m3", "Caller ground-state neutral-density profile.", "Always.", "Identity after the saved n0 contract check (finite, positive, below 1e32)."),
        _edge("$input", "no_null", "profile_validation", "no_null", "Caller branch selector.", "Always; the port defaults to 1 when omitted.", "Fail closed unless the value is 1."),
        _edge("$input", "jh_payload", "payload_field_extraction", "jh_payload", "Caller coefficient payload.", "Always.", "Read-only field extraction; the payload itself is validated by the bound assets."),
        _edge("profile_validation", "density", "r02_evaluation", "density", "Paired profile for the bound r asset.", "After profile validation.", "Identity; the bound asset applies its own saved sentinel overwrite."),
        _edge("profile_validation", "temperature", "r02_evaluation", "temperature", "Paired profile for the bound r asset.", "After profile validation.", "Identity."),
        _edge("channel_level_selection", "ion_channel_0", "r02_evaluation", "ion_channel_0", "The saved ion channel 0.", "Always.", "Constant selector."),
        _edge("channel_level_selection", f"principal_level_{level2}", "r02_evaluation", f"principal_level_{level2}", f"The level-{level2} r channel.", "Always.", "Constant selector."),
        _edge("payload_field_extraction", "density_knots", "r02_evaluation", "density_knots", "Density knots for the r spline.", "After payload field extraction.", "Identity."),
        _edge("payload_field_extraction", "temperature_knots", "r02_evaluation", "temperature_knots", "Temperature knots for the r spline.", "After payload field extraction.", "Identity."),
        _edge("payload_field_extraction", "spline_order", "r02_evaluation", "spline_order", "The payload's order field (FITPACK spline degree 4).", "After payload field extraction.", "Integer conversion only."),
        _edge("payload_field_extraction", "log_r_bscoef", "r02_evaluation", "log_r_bscoef", "The (n, 2, 5) r coefficient tensor.", "After payload field extraction.", "Identity."),
        _edge("profile_validation", "no_null", "r02_evaluation", "no_null", "The admitted branch selector.", "After profile validation.", "Identity."),
        _edge("r02_evaluation", f"r0{level2}", "photon_rate_contraction", "r02", "The level-2 ion-0 r coefficient.", "After the r02 evaluation completes.", "Identity."),
    ]
    r12 = [
        _edge("profile_validation", "density", "r12_evaluation", "density", "Paired profile for the bound r asset.", "After profile validation.", "Identity."),
        _edge("profile_validation", "temperature", "r12_evaluation", "temperature", "Paired profile for the bound r asset.", "After profile validation.", "Identity."),
        _edge("channel_level_selection", "ion_channel_1", "r12_evaluation", "ion_channel_1", "The saved ion channel 1.", "Always.", "Constant selector."),
        _edge("channel_level_selection", f"principal_level_{level2}", "r12_evaluation", f"principal_level_{level2}", f"The level-{level2} r channel.", "Always.", "Constant selector."),
        _edge("payload_field_extraction", "density_knots", "r12_evaluation", "density_knots", "Density knots for the r spline.", "After payload field extraction.", "Identity."),
        _edge("payload_field_extraction", "temperature_knots", "r12_evaluation", "temperature_knots", "Temperature knots for the r spline.", "After payload field extraction.", "Identity."),
        _edge("payload_field_extraction", "spline_order", "r12_evaluation", "spline_order", "The payload's order field (FITPACK spline degree 4).", "After payload field extraction.", "Integer conversion only."),
        _edge("payload_field_extraction", "log_r_bscoef", "r12_evaluation", "log_r_bscoef", "The (n, 2, 5) r coefficient tensor.", "After payload field extraction.", "Identity."),
        _edge("profile_validation", "no_null", "r12_evaluation", "no_null", "The admitted branch selector.", "After profile validation.", "Identity."),
        _edge("r12_evaluation", f"r1{level2}", "photon_rate_contraction", "r12", "The level-2 ion-1 r coefficient.", "After the r12 evaluation completes.", "Identity."),
    ]
    saha = []
    for level in (1, level2):
        node = f"saha_level_{level}"
        saha.extend([
            _edge("profile_validation", "density", node, "density", "Paired profile for the bound Saha asset.", "After profile validation.", "Identity; the bound asset enforces its own < 1e32 domain."),
            _edge("profile_validation", "temperature", node, "temperature", "Paired profile for the bound Saha asset.", "After profile validation.", "Identity."),
            _edge("channel_level_selection", f"principal_level_{level}", node, f"principal_level_{level}", f"The principal level {level} selector.", "Always.", "Constant selector."),
            _edge(node, f"saha{level}", "photon_rate_contraction", f"saha{level}", f"The level-{level} Saha population.", "After the Saha evaluation completes.", "Identity."),
        ])
    tail = [
        _edge("profile_validation", "n0", "photon_rate_contraction", "n0", "The ground-state neutral density of the correction term.", "After profile validation.", "Identity."),
        _edge("payload_field_extraction", "a_lyman", "photon_rate_contraction", "a_lyman", "The packaged A_Lyman Einstein coefficient vector.", "After payload field extraction.", "Identity; only the first entry enters the contraction."),
        _edge("photon_rate_contraction", "photon_rate_m3_s", "$output", "photon_rate_m3_s", "The Lyman-alpha photon rate.", "On successful contraction.", "The saved operation order A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2, then the finite positive gate."),
        _edge("photon_rate_contraction", "photon_rate_m3_s", "emissivity_contraction", "photon_rate_m3_s", "The photon rate feeding the emissivity factor.", "After the photon-rate gate.", "Identity."),
        _edge("emissivity_contraction", "emissivity_w_m3", "$output", "emissivity_w_m3", "The Lyman-alpha line emissivity.", "On successful contraction.", "The saved frozen factors (13.6057 * (0.25 - 1/9)) * photon_rate * 1.602177e-19, then the finite positive gate."),
    ]
    return edges + r12 + saha + tail


def make_emission_doc(*, asset_id, line_name, line_name_zh, anchor, level, einstein_field):
    level2 = level
    doc = {
        "schema": "scirel.asset-document.v1",
        "asset_id": asset_id,
        "kind": "task_graph",
        "title": {"en": f"Atomic-hydrogen Johnson-Hinnov {line_name} line emission", "zh": line_name_zh},
        "summary": (
            f"Compose the Johnson-Hinnov hydrogen {line_name} photon rate and line emissivity of an explicit "
            "one-dimensional profile from the bound r-coefficient and Saha-population assets, with the saved "
            "composition's frozen constants and operation order preserved bit for bit."
        ),
        "taxonomy": ["diagnostics", "atomic-hydrogen", "johnson-hinnov", "line-radiation", "task-graph"],
        "aliases": [f"evaluate_{line_name.split('-')[0].lower()}_{line_name.replace('-', '_')}", f"JH {line_name} emissivity"],
        "identity": {
            "relation": (
                f"the saved {line_name} relation: photon_rate = A[0] * (r_ion0 + r_ion1 * n0 / saha1) * saha_level{level2} "
                f"and emissivity = (13.6057 * (0.25 - 1/9) eV) * photon_rate * 1.602177e-19, with the r coefficients "
                f"and Saha populations bound from the already-integrated SciRel assets"
            ),
            "direction": (
                "paired electron density and temperature, ground-state neutral density, explicit JH payload -> "
                f"{line_name} emissivity and photon rate per sample"
            ),
            "definition": (
                f"The bound r asset evaluates r02 (ion 0) and r12 (ion 1) for principal level {level2} with the saved "
                f"1e32 sentinel density overwrite; the bound Saha asset evaluates the level-1 and level-{level2} "
                f"populations from the caller's density and temperature; the contraction applies the saved Einstein "
                f"coefficient A[0] and the frozen emissivity factors in the saved operation order."
            ),
            "model": (
                "the saved formal implementation's explicit-payload radiation composition ("
                f"{anchor}), re-expressed as an ordered composition of the bound SciRel assets; no hidden state"
            ),
            "geometry": "none; a zero-dimensional profile relation",
            "coordinates": (
                "electron density in m^-3, electron temperature in eV, ground-state neutral density in m^-3; "
                "emissivity in W m^-3, photon rate in m^-3 s^-1"
            ),
            "boundary": (
                "the composed domain is the intersection of the bound assets' contracts: density and temperature in "
                "(0, 1e32), n0 in (0, 1e32), non-empty one-dimensional paired arrays; only the source-complete "
                "no_null=1 branch is admitted; outputs must be finite and strictly positive"
            ),
            "assumptions": [
                "The bound r asset's saved 1e32 sentinel density overwrite carries into the composition: the r "
                "channels do not depend on the caller's density values beyond shape and validation.",
                "The bound Saha asset enforces its documented < 1e32 domain, so the composed domain is narrower "
                "than the saved radiation callable's; on the shared domain the outputs are bit-identical.",
                "The coefficient and Einstein tables are caller-supplied data; this graph composes them, it does "
                "not certify any table.",
                "No external atomic-physics reference is bound: the saved package records that residual as "
                "validation_oracle_gap.",
            ],
        },
        "inputs": PROFILE_PORTS,
        "outputs": [
            {
                "name": "emissivity_w_m3",
                "description": f"The {line_name} line emissivity with the saved energy factor.",
                "units": "W m^-3",
                "shape": "[n]",
                "dtype": "float64",
                "required": True,
                "constraints": "Finite for every accepted input; the saved composition gates finiteness only, so a caller-supplied Einstein coefficient of zero returns zero rates (no emission) and a negative one returns negative values (source parity).",
            },
            {
                "name": "photon_rate_m3_s",
                "description": f"The {line_name} photon production rate.",
                "units": "m^-3 s^-1",
                "shape": "[n]",
                "dtype": "float64",
                "required": True,
                "constraints": "Finite for every accepted input; the saved composition gates finiteness only, so a caller-supplied Einstein coefficient of zero returns zero rates (no emission) and a negative one returns negative values (source parity).",
            },
        ],
        "applicability": {
            "preconditions": [
                "The caller supplies a complete, consistent JH payload; the graph composes it, it does not construct or certify one.",
                "The profile inputs stay inside the composed domain (all values finite, positive and below 1e32).",
            ],
            "supported": [
                f"{line_name} photon rates and emissivities for explicit hydrogen profiles on any consistent caller-supplied payload.",
                "Rejecting malformed profiles, n0 outside the saved contract, incomplete payloads and non-1 no_null before any evaluation.",
            ],
            "excluded": [
                "Emissivities whose energy factor differs from the saved frozen factor; the saved arithmetic is preserved, not repaired.",
                "Two-dimensional or spatially gridded profiles: the bound assets accept one-dimensional profiles only.",
                "Coefficient or Einstein tables validated against an external atomic-physics reference; none is bound.",
            ],
        },
        "failure_semantics": {
            "invalid_input": (
                "Raises ValueError with a message naming the condition when the profiles are not non-empty same-shaped "
                "1-D finite positive arrays, when density or temperature reach 1e32 (the composed Saha domain), when n0 "
                "is not finite, positive and below the 1e32 sentinel, when no_null is not 1, when the payload violates the saved exact eight-field "
                "contract (field set, knots, order, 77-coefficient geometry, finiteness), or when required inputs are "
                "missing; bound-asset validation failures propagate unchanged."
            ),
            "runtime_failure": (
                "Raises ValueError when the composition produces a non-finite photon rate or emissivity; per source "
                "parity the gate is finiteness-only, so a zero or negative caller-supplied Einstein coefficient "
                "returns zero or negative values rather than being rejected."
            ),
            "nonconvergence": "Not applicable; this TaskGraph is an ordered DAG with no feedback loop.",
            "partial_results": "Never returned; a rejected call produces no diagnostic.",
        },
        "provenance": {
            "lineage_summary": LINEAGE.format(
                package="原子氢JH-r系数B样条评价", anchor=anchor, sha=SAVED_SHA
            ),
            **PROVENANCE_BASE,
        },
        "public_api": {
            "python": {
                "module": f"scirel.diagnostics.{asset_id.split('.', 2)[2].replace('-', '_')}",
                "symbol": f"solve_hydrogen_jh_{line_name.split('-')[0].lower()}_{line_name.split('-')[1]}_emission",
                "signature": f"solve_hydrogen_jh_{line_name.split('-')[0].lower()}_{line_name.split('-')[1]}_emission(inputs=None, **kwargs)",
            }
        },
        "version": {
            "implementation_version": DEV_VERSION,
            "dependencies": [{"asset_id": R_DEP}, {"asset_id": SAHA_DEP}],
        },
        "example": {
            "description": (
                f"Evaluate the {line_name} emission on a synthetic validated payload and confirm the saved "
                "energy factor and the composed-domain rejections."
            ),
            "code": EXAMPLES[asset_id],
            "expected": (
                "Finite strictly positive emissivity and photon rate with the inputs' shape; the emissivity equals the "
                "saved frozen factor times the photon rate times the elementary charge; an n0 at the 1e32 sentinel and "
                "no_null=0 are rejected."
            ),
        },
        "verification": {
            "scope": [
                "That the photon rate equals an independent recomputation from the bound SciRel assets with the saved operation order, bit for bit.",
                "That the emissivity carries the saved frozen energy factor (13.6057 * (0.25 - 1/9) eV), recorded as an open expert question for the Lyman line.",
                "That the r channels reach the bound asset through the declared dependency binding (asset-loader resolution witness).",
                "That n0 enters the photon rate and the composition fails closed on the composed-domain violations.",
                "That the payload contract is enforced on the full eight-field set (a field the branch does not consume may not be dropped) and that a zero Einstein coefficient returns zero rates on both replay arms (pre-review regressions).",
                "Exact bit-level replay against the saved KN1DPy composition, pinned by SHA-256, on the packaged coefficient payload, plus the declared above-1e32 divergence and the shared rejection behavior. This replay is environment-gated and is historical development evidence, not qualified-L1 provenance.",
            ],
            "tests": TESTS[asset_id],
            "evidence_ceiling": EVIDENCE_CEILING,
            "known_limitations": COMMON_KNOWN_LIMITATIONS,
        },
        "graph": {
            "nodes": [
                PROFILE_VALIDATION_NODE,
                _payload_extraction_node("a_lyman"),
                _level_selection_node(level2),
                _r_node("r02_evaluation", 0, level2),
                _r_node("r12_evaluation", 1, level2),
                _saha_node(1),
                _saha_node(level2),
                {
                    "id": "photon_rate_contraction",
                    "kind": "controlled_glue",
                    "description": "Contract the r channels, n0, the Saha populations and the Einstein coefficient in the saved operation order, then gate the result finite and positive.",
                    "inputs": ["r02", "r12", "n0", "saha1", f"saha{level2}", "a_lyman"],
                    "outputs": ["photon_rate_m3_s"],
                },
                {
                    "id": "emissivity_contraction",
                    "kind": "controlled_glue",
                    "description": "Apply the saved frozen emissivity factors and gate the result finite and positive.",
                    "inputs": ["photon_rate_m3_s"],
                    "outputs": ["emissivity_w_m3"],
                },
            ],
            "edges": _emission_edges(level2),
            "execution": {
                "mode": "ordered_dag_composition",
                "ordering": (
                    "Validate the composed-domain profile contract, extract the payload fields, evaluate the two r "
                    "channels and the two Saha populations through the bound assets, contract the photon rate, apply "
                    "the emissivity factors, and gate both outputs finite and positive."
                ),
                "branches": [],
                "state_ownership": (
                    "Caller owns the profiles and the payload; the graph owns only local named values for the current "
                    "call and retains no mutable state."
                ),
                "failure_propagation": (
                    "Validation or bound-asset failure aborts the call immediately; no fallback, retry or partial "
                    "diagnostic is produced."
                ),
                "feedback": [],
            },
        },
    }
    return doc


LYMAN_EXAMPLE = '''import numpy as np
from scipy.interpolate import RectBivariateSpline
from scirel.diagnostics import solve_hydrogen_jh_lyman_alpha_emission

temperature_axis = np.linspace(-1.0, 1.0, 11)
density_axis = np.linspace(30.0, 32.0, 7)
spline = RectBivariateSpline(temperature_axis, density_axis, np.add.outer(temperature_axis, density_axis), kx=4, ky=4)
temperature_knots, density_knots = spline.get_knots()
coefficients = spline.get_coeffs()
payload = {
    "DKnot": density_knots,
    "TKnot": temperature_knots,
    "order": 4,
    "LogR_BSCoef": np.zeros((coefficients.size, 2, 5)),
    "LogS_BSCoef": coefficients.copy(),
    "LogAlpha_BSCoef": coefficients.copy() + 0.25,
    "A_Lyman": np.linspace(3.0e8, 1.0e5, 15),
    "A_Balmer": np.linspace(4.4e7, 2.0e4, 15),
}
density = np.array([1.0e20, 5.0e20])
temperature = np.array([5.0, 30.0])
n0 = np.array([1.0e17, 2.0e18])
result = solve_hydrogen_jh_lyman_alpha_emission(density_m3=density, temperature_ev=temperature, n0_m3=n0, jh_payload=payload)
assert result["photon_rate_m3_s"].shape == density.shape
assert np.all(np.isfinite(result["emissivity_w_m3"])) and np.all(result["emissivity_w_m3"] > 0.0)
saved_factor = 13.6057 * (0.25 - 1.0 / 9.0)
np.testing.assert_array_equal(result["emissivity_w_m3"], saved_factor * result["photon_rate_m3_s"] * 1.602177e-19)
try:
    solve_hydrogen_jh_lyman_alpha_emission(density_m3=density, temperature_ev=temperature, n0_m3=np.full(2, 1.0e32), jh_payload=payload)
except ValueError as error:
    assert "n0_m3" in str(error)
else:
    raise AssertionError("an n0 at the 1e32 sentinel must be rejected")
try:
    solve_hydrogen_jh_lyman_alpha_emission(density_m3=density, temperature_ev=temperature, n0_m3=n0, jh_payload=payload, no_null=0)
except ValueError as error:
    assert "no_null=1" in str(error)
else:
    raise AssertionError("no_null=0 must be rejected")'''

BALMER_EXAMPLE = LYMAN_EXAMPLE.replace("solve_hydrogen_jh_lyman_alpha_emission", "solve_hydrogen_jh_balmer_alpha_emission")

INVERSION_EXAMPLE = '''import numpy as np
from scipy.interpolate import RectBivariateSpline
from scirel.diagnostics import solve_hydrogen_jh_balmer_alpha_emission, solve_hydrogen_jh_balmer_alpha_ground_state_inversion

temperature_axis = np.linspace(-1.0, 1.0, 11)
density_axis = np.linspace(30.0, 32.0, 7)
spline = RectBivariateSpline(temperature_axis, density_axis, np.add.outer(temperature_axis, density_axis), kx=4, ky=4)
temperature_knots, density_knots = spline.get_knots()
coefficients = spline.get_coeffs()
payload = {
    "DKnot": density_knots,
    "TKnot": temperature_knots,
    "order": 4,
    "LogR_BSCoef": np.zeros((coefficients.size, 2, 5)),
    "LogS_BSCoef": coefficients.copy(),
    "LogAlpha_BSCoef": coefficients.copy() + 0.25,
    "A_Lyman": np.linspace(3.0e8, 1.0e5, 15),
    "A_Balmer": np.linspace(4.4e7, 2.0e4, 15),
}
density = np.array([1.0e20, 5.0e20])
temperature = np.array([5.0, 30.0])
n0 = np.array([1.0e17, 2.0e18])
forward = solve_hydrogen_jh_balmer_alpha_emission(density_m3=density, temperature_ev=temperature, n0_m3=n0, jh_payload=payload)
result = solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
    balmer_alpha_w_m3=forward["emissivity_w_m3"], density_m3=density, temperature_ev=temperature, jh_payload=payload
)
assert set(result) == {
    "ground_state_density_m3", "photon_rate_m3_s", "n3_population_m3",
    "ionization_rate_m3_s", "recombination_rate_m3_s", "net_source_m3_s",
}
np.testing.assert_allclose(result["ground_state_density_m3"], n0, rtol=1.0e-12, atol=1.0e3)
try:
    solve_hydrogen_jh_balmer_alpha_ground_state_inversion(
        balmer_alpha_w_m3=np.zeros(2), density_m3=density, temperature_ev=temperature, jh_payload=payload
    )
except ValueError as error:
    assert "balmer_alpha_w_m3" in str(error)
else:
    raise AssertionError("a nonpositive emissivity must be rejected")'''

EXAMPLES = {
    "scirel.diagnostics.hydrogen-jh-lyman-alpha-emission": LYMAN_EXAMPLE,
    "scirel.diagnostics.hydrogen-jh-balmer-alpha-emission": BALMER_EXAMPLE,
}

TESTS = {
    "scirel.diagnostics.hydrogen-jh-lyman-alpha-emission": [
        "tests/graph_contracts/hydrogen_jh_lyman_alpha_emission/test_graph_hydrogen_jh_lyman_alpha_emission.py",
        "tests/graph_contracts/hydrogen_jh_lyman_alpha_emission/test_graph_hydrogen_jh_lyman_alpha_emission_l1.py",
    ],
    "scirel.diagnostics.hydrogen-jh-balmer-alpha-emission": [
        "tests/graph_contracts/hydrogen_jh_balmer_alpha_emission/test_graph_hydrogen_jh_balmer_alpha_emission.py",
        "tests/graph_contracts/hydrogen_jh_balmer_alpha_emission/test_graph_hydrogen_jh_balmer_alpha_emission_l1.py",
    ],
    "scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion": [
        "tests/graph_contracts/hydrogen_jh_balmer_alpha_ground_state_inversion/test_graph_hydrogen_jh_balmer_alpha_ground_state_inversion.py",
        "tests/graph_contracts/hydrogen_jh_balmer_alpha_ground_state_inversion/test_graph_hydrogen_jh_balmer_alpha_ground_state_inversion_l1.py",
    ],
}

LYMAN_KNOWN = [
    "The saved implementation multiplies BOTH the Lyman-alpha and the Balmer-alpha photon rate by "
    "13.6057 * (0.25 - 1/9) eV, the n=3 -> 2 photon energy; the returned Lyman emissivity therefore "
    "carries that factor rather than the physical n=1 -> 2 energy 13.6057 * (1 - 1/4) eV. The photon "
    "rate is unaffected. Whether a successor should repair the Lyman factor is an open expert-review "
    "question; this asset preserves the executed arithmetic.",
    *COMMON_KNOWN_LIMITATIONS,
]


def _inversion_edges():
    edges = [
        _edge("$input", "density_m3", "profile_validation", "density_m3", "Caller electron-density profile.", "Always.", "Identity after finiteness, positivity and the 1e32 composed-domain check."),
        _edge("$input", "temperature_ev", "profile_validation", "temperature_ev", "Caller electron-temperature profile.", "Always.", "Identity after the same profile validation."),
        _edge("$input", "balmer_alpha_w_m3", "profile_validation", "balmer_alpha_w_m3", "Caller observed Balmer-alpha emissivity.", "Always.", "Identity after the saved finite-positive shape-compatible check."),
        _edge("$input", "no_null", "profile_validation", "no_null", "Caller branch selector.", "Always; the port defaults to 1 when omitted.", "Fail closed unless the value is 1."),
        _edge("$input", "jh_payload", "payload_field_extraction", "jh_payload", "Caller coefficient payload.", "Always.", "Read-only field extraction; the payload itself is validated by the bound assets."),
    ]
    r_edges = []
    for channel, node, out in ((0, "r03_evaluation", "r03"), (1, "r13_evaluation", "r13")):
        r_edges.extend([
            _edge("profile_validation", "density", node, "density", "Paired profile for the bound r asset.", "After profile validation.", "Identity; the bound asset applies its own saved sentinel overwrite."),
            _edge("profile_validation", "temperature", node, "temperature", "Paired profile for the bound r asset.", "After profile validation.", "Identity."),
            _edge("channel_level_selection", f"ion_channel_{channel}", node, f"ion_channel_{channel}", f"The saved ion channel {channel}.", "Always.", "Constant selector."),
            _edge("channel_level_selection", "principal_level_3", node, "principal_level_3", "The level-3 r channel.", "Always.", "Constant selector."),
            _edge("payload_field_extraction", "density_knots", node, "density_knots", "Density knots for the r spline.", "After payload field extraction.", "Identity."),
            _edge("payload_field_extraction", "temperature_knots", node, "temperature_knots", "Temperature knots for the r spline.", "After payload field extraction.", "Identity."),
            _edge("payload_field_extraction", "spline_order", node, "spline_order", "The payload's order field (FITPACK spline degree 4).", "After payload field extraction.", "Integer conversion only."),
            _edge("payload_field_extraction", "log_r_bscoef", node, "log_r_bscoef", "The (n, 2, 5) r coefficient tensor.", "After payload field extraction.", "Identity."),
            _edge("profile_validation", "no_null", node, "no_null", "The admitted branch selector.", "After profile validation.", "Identity."),
            _edge(node, out, "ground_state_inversion", out, f"The level-3 ion-{channel} r coefficient.", "After the r evaluation completes.", "Identity."),
        ])
    saha_edges = []
    for level in (1, 3):
        node = f"saha_level_{level}"
        saha_edges.extend([
            _edge("profile_validation", "density", node, "density", "Paired profile for the bound Saha asset.", "After profile validation.", "Identity; the bound asset enforces its own < 1e32 domain."),
            _edge("profile_validation", "temperature", node, "temperature", "Paired profile for the bound Saha asset.", "After profile validation.", "Identity."),
            _edge("channel_level_selection", f"principal_level_{level}", node, f"principal_level_{level}", f"The principal level {level} selector.", "Always.", "Constant selector."),
            _edge(node, f"saha{level}", "ground_state_inversion", f"saha{level}", f"The level-{level} Saha population.", "After the Saha evaluation completes.", "Identity."),
        ])
    s_alpha_edges = [
        _edge("profile_validation", "density", "s_evaluation", "density", "Paired profile for the bound s asset.", "After profile validation.", "Identity; the s branch consumes the caller density."),
        _edge("profile_validation", "temperature", "s_evaluation", "temperature", "Paired profile for the bound s asset.", "After profile validation.", "Identity."),
        _edge("$input", "jh_payload", "s_evaluation", "jh_payload", "Payload for the bound s asset.", "After payload field extraction.", "Identity."),
        _edge("profile_validation", "no_null", "s_evaluation", "no_null", "The admitted branch selector.", "After profile validation.", "Identity."),
        _edge("s_evaluation", "s_rate", "ionization_contraction", "s_rate", "The s rate coefficient.", "After the s evaluation completes.", "Identity."),
        _edge("profile_validation", "density", "alpha_evaluation", "density", "Paired profile for the bound alpha asset.", "After profile validation.", "Identity; the bound asset applies its own saved sentinel overwrite."),
        _edge("profile_validation", "temperature", "alpha_evaluation", "temperature", "Paired profile for the bound alpha asset.", "After profile validation.", "Identity."),
        _edge("$input", "jh_payload", "alpha_evaluation", "jh_payload", "Payload for the bound alpha asset.", "After payload field extraction.", "Identity."),
        _edge("profile_validation", "no_null", "alpha_evaluation", "no_null", "The admitted branch selector.", "After profile validation.", "Identity."),
        _edge("alpha_evaluation", "alpha_rate", "recombination_contraction", "alpha_rate", "The alpha rate coefficient.", "After the alpha evaluation completes.", "Identity."),
    ]
    tail = [
        _edge("profile_validation", "balmer_alpha_w_m3", "photon_rate_inversion", "balmer_alpha_w_m3", "The observed emissivity.", "After profile validation.", "Identity."),
        _edge("photon_rate_inversion", "photon_rate_m3_s", "$output", "photon_rate_m3_s", "The recovered photon rate.", "On successful inversion.", "The saved operation order balmer / ((13.6057 * (0.25 - 1/9)) * 1.602177e-19)."),
        _edge("photon_rate_inversion", "photon_rate_m3_s", "n3_contraction", "photon_rate_m3_s", "The photon rate feeding the n=3 population recovery.", "After the photon-rate inversion.", "Identity."),
        _edge("payload_field_extraction", "a_balmer", "n3_contraction", "a_balmer", "The packaged A_Balmer Einstein coefficient vector.", "After payload field extraction.", "Identity; only the first entry enters the contraction."),
        _edge("n3_contraction", "n3_population_m3", "$output", "n3_population_m3", "The recovered n=3 population.", "On successful contraction.", "The saved operation order photon_rate / A_Balmer[0]."),
        _edge("n3_contraction", "n3_population_m3", "ground_state_inversion", "n3_population_m3", "The n=3 population entering the inversion.", "After the n=3 contraction.", "Identity."),
        _edge("ground_state_inversion", "ground_state_density_m3", "$output", "ground_state_density_m3", "The recovered ground-state neutral density.", "On successful inversion.", "The saved operation order (n3 / saha3 - r03) * saha1 / r13."),
        _edge("ground_state_inversion", "ground_state_density_m3", "ionization_contraction", "n0", "The recovered neutral density entering the ionization term.", "After the ground-state inversion.", "Identity."),
        _edge("profile_validation", "density", "ionization_contraction", "density", "The caller density entering the ionization term.", "After profile validation.", "Identity."),
        _edge("ionization_contraction", "ionization_rate_m3_s", "$output", "ionization_rate_m3_s", "The ionization source term.", "On successful contraction.", "The saved operation order n0 * (density * s)."),
        _edge("profile_validation", "density", "recombination_contraction", "density", "The caller density entering the recombination term.", "After profile validation.", "Identity."),
        _edge("recombination_contraction", "recombination_rate_m3_s", "$output", "recombination_rate_m3_s", "The recombination sink term.", "On successful contraction.", "The saved operation order density * (density * alpha)."),
        _edge("ionization_contraction", "ionization_rate_m3_s", "net_source_contraction", "ionization_rate_m3_s", "The ionization term feeding the net source.", "After the ionization contraction.", "Identity."),
        _edge("recombination_contraction", "recombination_rate_m3_s", "net_source_contraction", "recombination_rate_m3_s", "The recombination term feeding the net source.", "After the recombination contraction.", "Identity."),
        _edge("net_source_contraction", "net_source_m3_s", "$output", "net_source_m3_s", "The net hydrogen source term.", "On successful contraction.", "The saved operation order ionization - recombination, then the finite gate on every returned field."),
    ]
    return edges + r_edges + saha_edges + s_alpha_edges + tail


def make_inversion_doc():
    asset_id = "scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion"
    return {
        "schema": "scirel.asset-document.v1",
        "asset_id": asset_id,
        "kind": "task_graph",
        "title": {"en": "Atomic-hydrogen Balmer-alpha ground-state inversion", "zh": "原子氢JH Balmer-alpha基态反演"},
        "summary": (
            "Invert an observed Balmer-alpha volumetric emissivity into the ground-state neutral density and the "
            "ionization, recombination and net-source terms of an explicit one-dimensional hydrogen profile, composed "
            "from the bound r, s, alpha and Saha assets with the saved composition's frozen constants and operation "
            "order preserved bit for bit."
        ),
        "taxonomy": ["diagnostics", "atomic-hydrogen", "johnson-hinnov", "line-radiation", "inversion", "task-graph"],
        "aliases": ["N0_from_balmer_alpha", "JH Balmer-alpha inversion"],
        "identity": {
            "relation": (
                "the saved inversion: photon_rate = balmer / ((13.6057 * (0.25 - 1/9) eV) * 1.602177e-19), "
                "n3 = photon_rate / A_Balmer[0], n0 = (n3 / saha3 - r03) * saha1 / r13, ionization = n0 * (density * s), "
                "recombination = density * (density * alpha), net_source = ionization - recombination"
            ),
            "direction": (
                "observed Balmer-alpha emissivity, paired electron density and temperature, explicit JH payload -> "
                "ground-state density, photon rate, n=3 population, ionization, recombination and net source per sample"
            ),
            "definition": (
                "The bound r asset evaluates r03 and r13 (principal level 3) with the saved 1e32 sentinel density "
                "overwrite; the bound s asset consumes the caller's density; the bound alpha asset overwrites it with "
                "the sentinel; the bound Saha asset evaluates the level-1 and level-3 populations; the inversion "
                "applies the saved operation order to the observed emissivity and returns the diagnostic fields."
            ),
            "model": (
                "the saved formal implementation's explicit-payload Balmer-alpha inversion "
                "(KN1DPy/jh_related/N0_from_balmer_alpha.py:12-70), re-expressed as an ordered composition of the "
                "bound SciRel assets; no hidden state"
            ),
            "geometry": "none; a zero-dimensional profile relation",
            "coordinates": (
                "electron density in m^-3, electron temperature in eV, observed emissivity in W m^-3; ground-state "
                "density and n=3 population in m^-3, photon rate in m^-3 s^-1, source terms in m^-3 s^-1"
            ),
            "boundary": (
                "the composed domain is the intersection of the bound assets' contracts: density and temperature in "
                "(0, 1e32), the observed emissivity finite and strictly positive, non-empty one-dimensional paired "
                "arrays; only the source-complete no_null=1 branch is admitted; every returned field must be finite"
            ),
            "assumptions": [
                "The bound r and alpha assets' saved 1e32 sentinel density overwrite carries into the composition; "
                "the bound s asset consumes the caller's density, so the returned ionization and recombination terms "
                "carry the saved s/alpha density-semantics split.",
                "The bound Saha asset enforces its documented < 1e32 domain, so the composed domain is narrower than "
                "the saved inversion's; on the shared domain the outputs are bit-identical.",
                "The coefficient and Einstein tables are caller-supplied data; this graph composes them, it does not "
                "certify any table.",
                "No external atomic-physics reference is bound: the saved package records that residual as "
                "validation_oracle_gap.",
            ],
        },
        "inputs": [
            _input_port(
                "balmer_alpha_w_m3",
                "The observed Balmer-alpha volumetric emissivity to invert.",
                "W m^-3", "[n]", "real array-like",
                "A one-dimensional array of the same shape as the densities, finite and strictly positive.",
            ),
            PROFILE_PORTS[0],
            PROFILE_PORTS[1],
            PROFILE_PORTS[3],
            PROFILE_PORTS[4],
        ],
        "outputs": [
            {
                "name": name,
                "description": description,
                "units": units,
                "shape": "[n]",
                "dtype": "float64",
                "required": True,
                "constraints": constraint,
            }
            for name, description, units, constraint in [
                ("ground_state_density_m3", "The ground-state neutral density recovered from the observed emissivity.", "m^-3", "Finite for every accepted input; strictly positive when the observed emissivity is consistent with the profile."),
                ("photon_rate_m3_s", "The recovered Balmer-alpha photon production rate.", "m^-3 s^-1", "Finite and strictly positive for every accepted input."),
                ("n3_population_m3", "The recovered n=3 population.", "m^-3", "Finite for every accepted input."),
                ("ionization_rate_m3_s", "The electron-impact ionization source term n0 * (density * s).", "m^-3 s^-1", "Finite for every accepted input."),
                ("recombination_rate_m3_s", "The recombination sink term density * (density * alpha).", "m^-3 s^-1", "Finite for every accepted input."),
                ("net_source_m3_s", "The net hydrogen source ionization - recombination.", "m^-3 s^-1", "Finite for every accepted input."),
            ]
        ],
        "applicability": {
            "preconditions": [
                "The caller supplies a complete, consistent JH payload; the graph composes it, it does not construct or certify one.",
                "The profile inputs stay inside the composed domain (all values finite, positive and below 1e32) and the observed emissivity is finite and strictly positive.",
            ],
            "supported": [
                "Ground-state neutral densities and source-term diagnostics inverted from Balmer-alpha emissivities on any consistent caller-supplied payload.",
                "Rejecting malformed profiles, nonpositive emissivities, incomplete payloads and non-1 no_null before any evaluation.",
            ],
            "excluded": [
                "Emissivities at or below zero: rejected by the saved contract.",
                "Two-dimensional or spatially gridded profiles: the bound assets accept one-dimensional profiles only.",
                "Coefficient or Einstein tables validated against an external atomic-physics reference; none is bound.",
            ],
        },
        "failure_semantics": {
            "invalid_input": (
                "Raises ValueError with a message naming the condition when the profiles are not non-empty same-shaped "
                "1-D finite positive arrays, when density or temperature reach 1e32 (the composed Saha domain), when the "
                "observed emissivity is not finite, strictly positive and shape-compatible, when no_null is not 1, or "
                "when required inputs are missing; bound-asset validation failures propagate unchanged."
            ),
            "runtime_failure": (
                "Raises ValueError when the inversion produces a non-finite field; on the declared domain the relation "
                "is finite by construction, so this guards the payload boundary rather than expected inputs."
            ),
            "nonconvergence": "Not applicable; this TaskGraph is an ordered DAG with no feedback loop.",
            "partial_results": "Never returned; a rejected call produces no diagnostic.",
        },
        "provenance": {
            "lineage_summary": LINEAGE.format(
                package="原子氢JH-r系数B样条评价",
                anchor="KN1DPy/jh_related/N0_from_balmer_alpha.py:12-70",
                sha=SAVED_SHA,
            ),
            **PROVENANCE_BASE,
        },
        "public_api": {
            "python": {
                "module": "scirel.diagnostics.hydrogen_jh_balmer_alpha_ground_state_inversion",
                "symbol": "solve_hydrogen_jh_balmer_alpha_ground_state_inversion",
                "signature": "solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=None, **kwargs)",
            }
        },
        "version": {
            "implementation_version": DEV_VERSION,
            "dependencies": [
                {"asset_id": R_DEP},
                {"asset_id": S_DEP},
                {"asset_id": A_DEP},
                {"asset_id": SAHA_DEP},
            ],
        },
        "example": {
            "description": (
                "Invert the forward Balmer-alpha emission of a known neutral density and confirm the round trip and "
                "the fail-closed rejections."
            ),
            "code": INVERSION_EXAMPLE,
            "expected": (
                "The six diagnostic fields with the inputs' shape; the recovered ground-state density matches the "
                "forward n0 to rounding; a nonpositive emissivity is rejected."
            ),
        },
        "verification": {
            "scope": [
                "That every returned field equals an independent recomputation from the bound SciRel assets with the saved operation order, bit for bit.",
                "That the inversion round-trips a known neutral density through the forward Balmer-alpha emission graph.",
                "That the returned source terms carry the saved s/alpha density-semantics split.",
                "That the composition fails closed on the composed-domain violations.",
                "Exact bit-level replay against the saved KN1DPy inversion, pinned by SHA-256, on the packaged coefficient payload, plus the declared above-1e32 divergence and the shared rejection behavior. This replay is environment-gated and is historical development evidence, not qualified-L1 provenance.",
            ],
            "tests": TESTS[asset_id],
            "evidence_ceiling": EVIDENCE_CEILING,
            "known_limitations": COMMON_KNOWN_LIMITATIONS,
        },
        "graph": {
            "nodes": [
                {
                    "id": "profile_validation",
                    "kind": "controlled_glue",
                    "description": "Validate the composed-domain profile contract and expose the paired arrays, observed emissivity and branch selector.",
                    "inputs": ["balmer_alpha_w_m3", "density_m3", "temperature_ev", "no_null"],
                    "outputs": ["balmer_alpha_w_m3", "density", "temperature", "no_null"],
                },
                _payload_extraction_node("a_balmer"),
                {
                    "id": "channel_level_selection",
                    "kind": "controlled_glue",
                    "description": "Fix the saved ion-channel and principal-level selectors of the composition.",
                    "inputs": [],
                    "outputs": ["ion_channel_0", "ion_channel_1", "principal_level_1", "principal_level_3"],
                },
                {"id": "r03_evaluation", "kind": "operator", "asset_id": R_DEP, "description": "Evaluate the r coefficient for ion channel 0, principal level 3.", "inputs": ["density", "temperature", "ion_channel_0", "principal_level_3", "density_knots", "temperature_knots", "spline_order", "log_r_bscoef", "no_null"], "outputs": ["r03"]},
                {"id": "r13_evaluation", "kind": "operator", "asset_id": R_DEP, "description": "Evaluate the r coefficient for ion channel 1, principal level 3.", "inputs": ["density", "temperature", "ion_channel_1", "principal_level_3", "density_knots", "temperature_knots", "spline_order", "log_r_bscoef", "no_null"], "outputs": ["r13"]},
                _saha_node(1),
                _saha_node(3),
                {"id": "s_evaluation", "kind": "operator", "asset_id": S_DEP, "description": "Evaluate the s coefficient from the caller's density.", "inputs": ["density", "temperature", "jh_payload", "no_null"], "outputs": ["s_rate"]},
                {"id": "alpha_evaluation", "kind": "operator", "asset_id": A_DEP, "description": "Evaluate the alpha coefficient under the saved sentinel overwrite.", "inputs": ["density", "temperature", "jh_payload", "no_null"], "outputs": ["alpha_rate"]},
                {"id": "photon_rate_inversion", "kind": "controlled_glue", "description": "Recover the photon rate from the observed emissivity with the saved frozen factors.", "inputs": ["balmer_alpha_w_m3"], "outputs": ["photon_rate_m3_s"]},
                {"id": "n3_contraction", "kind": "controlled_glue", "description": "Recover the n=3 population from the photon rate and the Einstein coefficient.", "inputs": ["photon_rate_m3_s", "a_balmer"], "outputs": ["n3_population_m3"]},
                {"id": "ground_state_inversion", "kind": "controlled_glue", "description": "Invert the level-3 balance into the ground-state neutral density.", "inputs": ["n3_population_m3", "saha3", "r03", "saha1", "r13"], "outputs": ["ground_state_density_m3"]},
                {"id": "ionization_contraction", "kind": "controlled_glue", "description": "Form the ionization source term with the density-consuming s branch.", "inputs": ["n0", "density", "s_rate"], "outputs": ["ionization_rate_m3_s"]},
                {"id": "recombination_contraction", "kind": "controlled_glue", "description": "Form the recombination sink term with the sentinel-overwritten alpha branch.", "inputs": ["density", "alpha_rate"], "outputs": ["recombination_rate_m3_s"]},
                {"id": "net_source_contraction", "kind": "controlled_glue", "description": "Form the net source and gate every returned field finite.", "inputs": ["ionization_rate_m3_s", "recombination_rate_m3_s"], "outputs": ["net_source_m3_s"]},
            ],
            "edges": _inversion_edges(),
            "execution": {
                "mode": "ordered_dag_composition",
                "ordering": (
                    "Validate the composed-domain profile contract, extract the payload fields, evaluate the two r "
                    "channels, the two Saha populations, the s and the alpha coefficients through the bound assets, "
                    "recover the photon rate and n=3 population, invert the ground-state density, form the source "
                    "terms, and gate every returned field finite."
                ),
                "branches": [],
                "state_ownership": (
                    "Caller owns the profiles, the observed emissivity and the payload; the graph owns only local "
                    "named values for the current call and retains no mutable state."
                ),
                "failure_propagation": (
                    "Validation or bound-asset failure aborts the call immediately; no fallback, retry or partial "
                    "diagnostic is produced."
                ),
                "feedback": [],
            },
        },
    }


def main():
    lyman = make_emission_doc(
        asset_id="scirel.diagnostics.hydrogen-jh-lyman-alpha-emission",
        line_name="Lyman-alpha",
        line_name_zh="原子氢JH Lyman-alpha谱线发射",
        anchor="KN1DPy/jh_related/lyman_alpha.py:42-64",
        level=2,
        einstein_field="A_Lyman",
    )
    lyman["example"]["code"] = EXAMPLES["scirel.diagnostics.hydrogen-jh-lyman-alpha-emission"]
    lyman["verification"]["known_limitations"] = LYMAN_KNOWN
    balmer = make_emission_doc(
        asset_id="scirel.diagnostics.hydrogen-jh-balmer-alpha-emission",
        line_name="Balmer-alpha",
        line_name_zh="原子氢JH Balmer-alpha谱线发射",
        anchor="KN1DPy/jh_related/balmer_alpha.py:40-64",
        level=3,
        einstein_field="A_Balmer",
    )
    balmer["example"]["code"] = EXAMPLES["scirel.diagnostics.hydrogen-jh-balmer-alpha-emission"]
    inversion = make_inversion_doc()
    for doc in (lyman, balmer, inversion):
        target = OUT / f"{doc['asset_id']}.json"
        target.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"written {target}")


if __name__ == "__main__":
    main()
