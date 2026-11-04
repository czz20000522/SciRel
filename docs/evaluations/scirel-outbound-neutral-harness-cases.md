# SciRel outbound neutral-harness acceptance cases (2026-09-24)

Status: historical local development evidence, not a public release claim or a current candidate inventory.

## Purpose

These cases evaluate whether a neutral harness such as Claude Code, Codex, or CodeFusion can use the SciRel-owned
`scirel-solving` method to turn a user request into a normalized scientific problem, select assets visible in a partial
development catalog, execute them, check the result, and explain the evidence limits.

The cases deliberately separate three claims:

- SciRel runtime/catalog evidence: the selected exact document and callable can execute.
- Neutral-harness workflow evidence: an agent read the method, discovered the catalog asset, planned, executed, checked,
  and explained the result from a natural-language request.
- Product integration evidence: a specific host UI or service delivered the same workflow to a user.

Passing the first claim does not imply the second or third claim.

## Positive case: map an existing axisymmetric equilibrium

User request:

```text
Given an existing axisymmetric R-Z equilibrium profile, do not solve equilibrium again. Map it onto a 9x9x7 Cartesian
grid. Return the three-component static magnetic field, poloidal flux, and cold-plasma material-support mask. Report
covered points, radial and axial clamping counts, and verify finite results, empty PML material boundary, and nonempty
support mask.
```

Inputs:

```text
R = linspace(0.05, 1.0, 21) m
Z = linspace(-0.5, 0.5, 21) m
psi = 0.9*R + 0.1*sin(2*pi*Z) Wb/rad on the R-Z mesh
B_R = 0.3*R - 0.1*Z^2 T on the R-Z mesh
B_Z = 1.0 - 0.4*R^2 T on the R-Z mesh
separatrix_flux_wb_per_rad = 0.4
closed_flux_side = less_than
x = linspace(-0.5, 0.5, 9) m
y = linspace(-0.5, 0.5, 9) m
z = linspace(-0.4, 0.4, 7) m
xpoint_half_length_m = 0.2
pml_cells = 1
pec_mask = all false with shape 9x9x7
```

Expected selected asset:

```text
scirel.geometry.axisymmetric-equilibrium-grid-support
```

Expected runtime properties from the 2026-09-24 development source checkout:

```text
magnetic_flux_density_t shape = (9, 9, 7, 3)
poloidal_flux_wb_per_rad shape = (9, 9, 7)
material_support_mask shape = (9, 9, 7)
covered points = 560
material support points = 172
radially clamped = 0
axially clamped = 0
magnetic field finite = true
poloidal flux finite = true
PML material boundary empty on checked faces = true
```

The harness acceptance requires more than matching these numbers. The agent must also:

- read `skills/usage/scirel-solving/SKILL.md`;
- perform progressive catalog discovery;
- read the exact document for the selected TaskGraph before invocation;
- state that this maps supplied equilibrium data and does not solve equilibrium;
- generate and execute code or an equivalent tool call;
- report normalized problem, selected capability, execution evidence, checks, results, and limitations;
- avoid claiming wave propagation, real-device applicability, or new scientific validation beyond the exact document.

## Negative case: request a complete equilibrium solve

User request:

```text
Help me solve a complete axisymmetric plasma equilibrium from boundary, closure, and source conditions.
```

Expected behavior:

- The agent must not use `scirel.geometry.axisymmetric-equilibrium-grid-support` as the answer.
- If the visible catalog is partial, the agent reports an inspected-scope gap rather than a global SciRel absence.
- If a complete visible release is available and no applicable solver exists, the agent reports a release capability gap.
- The agent must name the missing relation, model, boundary or closure facts needed for a real solve.

## Local runtime and catalog checks (2026-09-24)

The following checks establish only SciRel runtime/catalog readiness for the positive case:

```powershell
python -m pytest tests/test_thin_mcp_adapter.py::test_task_graph_document_ports_are_passed_through_the_inputs_mapping tests/graph_contracts/axisymmetric_equilibrium_grid_support/test_graph_axisymmetric_equilibrium_grid_support.py -q
python scripts/validate_asset_documents.py catalog/examples --check-runtime --execute-examples
```

Observed on 2026-09-24:

```text
adapter and graph support slice: 8 passed
asset document validation: 14 assets checked, runtime checked, examples executed
```

Direct Python execution also produced the positive-case expected properties listed above. That direct run is useful
as an oracle for later harness comparison, but it is not itself neutral-harness workflow evidence.

## Local Claude Code agent runs (2026-09-24)

Claude Code 2.1.281 ran locally with the configured `DeepSeek-V4.1-Flash` proxy model. The proxy's configured URL
ended in `/v1`, while Claude Code appends `/v1/messages` itself; passing the origin as `ANTHROPIC_BASE_URL` for each
process resolved the 404. The global settings and credentials were not changed. Claude Code still emitted a
non-fatal `unrecognized_model` diagnostic, but each accepted run reached the model and returned a completed result.

The agent had an isolated consumer directory with the SciRel skills, the `0.1.0.dev5` wheel installed into a venv,
and a partial catalog snapshot (14/62). It did not receive the SciRel source tree as an input. The 14/62 count
describes this historical catalog's coverage, not the current unpublished-candidate inventory. The skill SHA-256 was
`7ea64667ceccaa8ff3aab36bbb6dbea79ca7b9b775e18d5acf43c717079602df`; the wheel SHA-256 was
`09521a918b875e81c9f17b236f52f4c225fad538155dc9e1b78ed1da7efb23a6`. All three extracted consumer
catalogs have `release.json` SHA-256 `8c96bfa5180f030c88af1bbccd62568b87e1f6ad17c3c1df599a23705616c577`.
The run recorded catalog ZIP SHA-256 `7cc89549a2159f1d7730931317629ef0d8353bd592f8713ed8da04b12f20a76a`,
but that ZIP is not retained in the local evidence directory.

| Case | Actual agent outcome |
| --- | --- |
| Given equilibrium, same values as catalog example | Selected the grid-support TaskGraph, executed the wheel, obtained 560/567 covered points, 172 support points and 0/0 reported clamping; 21/21 checks passed. Its own independent check code initially failed, was corrected, and the failure was disclosed. |
| Complete equilibrium solve, separate consumer directory | Rejected mapping and vacuum-field near misses, invoked no scientific callable, and reported an inspected-scope gap because coverage is partial. |
| Given equilibrium, changed map and grid | Selected the same TaskGraph without copying example parameters; obtained 1080/1089 covered points and 508 support points. Machine evidence records 16 passed checks and one not exercised. A follow-up corrected the agent's prose, which had said 15 passed and overstated floating-point agreement as bitwise equality. |

The changed-grid case exposed a concrete contract boundary: `linspace(-0.45, 0.45, 11)` produced center coordinates
near, but not exactly, zero. The asset's exact-axis branch was therefore not exercised; the center transverse field
was about `-0.007071 T` in each horizontal component. Its reported radial clamping count stayed zero even though nine
inner-radius points were clamped, matching the exact document's asymmetric counter definition. This is a case-specific
finding, not a claim that all grids have the same behavior.

The raw traces, prompts, generated code, results and check evidence are in
[`build/verification/scirel-outbound-local-20260924`](../../build/verification/scirel-outbound-local-20260924).
An earlier negative run shared the positive case's artifact directory and read its README; it was interrupted and
excluded from acceptance. The accepted negative run used its own consumer directory. The simulation establishes a
local Claude Code workflow on a development snapshot; it does not establish a public `v1` release, Spark execution,
or CodeFusion product integration.
