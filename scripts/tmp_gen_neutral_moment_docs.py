"""One-off generator for the 11 r60 neutral-moment-family exact documents.

Rerun semantics: writes exactly the 11 new kinetic documents listed in DOCS,
refuses to touch anything else, and stamps only DEV_VERSION.  After the r60
freeze this script is deleted from the tracked tree (per the r59 review
convention) -- the generated and validated documents are the artifacts.
Run once from the repository root:
    python -B scripts/tmp_gen_neutral_moment_docs.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("catalog/examples")
DEV_VERSION = "0.1.0.dev32"
SAVED_BUNDLE = "D1待重审历史产物/KN1DPy-631d0bf1"

LINEAGE_TMPL = (
    "Development integration from the saved KN1DPy {package} package, source anchor {anchor}, "
    "as recorded by the saved bundle's own provenance section (the raw source tree was not "
    "re-read; the anchor is the saved candidate's). Saved implementation file SHA-256 {sha}. "
    "The saved formal implementation is reproduced bit for bit with its documented validation "
    "contract and error messages; no repair is claimed. KN1DPy's strict D1 qualification has "
    "been withdrawn and the bundle sits in the re-review archive, so all of this is bounded "
    "historical development comparison, not qualified-L1 provenance and not expert approval."
)

EVIDENCE_CEILING = (
    "The maintained tests establish the relation against independent recomputation with the "
    "same frozen constants and operation order, the documented fail-closed contracts, and -- "
    "in the environment-gated replay test -- bit-identical agreement with the saved KN1DPy "
    "implementation pinned by SHA-256, including rejection-behavior agreement. That replay is "
    "historical development evidence, not qualified-L1 provenance. KN1DPy's strict D1 "
    "qualification is withdrawn; the saved bundle supports bounded historical development "
    "comparison only. Expert recognition, version-level trust and distribution licensing "
    "remain pending."
)

COMMON_LIMITS = [
    "The saved bundle sits in the re-review archive and KN1DPy's strict D1 qualification is "
    "withdrawn; the historical replay evidence cannot be upgraded to qualified-L1 provenance "
    "without a new strict freeze and independent review of the source project.",
    "Public distribution licensing remains pending a human decision.",
]

PROVENANCE_BASE = {
    "source_kinds": [
        "saved L1 operator document and implementation",
        "independent recomputation witness",
        "environment-gated historical replay test",
        "scientific regression tests",
    ],
    "public_references": [],
    "license_status": "pending-human-decision",
}


def _port(name, description, units, shape, dtype, constraints, required=True, default=None):
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


def _doc(asset_id, spec, summary, identity, inputs, outputs, applicability, failures,
         example, scope, extra_limits=()):
    return {
        "schema": "scirel.asset-document.v1",
        "asset_id": asset_id,
        "kind": "operator",
        "title": {"en": spec["title_en"], "zh": spec["title_zh"]},
        "summary": summary,
        "taxonomy": spec["taxonomy"],
        "aliases": [spec["symbol"]],
        "identity": identity,
        "inputs": inputs,
        "outputs": outputs,
        "applicability": applicability,
        "failure_semantics": failures,
        "provenance": {
            "lineage_summary": LINEAGE_TMPL.format(
                package=spec["package"], anchor=spec["anchor"], sha=spec["sha"]
            ),
            **PROVENANCE_BASE,
        },
        "public_api": {
            "python": {
                "module": spec["module"],
                "symbol": spec["symbol"],
                "signature": spec["signature"],
            }
        },
        "version": {"implementation_version": DEV_VERSION, "dependencies": []},
        "example": example,
        "verification": {
            "scope": scope,
            "tests": spec["tests"],
            "evidence_ceiling": EVIDENCE_CEILING,
            "known_limitations": [*extra_limits, *COMMON_LIMITS],
        },
    }


def _fail(invalid, runtime="Raises ValueError when the evaluation produces a non-finite result where the contract demands finiteness; no fallback is selected."):
    return {
        "invalid_input": invalid,
        "runtime_failure": runtime,
        "nonconvergence": "Not applicable.",
        "partial_results": "Never returned; a rejected call produces no result.",
    }


def _app(pre, sup, exc):
    return {"preconditions": pre, "supported": sup, "excluded": exc}


DOCS = []

# 1 thermal-speed-scale -------------------------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.thermal-speed-scale",
    {
        "package": "热速度标度换算", "title_en": "Neutral species thermal-speed scale",
        "title_zh": "中性物种热速度标度", "module": "scirel.kinetic.thermal_speed_scale",
        "symbol": "compute_thermal_speed_m_s",
        "signature": "compute_thermal_speed_m_s(temperature_ev, mass_amu)",
        "taxonomy": ["kinetic", "neutral-transport", "thermal-speed", "scale"],
        "anchor": "KN1DPy/kinetic_h2.py:1360-1371 (the source-entry thermal-speed port)",
        "sha": "9867b3fbc30317e519d0b1ed62d885c8550d00337d889542b5653c267b82fda8",
        "tests": ["tests/operator_contracts/test_thermal_speed_and_density_reduction.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The explicit second-moment thermal speed sqrt(2 e T / m) of a neutral species from its "
    "temperature in eV and mass in amu, with the saved source's frozen constants (hydrogen mass "
    "1.6726231e-27 kg, elementary charge 1.602177e-19 J/eV).",
    {
        "relation": "the second-moment thermal speed scale v = sqrt(2 e T_ev / (m_amu m_H)) with frozen constants",
        "direction": "temperature and mass -> one thermal-speed scalar",
        "definition": "v = sqrt(2 * 1.602177e-19 * T_ev / (m_amu * 1.6726231e-27)); the same Vth normalization the saved moment-reduction and boundary-flux relations consume",
        "model": "the saved formal implementation's explicit scalar relation",
        "geometry": "none; a scalar material scale",
        "coordinates": "temperature in eV, mass in amu; speed in m/s",
        "boundary": "both scalars finite and strictly positive; the result finite and strictly positive",
        "assumptions": [
            "The frozen hydrogen mass and elementary charge are the saved source's values, not CODATA-current values.",
            "This is a normalization scale, not a measured temperature diagnostic.",
        ],
    },
    [
        _port("temperature_ev", "Temperature of the species.", "eV", "scalar", "real scalar",
              "A finite strictly positive scalar."),
        _port("mass_amu", "Particle mass in multiples of the hydrogen mass.", "amu", "scalar", "real scalar",
              "A finite strictly positive scalar."),
    ],
    [_port("result", "The thermal-speed mapping.", "m/s", "mapping", "mapping with one float64 scalar",
           "Carries exactly one field thermal_speed_m_s; finite and strictly positive.")],
    _app(
        ["Finite positive temperature and mass scalars."],
        ["Thermal-speed normalization for any neutral species declared by its amu mass."],
        ["Non-finite or nonpositive inputs; a non-finite result."],
    ),
    _fail("Raises ValueError when temperature_ev or mass_amu is non-finite or nonpositive, or the result is not finite and positive."),
    {
        "description": "Evaluate the thermal speed for one temperature/mass pair and confirm the frozen-constant relation and the rejections.",
        "code": "import math\nfrom scirel.kinetic import compute_thermal_speed_m_s\nresult = compute_thermal_speed_m_s(1.0, 2.0)\nassert result['thermal_speed_m_s'] == math.sqrt(2.0 * 1.602177e-19 / (2.0 * 1.6726231e-27))\nassert compute_thermal_speed_m_s(4.0, 1.0)['thermal_speed_m_s'] == 2.0 * result['thermal_speed_m_s']\ntry:\n    compute_thermal_speed_m_s(0.0, 1.0)\nexcept ValueError as error:\n    assert 'temperature_ev' in str(error)\nelse:\n    raise AssertionError('a nonpositive temperature must be rejected')",
        "expected": "The mapping with the frozen-constant thermal speed; doubling the temperature doubles the speed; a nonpositive temperature is rejected.",
    },
    [
        "That the speed equals the independent frozen-constant relation exactly.",
        "That the speed scales with the square root of temperature and inversely with mass.",
        "The input and failure contracts (nonpositive and non-finite scalars).",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

# 2 generation-density-reduction ----------------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.generation-density-reduction",
    {
        "package": "中性分布密度归约", "title_en": "Neutral generation-density reduction",
        "title_zh": "中性代际分布密度归约", "module": "scirel.kinetic.generation_density_reduction",
        "symbol": "reduce_generation_density",
        "signature": "reduce_generation_density(distribution, cylindrical_weight, dvx)",
        "taxonomy": ["kinetic", "neutral-transport", "density-reduction", "moment"],
        "anchor": "KN1DPy/kinetic_h.py:1410-1424; kinetic_h2.py:1548-1573",
        "sha": "d11b3ece9c168f6e19df37a14aec5e46adf279f379f6bf835b0e26271cb8776c",
        "tests": ["tests/operator_contracts/test_thermal_speed_and_density_reduction.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "Reduce a (nvr, nvx, nx) neutral generation distribution to per-spatial-cell densities by the "
    "cylindrical quadrature sum of weight * distribution * dvx over both velocity axes, with the "
    "saved one-dimensional radial-weight projection path and the saved uniform-column routing.",
    {
        "relation": "per-cell generation density: n[x] = sum over (vr, vx) of W(vr,vx) * f(vr,vx,x) * dvx[vx]",
        "direction": "one generation distribution plus cylindrical quadrature -> (nx,) densities",
        "definition": "With a full (nvr,nvx) weight the sum runs over both axes at once; with a one-dimensional radial weight the saved moveaxis projection path computes sum_r w[r] * (sum_x f[r,x,:]*dvx[x]); a full weight whose columns are all equal is routed to the radial path, as saved",
        "model": "the saved formal implementation's discrete velocity-space density integral",
        "geometry": "zero-dimensional spatial cells with a 2-D cylindrical velocity quadrature",
        "coordinates": "distribution and weight in the source's discrete units, dvx in the axial cell measure; result in the source's discrete density unit",
        "boundary": "distribution finite 3-D; weight finite nonnegative, one- or two-dimensional and aligned; dvx finite nonnegative aligned to the velocity axis",
        "assumptions": [
            "The caller owns the cylindrical quadrature and its normalization; this asset integrates, it does not construct the quadrature.",
            "The saved uniform-column routing is an exact algebraic identity of the two paths only in exact arithmetic; the float path is preserved verbatim.",
        ],
    },
    [
        _port("distribution", "One generation's velocity distribution.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional array."),
        _port("cylindrical_weight", "Cylindrical quadrature weight.", "source-discrete measure", "[nvr,nvx] or [nvr]", "real array-like",
              "Finite and nonnegative; one-dimensional radial weights align to the radial axis, two-dimensional weights to the leading distribution axes."),
        _port("dvx", "Axial cell sizes.", "source-discrete measure", "[nvx]", "real array-like",
              "Finite and nonnegative, aligned to the distribution's velocity axis."),
    ],
    [_port("density", "Per-spatial-cell generation densities.", "source-discrete density", "[nx]", "float64 array",
           "Finite; signed values are preserved (no clamp).")],
    _app(
        ["Aligned finite distribution and quadrature with nonnegative weights."],
        ["Per-generation density reduction for atomic or molecular neutral fields on a shared quadrature."],
        ["Negative weights or cell sizes; misaligned axes: rejected by the saved contract."],
    ),
    _fail("Raises ValueError when the distribution is not three-dimensional, the weight is not one- or two-dimensional and aligned, dvx is not aligned, any field is non-finite, or any weight or cell size is negative."),
    {
        "description": "Reduce one random generation distribution with both saved weight forms and confirm the routing identity.",
        "code": "import numpy as np\nfrom scirel.kinetic import reduce_generation_density\nf = np.ones((2, 2, 2))\nw2 = np.full((2, 2), 0.5)\ndx = np.array([0.5, 1.0])\nresult = reduce_generation_density(f, w2, dx)\nnp.testing.assert_allclose(result, [0.75, 0.75])\nradial = np.array([0.25, 0.75])\nuniform = np.repeat(radial[:, None], 2, axis=1)\nnp.testing.assert_array_equal(reduce_generation_density(f, uniform, dx), reduce_generation_density(f, radial, dx))\ntry:\n    reduce_generation_density(f, np.ones((2, 2)), np.array([0.5, -1.0]))\nexcept ValueError as error:\n    assert 'aligned' in str(error)\nelse:\n    raise AssertionError('a negative dvx must be rejected')",
        "expected": "Per-cell densities matching the quadrature sum; the uniform-column routing identity holds; a negative dvx is rejected.",
    },
    [
        "That the two-dimensional-weight result equals the independent per-cell quadrature sum with the saved operation order.",
        "That the one-dimensional radial weight reproduces the saved moveaxis projection path.",
        "That the saved uniform-column routing identity holds (two paths agree on column-uniform weights).",
        "The alignment and nonnegativity failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256, on both weight forms. Environment-gated; historical development evidence only.",
    ],
))

# 3 axisymmetric-neutral-moments ----------------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.axisymmetric-neutral-moments",
    {
        "package": "轴对称中性分布矩归约", "title_en": "Axisymmetric neutral velocity-space moment reduction",
        "title_zh": "轴对称中性分布矩归约", "module": "scirel.kinetic.axisymmetric_neutral_moments",
        "symbol": "reduce_axisymmetric_neutral_moments",
        "signature": "reduce_axisymmetric_neutral_moments(distribution, vx, vr, cylindrical_volume, normalization_temperature_ev, isotope_mass_amu, molecularity, axial_quadrature=None, radial_quadrature=None, empty_slice_policy='reject')",
        "taxonomy": ["kinetic", "neutral-transport", "moment-reduction", "axisymmetric", "diagnostics"],
        "anchor": "KN1DPy/kinetic_h.py:1443-1605; kinetic_h2.py:1612-1801",
        "sha": "02b58e9447e632d071877b15da871e07a5032654d6d79db8e2945dc8e3f9987e",
        "tests": ["tests/operator_contracts/test_axisymmetric_neutral_moments.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "Recover the density, axial flux and flow speed, pressure, temperature, diagonal stresses and "
    "random heat flux of an H or H2 one-dimensional-space, two-dimensional-axisymmetric velocity "
    "distribution, with the saved frozen constants and the saved sigma_zz = sigma_yy "
    "identification and empty-slice policies preserved exactly.",
    {
        "relation": "the saved cylindrical velocity-space moment integrals of one distribution with thermal-speed normalization Vth = sqrt(2 e T_norm / (m_amu m_H))",
        "direction": "distribution plus axes, volume, normalization and species scalars -> nine moment profiles",
        "definition": "density = integral of f over velocity; axial_flux = Vth * integral(vx f); flow = flux/density; pressure and stresses from the centered second moments about the flow in eV m^-3; heat flux from the centered third moment in W m^-2; sigma_zz is returned as an independent copy of sigma_yy (the saved cylindrical identification); the optional explicit quadrature pair must reconstruct cylindrical_volume exactly and switches to the saved per-slice summation order",
        "model": "the saved formal implementation's discrete cylindrical moment reduction",
        "geometry": "one-dimensional space, two-dimensional axisymmetric velocity space",
        "coordinates": "velocity axes and distributions in the source's normalized units; density m^-3, flux m^2 s^-1, flow m/s, pressure and stresses eV m^-3, temperature eV, heat flux W m^-2",
        "boundary": "finite 3-D distribution aligned to the axes; finite positive volume; positive normalization temperature and mass; molecularity in {1, 2}; empty_slice_policy in {reject, source_default}",
        "assumptions": [
            "sigma_zz = sigma_yy is the saved source's cylindrical symmetry identification, preserved verbatim; whether a successor should return an independent zz stress is an open expert question.",
            "The source_default empty-slice policy (flow 0 m/s, temperature 1 eV on zero-density slices) is the saved initial-iteration semantics, preserved for callers that need it; reject is this integration's default.",
            "The moment recovery assumes the caller's distribution is normalized as the saved source normalizes it; this asset reduces, it does not renormalize.",
        ],
    },
    [
        _port("distribution", "The velocity distribution.", "source-normalized", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional array aligned to the axes."),
        _port("vx", "The axial velocity axis.", "source-normalized", "[nvx]", "real array-like", "Finite one-dimensional."),
        _port("vr", "The radial velocity axis.", "source-normalized", "[nvr]", "real array-like", "Finite one-dimensional."),
        _port("cylindrical_volume", "The cylindrical cell-volume weights.", "source-normalized measure", "[nvr,nvx]", "real array-like",
              "Finite and strictly positive, aligned to the axes."),
        _port("normalization_temperature_ev", "The normalization temperature.", "eV", "scalar", "real scalar",
              "Finite and strictly positive."),
        _port("isotope_mass_amu", "The isotope mass.", "amu", "scalar", "real scalar", "Finite and strictly positive."),
        _port("molecularity", "The species branch: 1 for H, 2 for H2.", "dimensionless enum", "scalar", "integer scalar",
              "Exactly 1 or 2."),
        _port("axial_quadrature", "Optional explicit axial weights.", "source-normalized measure", "[nvx]", "real array-like",
              "Positive, aligned; must be provided together with radial_quadrature; together they must reconstruct cylindrical_volume exactly.",
              required=False, default=None),
        _port("radial_quadrature", "Optional explicit radial weights.", "source-normalized measure", "[nvr]", "real array-like",
              "Positive, aligned; must be provided together with axial_quadrature.",
              required=False, default=None),
        _port("empty_slice_policy", "The zero-density slice policy.", "dimensionless enum", "scalar", "string scalar",
              "Exactly 'reject' (fail closed) or 'source_default' (flow 0 m/s, temperature 1 eV).",
              required=False, default="reject"),
    ],
    [
        _port("moments", "The nine moment fields.", "mixed (see constraints)", "mapping", "mapping of [nx] float64 arrays",
              "Exactly density_m3, axial_flux_m2_s, axial_velocity_m_s, pressure_ev_m3, temperature_ev, stress_xx_ev_m3, stress_yy_ev_m3, stress_zz_ev_m3 (an independent copy of the y stress), random_heat_flux_w_m2; each finite with shape [nx]."),
    ],
    _app(
        ["Finite aligned distribution and quadrature with positive volume weights and species scalars."],
        ["Moment diagnostics for H (molecularity 1) and H2 (molecularity 2) distributions on a shared cylindrical quadrature."],
        ["Distributions on other quadrature geometries; renormalization of caller distributions; nonpositive-volume meshes."],
    ),
    _fail("Raises ValueError when the distribution/quadrature/species contract is violated, the explicit quadrature does not reconstruct cylindrical_volume, the policy enum is invalid, or (under 'reject') any spatial slice has nonpositive density."),
    {
        "description": "Reduce one random distribution, confirm the sigma_zz alias and the empty-slice divergence, and witness flow and temperature recovery on a shifted-Maxwellian-like distribution.",
        "code": "import numpy as np\nfrom scirel.kinetic import compute_thermal_speed_m_s, reduce_axisymmetric_neutral_moments\nvr = (np.arange(160) + 0.5) * (4.0 / 160)\nvx = -4.0 + (np.arange(200) + 0.5) * (10.0 / 200)\nvolume = np.outer(vr * (4.0 / 160), np.full(200, 10.0 / 200))\nvth = compute_thermal_speed_m_s(2.0, 1.0)['thermal_speed_m_s']\nvr_grid, vx_grid = np.meshgrid(vr, vx, indexing='ij')\nshift = 3.0e3 / vth\nf = np.exp(-(vr_grid[:, :, None] ** 2 + (vx_grid[:, :, None] - shift) ** 2))\nf = np.broadcast_to(f, (160, 200, 1)).copy()\nresult = reduce_axisymmetric_neutral_moments(f, vx, vr, volume, normalization_temperature_ev=2.0, isotope_mass_amu=1.0, molecularity=1)\nassert abs(result['axial_velocity_m_s'][0] - 3.0e3) < 0.02 * 3.0e3\nassert abs(result['temperature_ev'][0] - 2.0) < 0.05 * 2.0\nassert np.array_equal(result['stress_zz_ev_m3'], result['stress_yy_ev_m3'])\nzero = np.zeros_like(f)\ntry:\n    reduce_axisymmetric_neutral_moments(zero, vx, vr, volume, normalization_temperature_ev=2.0, isotope_mass_amu=1.0, molecularity=1)\nexcept ValueError as error:\n    assert 'positive density' in str(error)\nelse:\n    raise AssertionError('a zero-density slice must be rejected under the default policy')",
        "expected": "Nine finite moment profiles; the shifted-Maxwellian witness recovers flow and temperature within quadrature accuracy; sigma_zz aliases sigma_yy; a zero-density slice fails closed under the default policy.",
    },
    [
        "That the default-policy moments equal an independent per-slice recomputation with the saved operation order.",
        "That the explicit-quadrature path follows the saved per-slice summation order and fails closed on a volume mismatch.",
        "That a shifted-Maxwellian-like distribution recovers its flow speed and temperature within quadrature accuracy (independent physical witness).",
        "That sigma_zz aliases sigma_yy as an independent copy, and that the two empty-slice policies diverge exactly as saved.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256, on the default, explicit-quadrature and source_default paths. Environment-gated; historical development evidence only.",
    ],
    [
        "The sigma_zz = sigma_yy identification is the saved source's; an independent zz stress is not provided. Whether that identification is the intended published contract is carried over as an open expert question.",
        "Under 'source_default', zero-density slices report the saved neutral values (flow 0 m/s, temperature 1 eV), which are not physical measurements.",
    ],
))

# 4 elastic-frequency-channels ------------------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.elastic-frequency-channels",
    {
        "package": "弹性频率通道求和", "title_en": "Elastic collision-frequency channel sum",
        "title_zh": "弹性频率通道求和", "module": "scirel.kinetic.elastic_frequency_channels",
        "symbol": "sum_elastic_frequency_channels",
        "signature": "sum_elastic_frequency_channels(frequency_profiles)",
        "taxonomy": ["kinetic", "neutral-transport", "elastic-frequency", "reduction"],
        "anchor": "KN1DPy/kinetic_h.py:1297-1317; kinetic_h2.py:1258-1297 (the Omega-channel total)",
        "sha": "7058571007eeeb435610369b3db7ed6b7b4757ba49619cd24a605e59e1f769d8",
        "tests": ["tests/operator_contracts/test_neutral_transport_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The pointwise sum of exactly three already-normalized elastic collision-frequency channels "
    "into the transport total elastic frequency, preserving the caller's channel order.",
    {
        "relation": "Omega_total = Omega_1 + Omega_2 + Omega_3 pointwise over equal-shape channel profiles",
        "direction": "three caller-ordered channel profiles -> one total profile",
        "definition": "The three channels are added left to right in caller order (float summation order preserved); exactly three channels are admitted by the saved contract",
        "model": "the saved formal implementation's channel confluence",
        "geometry": "none; a pointwise reduction over caller-declared shapes",
        "coordinates": "frequencies in s^-1",
        "boundary": "exactly three non-empty finite equal-shape profiles",
        "assumptions": [
            "The three-channel count is the saved contract for one species family's elastic pairs; other counts are rejected.",
            "Channels are expected nonnegative by physics but only finiteness is enforced, as saved.",
        ],
    },
    [
        _port("frequency_profiles", "The elastic frequency channels.", "s^-1", "list[3] of equal-shape arrays", "sequence of real array-like",
              "Exactly three non-empty finite arrays of one common shape, in caller order."),
    ],
    [_port("total", "The summed transport frequency.", "s^-1", "common shape", "float64 array",
           "Finite; equals the pointwise sum in the saved order.")],
    _app(
        ["Three finite equal-shape caller-normalized channel profiles."],
        ["Confluence of the species-pair elastic Omega channels on one shared grid."],
        ["Fewer or more than three channels; mismatched shapes; non-finite values."],
    ),
    _fail("Raises ValueError when the channel count is not three, any channel is empty, shapes differ, or any value is non-finite."),
    {
        "description": "Sum three channels pointwise, confirm zero channels pass through, and reject contract violations.",
        "code": "import numpy as np\nfrom scirel.kinetic import sum_elastic_frequency_channels\nresult = sum_elastic_frequency_channels([np.array([1.0, 2.0]), np.array([0.5, 1.0]), np.array([0.25, 0.5])])\nnp.testing.assert_array_equal(result['elastic_frequency_s_inv'], [1.75, 3.5])\ntry:\n    sum_elastic_frequency_channels([np.ones(3), np.ones(3)])\nexcept ValueError as error:\n    assert 'exactly three' in str(error)\nelse:\n    raise AssertionError('a two-channel call must be rejected')",
        "expected": "The pointwise sum in caller order; a two-channel call is rejected.",
    },
    [
        "That the sum equals an independent pointwise addition in the saved order.",
        "The channel-count, shape, and finiteness failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

# 5 incoming-boundary-flux-normalization --------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.incoming-boundary-flux-normalization",
    {
        "package": "入射中性边界通量归一化", "title_en": "Incoming neutral boundary-flux normalization",
        "title_zh": "入射中性边界通量归一化", "module": "scirel.kinetic.incoming_boundary_flux_normalization",
        "symbol": "normalize_incoming_neutral_boundary",
        "signature": "normalize_incoming_neutral_boundary(boundary_shape, vx, cylindrical_volume, thermal_speed_m_s, target_flux_m2_s)",
        "taxonomy": ["kinetic", "neutral-transport", "boundary-condition", "normalization"],
        "anchor": "KN1DPy/kinetic_h.py:600-616; kinetic_h2.py:715-731",
        "sha": "7251bb29eca994683134966abac0a7f731baf557202db1d19fc798f70474768e",
        "tests": ["tests/operator_contracts/test_neutral_transport_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "Scale a caller-owned H or H2 boundary shape distribution on the positive axial-velocity half "
    "space to a requested incoming neutral particle flux, returning the scaled boundary "
    "distribution, the applied scale, and the pre-scale flux integral.",
    {
        "relation": "the saved positive-half flux normalization: incoming_flux = Vth * sum(volume * shape * vx) over vx > 0; scale = abs(target_flux) / incoming_flux",
        "direction": "boundary shape plus axes, volume, thermal speed and target flux -> scaled boundary, scale, incoming flux",
        "definition": "Only the positive-vx half enters the integral; the returned distribution is exactly zero on the nonpositive half; the scale is the saved abs(target)/flux form, so a negative requested flux yields the same positive scale",
        "model": "the saved formal implementation's boundary source normalization",
        "geometry": "one radial dimension times the axial velocity axis",
        "coordinates": "shape and volume in the source's normalized units, vx in normalized axial speed, thermal speed m/s, target flux m^-2 s^-1",
        "boundary": "finite nonnegative (nvr,nvx) shape with (nvr,nvx) volume, positive thermal speed, finite target flux, at least one positive vx node, strictly positive positive-half flux",
        "assumptions": [
            "The caller owns the boundary shape and the quadrature; this asset normalizes, it does not construct a distribution.",
            "The sign convention of the requested flux is the caller's (the saved scale uses abs); direction is carried by the profile, not the scale.",
        ],
    },
    [
        _port("boundary_shape", "The caller's boundary shape.", "source-normalized", "[nvr,nvx]", "real array-like",
              "Finite and nonnegative; axial velocity on the second axis."),
        _port("vx", "The axial velocity axis.", "source-normalized", "[nvx]", "real array-like",
              "Finite; must contain at least one positive node."),
        _port("cylindrical_volume", "The cylindrical quadrature weight.", "source-normalized measure", "[nvr,nvx]", "real array-like",
              "Finite, same shape as the boundary shape."),
        _port("thermal_speed_m_s", "The species thermal speed.", "m/s", "scalar", "real scalar",
              "Finite and strictly positive."),
        _port("target_flux_m2_s", "The requested incoming particle flux.", "m^-2 s^-1", "scalar", "real scalar",
              "Finite (any sign; the saved scale uses the absolute value)."),
    ],
    [
        _port("incoming_boundary", "The scaled boundary distribution.", "source-normalized", "[nvr,nvx]", "float64 array",
              "Zero on the nonpositive-vx half; the scaled shape on the positive half."),
        _port("scale", "The applied scalar scale.", "dimensionless", "scalar", "float scalar", "Finite and positive."),
        _port("incoming_flux", "The pre-scale positive-half flux integral.", "m^-2 s^-1", "scalar", "float scalar", "Finite and positive."),
    ],
    _app(
        ["Finite nonnegative shape and volume, positive thermal speed, a positive-vx half with positive flux."],
        ["Boundary sources for H and H2 inflow conditions on a shared normalized mesh."],
        ["Shapes with nonpositive flux on the positive half; meshes without a positive-vx node; non-finite scalars."],
    ),
    _fail("Raises ValueError when the shape/quadrature/scalar contract is violated, vx has no positive node, or the positive-half flux is nonpositive."),
    {
        "description": "Normalize one boundary shape to a requested flux and confirm the positive-half semantics and rejections.",
        "code": "import numpy as np\nfrom scirel.kinetic import normalize_incoming_neutral_boundary\nshape = np.ones((2, 3))\nvolume = np.ones((2, 3))\nvx = np.array([-1.0, 0.5, 1.0])\nresult, scale, initial = normalize_incoming_neutral_boundary(shape, vx, volume, 2.0, -12.0)\nassert initial == 6.0 and scale == 2.0\nassert np.all(result[:, 0] == 0.0)\ntry:\n    normalize_incoming_neutral_boundary(shape, np.array([-1.0, -0.5, 0.0]), volume, 2.0, 12.0)\nexcept ValueError as error:\n    assert 'positive incoming half' in str(error)\nelse:\n    raise AssertionError('a mesh without a positive-vx node must be rejected')",
        "expected": "The positive half scaled to the requested flux (sign-independent scale), the negative half exactly zero; a mesh without an incoming half is rejected.",
    },
    [
        "That the returned flux integral after scaling equals the requested target on the positive half.",
        "That the negative half is exactly zero and the scale matches the saved abs(target)/flux form.",
        "The fail-closed contracts (no positive half, zero flux, invalid scalars).",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

# 6 spatial-source-shape-normalization ----------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.spatial-source-shape-normalization",
    {
        "package": "空间源形状归一化", "title_en": "Spatial source-shape normalization",
        "title_zh": "空间源形状归一化", "module": "scirel.kinetic.spatial_source_shape_normalization",
        "symbol": "normalize_spatial_source_shape",
        "signature": "normalize_spatial_source_shape(source, x_m)",
        "taxonomy": ["kinetic", "neutral-transport", "source-normalization"],
        "anchor": "KN1DPy/kn1d.py:520-577 (the wall source shape port of the source-entry dual-branch graphs)",
        "sha": "83b2d7b9e860d8ee57cef6b5332b97fe31a6269a861c6e2a6df42506bfd18629",
        "tests": ["tests/operator_contracts/test_neutral_transport_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "Normalize a nonnegative one-dimensional spatial source profile to unit integral under the "
    "trapezoidal measure, returning the unit-integral shape and the original integral.",
    {
        "relation": "shape = source / integral(source, x) with the trapezoidal measure; the normalized shape re-integrates to 1 within the saved tolerance",
        "direction": "source profile plus coordinates -> unit-integral shape and original integral",
        "definition": "The saved numpy trapezoidal rule on the caller's coordinates; the saved unit-integral re-check uses rtol 1e-12, atol 1e-14; a zero profile is rejected, never silently replaced",
        "model": "the saved formal implementation's profile normalization",
        "geometry": "one-dimensional space",
        "coordinates": "coordinates in m; shape in m^-1; integral in the source's profile unit times m",
        "boundary": "aligned finite one-dimensional profile and strictly increasing coordinates with at least two nodes; nonnegative source; finite positive integral",
        "assumptions": [
            "The trapezoidal measure is the saved spatial discretization; other quadratures are excluded.",
            "The strict positivity precondition is what lets the shape rebuild a total source.",
        ],
    },
    [
        _port("source", "The source profile.", "source units", "[n]", "real array-like",
              "A finite nonnegative one-dimensional array."),
        _port("x_m", "The spatial coordinates.", "m", "[n]", "real array-like",
              "Finite, strictly increasing, at least two nodes, aligned to the source."),
    ],
    [
        _port("shape_m_inv", "The unit-integral source shape.", "m^-1", "[n]", "float64 array",
              "Finite and nonnegative; trapezoidal integral exactly re-checked to 1."),
        _port("integral_source", "The original spatial integral.", "source units times m", "scalar", "float scalar",
              "Finite and strictly positive."),
    ],
    _app(
        ["Aligned finite nonnegative profile on a strictly increasing coordinate mesh."],
        ["Wall-source and volumetric source shapes needing unit spatial integrals."],
        ["Zero or negative profiles; non-monotonic coordinates; fewer than two nodes."],
    ),
    _fail("Raises ValueError when the alignment/monotonicity/positivity contract is violated or the normalized shape fails its unit-integral re-check."),
    {
        "description": "Normalize one profile and confirm the independent trapezoidal measure and fail-closed contracts.",
        "code": "import numpy as np\nfrom scirel.kinetic import normalize_spatial_source_shape\nsource = np.array([1.0, 2.0, 1.0])\nx_m = np.array([0.0, 1.0, 2.0])\nresult = normalize_spatial_source_shape(source, x_m)\nassert result['integral_source'] == 3.0\nnp.testing.assert_array_equal(result['shape_m_inv'], source / 3.0)\nassert np.trapezoid(result['shape_m_inv'], x_m) == 1.0\ntry:\n    normalize_spatial_source_shape(np.array([0.0, 0.0]), np.array([0.0, 1.0]))\nexcept ValueError as error:\n    assert 'positive spatial integral' in str(error)\nelse:\n    raise AssertionError('a zero profile must be rejected')",
        "expected": "The unit-integral shape and original integral; a zero profile is rejected, never silently replaced.",
    },
    [
        "That the shape equals the independent trapezoidal normalization and re-integrates to exactly 1.",
        "The alignment, monotonicity, and positivity failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

# 7 neutral-total-collision-frequency -----------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.neutral-total-collision-frequency",
    {
        "package": "中性总损失碰撞频率组装", "title_en": "Neutral total-loss collision frequency assembly",
        "title_zh": "中性总损失碰撞频率组装", "module": "scirel.kinetic.neutral_total_collision_frequency",
        "symbol": "assemble_neutral_total_collision_frequency",
        "signature": "assemble_neutral_total_collision_frequency(vr, vx, base_loss_frequency_s_inv, elastic_frequency_s_inv, pipe_diameter_m, charge_exchange_frequency_s_inv=None, charge_exchange_enabled=True)",
        "taxonomy": ["kinetic", "neutral-transport", "collision-frequency", "wall-loss"],
        "anchor": "KN1DPy/kinetic_h.py:1089-1095; kinetic_h2.py:1151-1157",
        "sha": "69c25bd24033e3d7cdbaf2cdbc3becadd35e09a6149f8a1bfea4534c9e35bcbd",
        "tests": ["tests/operator_contracts/test_neutral_transport_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "Assemble the neutral total-loss frequency alpha_c = optional Alpha_CX + base loss + Omega_EL "
    "+ wall loss (2 vr / D broadcast over the grid) used by the saved source's spatial advance.",
    {
        "relation": "alpha_c[vr,vx,x] = optional CX[vr,vx,x] + base[x] + elastic[x] + wall[vr,x], with wall = 2 vr / D[x] where D[x] > 0 and zero where D[x] = 0",
        "direction": "axes, base/elastic/diameter profiles and optional CX field -> (nvr,nvx,nx) total frequency",
        "definition": "The saved assembly order (base + elastic + wall, then + CX when enabled); zero pipe diameter yields zero wall loss in those cells (the saved semantics, not an infinite-pipe limit); enabling charge exchange without a field fails closed",
        "model": "the saved formal implementation's total-loss assembly",
        "geometry": "one radial and one axial velocity dimension over one spatial axis",
        "coordinates": "frequencies in s^-1; pipe diameter in m",
        "boundary": "finite one-dimensional axes with positive radial nodes; finite nonnegative base/elastic/diameter profiles of one common spatial shape; CX field (when enabled) finite nonnegative (nvr,nvx,nx)",
        "assumptions": [
            "The wall loss 2 vr / D is the saved free-flight pipe model; it is a geometric escape frequency, not a surface-interaction model.",
            "A zero pipe diameter means no wall loss in the saved arithmetic; whether the published contract should instead reject zero diameters is an open expert question.",
        ],
    },
    [
        _port("vr", "The radial velocity axis.", "source-normalized", "[nvr]", "real array-like",
              "Finite, strictly positive nodes."),
        _port("vx", "The axial velocity axis.", "source-normalized", "[nvx]", "real array-like", "Finite."),
        _port("base_loss_frequency_s_inv", "The base ionization/dissociation loss profile.", "s^-1", "[nx]", "real array-like",
              "Finite and nonnegative."),
        _port("elastic_frequency_s_inv", "The elastic frequency profile.", "s^-1", "[nx]", "real array-like",
              "Finite and nonnegative, same shape as the base loss."),
        _port("pipe_diameter_m", "The pipe diameter profile.", "m", "[nx]", "real array-like",
              "Finite and nonnegative; zero diameter cells get zero wall loss."),
        _port("charge_exchange_frequency_s_inv", "The optional CX frequency field.", "s^-1", "[nvr,nvx,nx]", "real array-like",
              "When enabled: required, finite and nonnegative. When disabled: ignored even if supplied.",
              required=False, default=None),
        _port("charge_exchange_enabled", "Whether the CX contribution is included.", "dimensionless", "scalar", "boolean scalar",
              "The saved branch selector.", required=False, default=True),
    ],
    [_port("total_frequency_s_inv", "The assembled total loss frequency.", "s^-1", "[nvr,nvx,nx]", "float64 array",
           "Finite; nonnegative on the declared domain (all inputs nonnegative).")],
    _app(
        ["Finite aligned profiles and axes with positive radial nodes."],
        ["Total-loss assembly for H and H2 spatial-advance schemes with optional wall and CX terms."],
        ["Negative loss contributions; negative diameters; enabled CX without a field."],
    ),
    _fail("Raises ValueError when the axes/profiles violate the finiteness/nonnegativity/alignment contract, or enabled charge exchange lacks its explicit field."),
    {
        "description": "Assemble the total loss with wall and CX terms, confirm the zero-diameter wall semantics and the enabled-CX fail-closed rule.",
        "code": "import numpy as np\nfrom scirel.kinetic import assemble_neutral_total_collision_frequency\nresult = assemble_neutral_total_collision_frequency([1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], np.ones((2, 2, 2)))\nnp.testing.assert_allclose(result[:, :, 0], [[10.0, 10.0], [11.0, 11.0]])\nnp.testing.assert_allclose(result[:, :, 1], [[11.0, 11.0], [11.0, 11.0]])\ndisabled = assemble_neutral_total_collision_frequency([1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], charge_exchange_enabled=False)\nnp.testing.assert_allclose(disabled[:, :, 0], [[9.0, 9.0], [10.0, 10.0]])\ntry:\n    assemble_neutral_total_collision_frequency([1.0], [1.0], [1.0], [1.0], [0.0])\nexcept ValueError as error:\n    assert 'charge exchange' in str(error)\nelse:\n    raise AssertionError('enabled CX without a field must fail closed')",
        "expected": "The assembled totals with the saved wall-loss broadcast and the zero-diameter semantics; enabled CX without a field is rejected.",
    },
    [
        "That the assembly equals an independent recomputation of the wall broadcast and the saved term order.",
        "That the zero-diameter cells carry zero wall loss and enabled-CX-without-field fails closed.",
        "The alignment and nonnegativity failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

# 8 atomic-scattered-sources-reduction ----------------------------------------
DOCS.append(_doc(
    "scirel.kinetic.atomic-scattered-sources-reduction",
    {
        "package": "原子双通道散射源归约", "title_en": "Atomic scattered-source two-channel reduction",
        "title_zh": "原子双通道散射源归约", "module": "scirel.kinetic.atomic_scattered_sources_reduction",
        "symbol": "reduce_atomic_scattered_sources",
        "signature": "reduce_atomic_scattered_sources(charge_exchange_source_distribution, elastic_source_distribution)",
        "taxonomy": ["kinetic", "neutral-transport", "scattering-source", "reduction"],
        "anchor": "KN1DPy/kinetic_h.py:1297-1317",
        "sha": "6fe5d850c7aef5c07f8c5996dc65948a6ba35f1ea10e120dcb6fd28ed61ff159",
        "tests": ["tests/operator_contracts/test_scattered_source_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The source-order sum Beta_CX + OmegaM of the atomic charge-exchange and elastic "
    "scattered-generation source distributions on one velocity-space mesh, preserving signed "
    "values.",
    {
        "relation": "Beta = Beta_CX + OmegaM pointwise on one (nvr,nvx,nx) mesh",
        "direction": "two aligned source fields -> their pointwise sum",
        "definition": "The saved plain pointwise addition; no clamping of signed values",
        "model": "the saved formal implementation's scattered-source aggregation",
        "geometry": "two velocity dimensions over one spatial axis",
        "coordinates": "all fields in the source's discrete source-distribution units",
        "boundary": "two finite aligned three-dimensional fields; signed values preserved",
        "assumptions": [
            "The caller owns the upstream per-channel source construction; this asset only aggregates.",
            "Signed entries are meaningful (upstream normalizations may subtract); the saved sum does not clamp.",
        ],
    },
    [
        _port("charge_exchange_source_distribution", "The CX scattered source.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field; signed values preserved."),
        _port("elastic_source_distribution", "The elastic scattered source.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field aligned to the CX field; signed values preserved."),
    ],
    [_port("total_source", "The aggregated scattered source.", "source-discrete", "[nvr,nvx,nx]", "float64 array",
           "The pointwise sum; finite; signed values preserved.")],
    _app(
        ["Two finite aligned scattered-source fields."],
        ["Atomic generation-source aggregation on a shared mesh."],
        ["Misaligned meshes; non-finite fields."],
    ),
    _fail("Raises ValueError when the fields are not finite aligned three-dimensional arrays."),
    {
        "description": "Aggregate two atomic sources, including a cancellation case, and reject misalignment.",
        "code": "import numpy as np\nfrom scirel.kinetic import reduce_atomic_scattered_sources\nsource = np.ones((1, 2, 3))\nnp.testing.assert_allclose(reduce_atomic_scattered_sources(source, 2 * source), 3 * source)\nnp.testing.assert_allclose(reduce_atomic_scattered_sources(source, -source), np.zeros_like(source))\ntry:\n    reduce_atomic_scattered_sources(source, np.ones((1, 2, 4)))\nexcept ValueError as error:\n    assert 'finite aligned 3-D' in str(error)\nelse:\n    raise AssertionError('a misaligned field must be rejected')",
        "expected": "The pointwise sums including exact cancellation; a misaligned field is rejected.",
    },
    [
        "That the sum equals an independent pointwise addition and preserves signed values.",
        "The alignment and finiteness failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256, including a signed cancellation case. Environment-gated; historical development evidence only.",
    ],
))

DOCS.append(_doc(
    "scirel.kinetic.molecular-scattered-sources-reduction",
    {
        "package": "分子三通道散射源归约", "title_en": "Molecular scattered-source three-channel reduction",
        "title_zh": "分子三通道散射源归约", "module": "scirel.kinetic.molecular_scattered_sources_reduction",
        "symbol": "reduce_molecular_scattered_sources",
        "signature": "reduce_molecular_scattered_sources(wall_source_distribution, charge_exchange_source_distribution, elastic_source_distribution)",
        "taxonomy": ["kinetic", "neutral-transport", "scattering-source", "reduction"],
        "anchor": "KN1DPy/kinetic_h2.py:1422-1546",
        "sha": "4b17a8e6a15d2c7ebf4e0fdc58db7e7b81af8c0139687182dbe8c5a9e6542898",
        "tests": ["tests/operator_contracts/test_scattered_source_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The source-order sum Swall + Beta_CX + OmegaM of the molecular wall, charge-exchange and "
    "elastic scattered-generation source distributions on one velocity-space mesh, preserving "
    "signed values.",
    {
        "relation": "Beta = Swall + Beta_CX + OmegaM pointwise on one (nvr,nvx,nx) mesh",
        "direction": "three aligned source fields -> their pointwise sum in the saved source order",
        "definition": "The saved plain pointwise addition in the order wall, CX, elastic; no clamping of signed values",
        "model": "the saved formal implementation's scattered-source aggregation",
        "geometry": "two velocity dimensions over one spatial axis",
        "coordinates": "all fields in the source's discrete source-distribution units",
        "boundary": "three finite aligned three-dimensional fields; signed values preserved",
        "assumptions": [
            "The wall-source channel exists only on the molecular side of the saved source; this is why the molecular reduction is a separate asset from its atomic sibling.",
            "The caller owns the per-channel source construction; this asset only aggregates.",
        ],
    },
    [
        _port("wall_source_distribution", "The wall scattered source.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field; signed values preserved."),
        _port("charge_exchange_source_distribution", "The CX scattered source.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field aligned to the wall field."),
        _port("elastic_source_distribution", "The elastic scattered source.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field aligned to the wall field."),
    ],
    [_port("total_source", "The aggregated scattered source.", "source-discrete", "[nvr,nvx,nx]", "float64 array",
           "The pointwise sum in the saved order; finite; signed values preserved.")],
    _app(
        ["Three finite aligned scattered-source fields."],
        ["Molecular generation-source aggregation on a shared mesh."],
        ["Misaligned meshes; non-finite fields."],
    ),
    _fail("Raises ValueError when the fields are not finite aligned three-dimensional arrays."),
    {
        "description": "Aggregate three molecular sources in the saved order and reject misalignment.",
        "code": "import numpy as np\nfrom scirel.kinetic import reduce_molecular_scattered_sources\nrng = np.random.default_rng(31)\nwall, cx, elastic = (rng.random((2, 3, 4)) for _ in range(3))\nresult = reduce_molecular_scattered_sources(wall, cx, elastic)\nnp.testing.assert_array_equal(result, wall + cx + elastic)\ntry:\n    reduce_molecular_scattered_sources(wall, cx, np.ones((2, 3, 5)))\nexcept ValueError as error:\n    assert 'finite aligned 3-D' in str(error)\nelse:\n    raise AssertionError('a misaligned field must be rejected')",
        "expected": "The pointwise sum in the saved order; a misaligned field is rejected.",
    },
    [
        "That the sum equals an independent pointwise addition in the saved order and preserves signed values.",
        "The alignment and finiteness failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

DOCS.append(_doc(
    "scirel.kinetic.elastic-regeneration-aggregation",
    {
        "package": "弹性重生散射源聚合", "title_en": "Elastic regeneration-source channel aggregation",
        "title_zh": "弹性重生散射源聚合", "module": "scirel.kinetic.elastic_regeneration_aggregation",
        "symbol": "aggregate_elastic_regeneration_source",
        "signature": "aggregate_elastic_regeneration_source(frequencies_s_inv, regenerated_distributions)",
        "taxonomy": ["kinetic", "neutral-transport", "elastic-scattering", "aggregation"],
        "anchor": "KN1DPy/kinetic_h.py:1340-1398; kinetic_h2.py:1468-1538",
        "sha": "8957adc7a5f0cd11cbdc6b3c6738057adbab660285c38fb2da490db09f7919c0",
        "tests": ["tests/operator_contracts/test_scattered_source_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The channel-keyed elastic regeneration sum sum_q Omega_q[x] * M_q(vr,vx,x): each named "
    "channel contributes its one-dimensional frequency profile multiplied into its "
    "three-dimensional regenerated distribution.",
    {
        "relation": "Beta_EL = sum over channels q of Omega_q[x] * M_q[vr,vx,x]",
        "direction": "named channel frequency profiles plus regenerated distributions -> one aggregated source",
        "definition": "The frequency and distribution key sets must match exactly; each term multiplies the (nx,) profile into the last axis; the saved dict iteration order defines the float summation order",
        "model": "the saved formal implementation's channel aggregation",
        "geometry": "two velocity dimensions over one spatial axis, one term per declared channel",
        "coordinates": "frequencies in s^-1; distributions in the source's discrete units",
        "boundary": "matching nonempty key sets; finite nonnegative (nx,) frequencies; finite nonnegative (nvr,nvx,nx) distributions with a matching spatial axis",
        "assumptions": [
            "Channel keys are caller-declared identifiers (e.g. species-pair names); the asset does not interpret them.",
            "Distributions and frequencies are expected nonnegative by physics and enforced so, as saved.",
        ],
    },
    [
        _port("frequencies_s_inv", "The per-channel elastic frequency profiles.", "s^-1", "mapping name->[nx]", "mapping of real array-like",
              "Finite and nonnegative; keys must match the distribution mapping exactly."),
        _port("regenerated_distributions", "The per-channel regenerated distributions.", "source-discrete", "mapping name->[nvr,nvx,nx]", "mapping of real array-like",
              "Finite and nonnegative; each spatial axis must match its frequency profile."),
    ],
    [_port("regeneration_source", "The aggregated regeneration source.", "source-discrete s^-1", "[nvr,nvx,nx]", "float64 array",
           "Finite and nonnegative; the saved-order channel sum.")],
    _app(
        ["Matching nonempty channel key sets with aligned finite nonnegative fields."],
        ["Elastic regeneration aggregation over caller-declared species-pair channels."],
        ["Mismatched key sets; empty channel sets; negative or non-finite fields; spatial-axis mismatches."],
    ),
    _fail("Raises ValueError when the key sets do not match, no channel is present, or any field violates the finiteness, nonnegativity, or alignment contract."),
    {
        "description": "Aggregate two named channels and confirm the key and field fail-closed contracts.",
        "code": "import numpy as np\nfrom scirel.kinetic import aggregate_elastic_regeneration_source\nfreqs = {'a': np.array([1.0, 2.0]), 'b': np.array([0.5, 1.0])}\ndists = {'a': np.ones((1, 1, 2)), 'b': np.ones((1, 1, 2))}\nresult = aggregate_elastic_regeneration_source(freqs, dists)\nnp.testing.assert_array_equal(result, [[[1.5, 3.0]]])\ntry:\n    aggregate_elastic_regeneration_source(freqs, {'a': np.ones((1, 1, 2))})\nexcept ValueError as error:\n    assert 'channel keys must match' in str(error)\nelse:\n    raise AssertionError('mismatched keys must be rejected')",
        "expected": "The channel-weighted sum; mismatched keys are rejected.",
    },
    [
        "That the aggregation equals an independent channel-weighted sum in the saved iteration order.",
        "The key-set, alignment, and nonnegativity failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))

DOCS.append(_doc(
    "scirel.kinetic.simple-charge-exchange-source",
    {
        "package": "简化电荷交换散射源", "title_en": "Simple charge-exchange scattered-generation source",
        "title_zh": "简化电荷交换散射源", "module": "scirel.kinetic.simple_charge_exchange_source",
        "symbol": "assemble_simple_charge_exchange_source",
        "signature": "assemble_simple_charge_exchange_source(target_distribution, charge_exchange_frequency_s_inv, previous_generation_distribution, cylindrical_weight, dvx)",
        "taxonomy": ["kinetic", "neutral-transport", "charge-exchange", "source"],
        "anchor": "KN1DPy/kinetic_h.py:1297-1317; kinetic_h2.py:1444-1461 (the Simple_CX construction)",
        "sha": "b4962366c43c308aa0ca8e047d00fb34ce2756f1db025e14a77339b1de50770f",
        "tests": ["tests/operator_contracts/test_scattered_source_reductions.py",
                   "tests/operator_contracts/test_neutral_moments_family_l1.py"],
    },
    "The cell-local charge-exchange scattered-generation source: the target distribution scaled "
    "per spatial cell by the quadrature contraction of the CX frequency field with the previous "
    "generation's distribution.",
    {
        "relation": "source[vr,vx,x] = target[vr,vx,x] * rate[x] with rate[x] = sum over (vr,vx) of W(vr,vx) * alpha[vr,vx,x] * previous[vr,vx,x] * dvx[vx]",
        "direction": "target, CX frequency, previous generation and quadrature -> the scattered source",
        "definition": "The saved cell-local construction: the rate contraction reduces the previous generation against the CX field, and the target shape is scaled per cell; no cross-cell transport enters",
        "model": "the saved formal implementation's Simple_CX per-generation scattering step",
        "geometry": "two velocity dimensions over one spatial axis; cell-local in space",
        "coordinates": "all fields in the source's discrete units; frequency in s^-1",
        "boundary": "finite aligned three-dimensional target/frequency/previous fields; finite nonnegative (nvr,nvx) weight and (nvx) dvx; nonnegative frequency, weight, and dvx",
        "assumptions": [
            "Cell-locality is the saved per-generation scattering approximation; transport between cells is a separate step in the source.",
            "The caller owns the quadrature normalization and the CX frequency field.",
        ],
    },
    [
        _port("target_distribution", "The target distribution to scale.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field."),
        _port("charge_exchange_frequency_s_inv", "The CX frequency field.", "s^-1", "[nvr,nvx,nx]", "real array-like",
              "Finite and nonnegative, aligned to the target."),
        _port("previous_generation_distribution", "The previous generation's distribution.", "source-discrete", "[nvr,nvx,nx]", "real array-like",
              "A finite three-dimensional field aligned to the target."),
        _port("cylindrical_weight", "The cylindrical quadrature weight.", "source-discrete measure", "[nvr,nvx]", "real array-like",
              "Finite and nonnegative, aligned to the leading axes."),
        _port("dvx", "The axial cell sizes.", "source-discrete measure", "[nvx]", "real array-like",
              "Finite and nonnegative, aligned to the velocity axis."),
    ],
    [_port("scattered_source", "The cell-local scattered source.", "source-discrete s^-1", "[nvr,nvx,nx]", "float64 array",
           "Finite; the target scaled by the per-cell rate.")],
    _app(
        ["Finite aligned fields with nonnegative frequency, weight, and cell sizes."],
        ["Per-generation CX scattering on a shared quadrature for atomic and molecular fields."],
        ["Misaligned meshes; negative frequency, weight, or cell sizes; non-finite fields."],
    ),
    _fail("Raises ValueError when any field is non-finite or the alignment/nonnegativity contract is violated."),
    {
        "description": "Assemble one CX scattered source and confirm the cell-local rate contraction and fail-closed contracts.",
        "code": "import numpy as np\nfrom scirel.kinetic import assemble_simple_charge_exchange_source\ntarget = np.ones((1, 2, 2))\nalpha = np.array([[[2.0, 3.0], [4.0, 5.0]]])\nprevious = np.ones((1, 2, 2))\nweight = np.ones((1, 2))\ndvx = np.array([0.5, 1.0])\nresult = assemble_simple_charge_exchange_source(target, alpha, previous, weight, dvx)\nnp.testing.assert_allclose(result, [[[5.0, 6.5], [5.0, 6.5]]])\ntry:\n    assemble_simple_charge_exchange_source(target, alpha, previous, weight, np.array([0.5, -1.0]))\nexcept ValueError as error:\n    assert 'finite and aligned' in str(error)\nelse:\n    raise AssertionError('a negative dvx must be rejected')",
        "expected": "The target scaled by the per-cell contracted rate; a negative dvx is rejected.",
    },
    [
        "That the source equals an independent cell-local rate contraction with the saved operation order.",
        "The alignment and nonnegativity failure contracts.",
        "Exact bit-level replay against the saved KN1DPy implementation, pinned by SHA-256. Environment-gated; historical development evidence only.",
    ],
))


def main():
    written = []
    for doc in DOCS:
        target = OUT / f"{doc['asset_id']}.json"
        if target.exists():
            raise FileExistsError(f"refusing to overwrite an existing document: {target}")
        target.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n",
            encoding="utf-8", newline="\n",
        )
        written.append(target.name)
    print(f"written {len(written)} documents")


if __name__ == "__main__":
    main()
