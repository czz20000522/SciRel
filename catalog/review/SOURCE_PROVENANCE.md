# Source provenance registry

This is **review evidence**, not public contract text. It records where a
capability came from so a future owner can go back to the exact source if a
problem appears. The public contract body continues to describe only the
scientific relation, ports, failure semantics and validation; it does not carry
source project names, checkout paths or commit hashes.

Read this together with `catalog/review/evidence/source-audit-*.md` and
`VERDICTS.json`. A source-parity record is not a claim of physical correctness.

## Collision family (KN1DPy)

Source project: `W-M-plasma-group/KN1DPy`
Source commit: `bb22c87210f64a899ee3f17719b150fb193985e2`
Canonical archive path: `/mnt/e/SciRel-lab/sources/upstream-canonical-20261009/archives/W-M-plasma-group--KN1DPy--bb22c87210f64a899ee3f17719b150fb193985e2.tar.gz`
Archive SHA-256: `a7bd21f…` (full value in `evidence/source-audit-collisions.md`)

| asset | source file | result |
| --- | --- | --- |
| `scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient` | `KN1DPy/rates/janev/sigmav_rec_h1s.py` | source-parity |
| `scirel.collisions.atomic-hydrogen-charge-exchange-cross-section` | `KN1DPy/rates/janev/sigma_cx_h0.py` | source-parity |
| `scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient` | `KN1DPy/rates/janev/sigmav_cx_h0.py` | source-parity |
| `scirel.collisions.atomic-hydrogen-collision-matrices` | `KN1DPy/kinetic_h.py` | source-parity (assembly) |
| `scirel.collisions.atomic-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_h_h.py` | source-parity |
| `scirel.collisions.atomic-hydrogen-omega-frequencies` | `KN1DPy/kinetic_h.py` | source-defect repair accepted |
| `scirel.collisions.atomic-molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_h_hh.py` | source-conflict repaired |
| `scirel.collisions.janev-electron-impact-ionization-rate` | `KN1DPy/rates/janev/sigmav_ion_h0.py`, `sigmav_ion_hh.py` | source-parity |
| `scirel.collisions.molecular-hydrogen-charge-exchange-cross-section` | `KN1DPy/rates/janev/sigma_cx_hh.py` | source-parity (2e-15 relative) |
| `scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient` | `KN1DPy/rates/janev/sigmav_cx_hh.py` | source-parity |
| `scirel.collisions.molecular-hydrogen-collision-matrices` | `KN1DPy/kinetic_h2.py` | source-parity (assembly) |
| `scirel.collisions.molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_hh_hh.py` | source-defect repair accepted |
| `scirel.collisions.molecular-hydrogen-omega-frequencies` | `KN1DPy/kinetic_h2.py` | source-defect repair accepted |
| `scirel.collisions.proton-atomic-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_p_h.py` | source-conflict repaired |
| `scirel.collisions.proton-molecular-hydrogen-elastic-cross-section` | `KN1DPy/rates/janev/sigma_el_p_hh.py` | source-parity |

The saved review contracts reference an older `KN1DPy/sigma/...` layout and
saved implementation hashes that are not upstream blobs at this commit; exact
saved-artifact replay is unavailable. This is recorded as a source-revision
evidence gap, distinct from mathematical parity.

## TORAX Coulomb

- source: `torax/_src/physics/collisions.py`, `calculate_log_lambda_ii`
- pinned upstream commit: `48448e610eddaa887e8f99b0d6d21f91e1cad674`
- E checkout: `/mnt/e/SciRel-lab/projects/torax/source/CURRENT/checkout/torax/_src/physics/collisions.py`
- result: source-parity of Sauter 1999 Eq. 18e; not NRL 2013 Eq. c.

## PDRK continuation

- source: `examples/beammode/em1d_dr.m`
- pinned upstream commit: `21c08f215ef143aeafdde4c746e393d8a1feaef7`
- result: default seed/grid source-parity; failure propagation is a deliberate
  SciRel fail-closed API policy, not parity.

## Pleiades equilibrium / inversion

- upstream Pleiades commit: `0161abb3e9a1d85143c650f068ec524d672fc9ab`
- Pleiades delivery source commit: `e4ec86fa72d7cdbf74c4799f16127c8b099e7c00`
- axisymmetric admitted graph: `task_graphs/新版轴对称各向异性Picard平衡/graph.py` sha256 `3de0fc07...`, `task_graph.yaml` sha256 `3410647a...`, `vcommit_9ed34...`
- direct inversion admitted graph: `task_graphs/直接各向异性参数反演/graph.py` sha256 `6d1c3b52...`, `task_graph.yaml` sha256 `997b3335...`, `vcommit_d196...`
- result: task-graph assembly parity; no Pleiades upstream anisotropic formula.
  Mask/terminal-order are SciRel API policies. Direct inversion remains held
  because the exact admitted graph artifact is missing from the FINAL payload;
  see `DIRECT_INVERSION_ARTIFACT.md`.

## Rules

- Source identity belongs here or in `evidence/`, never in `catalog/examples`.
- A source-parity entry answers "does this match the pinned source", not "is
  this physically correct".
- A source-defect repair is labelled as a repair; it is not parity.
- If the source archive/commit changes, update this registry and re-run the
  comparison.
