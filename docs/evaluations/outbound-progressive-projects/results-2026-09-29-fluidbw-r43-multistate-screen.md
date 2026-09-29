# fluidBW r43 multi-state numerical screen (2026-09-29)

This evaluator-manufactured [custom project](../../../build/verification/fluidbw-r43-multistate-screen-20260929/project/README.md)
uses the [portable development delivery](results-2026-09-29-fluidbw-r43-development-delivery.md)
archive SHA-256
`51864f4fe401b4995847bff533f26244304e0bfd264f9286337dbbd83e4f63e5`.
It fixes a bounded analyst task: join two parameter snapshots to six supplied
wavepoints, deliver both kinetic determinant paths at each derived physical
wavepoint, and mark rows where their **numerical difference** reaches the
Agent-chosen `1e-5` follow-up threshold. All inputs are manufactured for
development; they are not measurements or a real user's plasma state.

The earlier D3 graph project held one equilibrium, `kz` and `kx_fraction`
fixed while expanding only the frequency table. This project reads separate
state and probe files, joins each probe to its state, converts magnetic field
from mT to T and reference density from cm^-3 to m^-3, then varies
`omega_fraction`, absolute `kz` and `kx_fraction` per row. The SciRel
`kinetic-dispersion-relation` TaskGraph still owns the scale derivation,
frequency/wave-number conversion, tensors and determinant science; project
glue only orchestrates calls and calculates
`abs(det_sum-det_ronnmark)/max(abs(det_sum),abs(det_ronnmark))` for a numerical
review label. The [request and plan](../../../build/verification/fluidbw-r43-multistate-screen-20260929/project/request-and-plan.md)
records the selected exact contract and dependency DAG. The Weideman-only
function table cannot supply this physical-input result; a root scan answers
a different question.

The [current CSV](../../../build/verification/fluidbw-r43-multistate-screen-20260929/project/results/current.csv)
has six finite rows across two states. S0 maps to `6 T`, `2e20 m^-3`; S1
maps to `5.5 T`, `1.5e20 m^-3`. Four rows reached the numerical threshold;
S1/P1 had the largest observed relative difference,
`0.00012725282745028096`. Two others were below threshold. The
[baseline CSV](../../../build/verification/fluidbw-r43-multistate-screen-20260929/project/results/baseline.csv)
holds one point per state and is exactly the first two rows of the current
result. An independent raw JSON/CSV reader checked both SI source mappings,
reran the installed public graph and compared every delivered numeric cell
and label. The focused test changed each mapped output field in turn and
confirmed that this reader rejects both errors.

A malformed seventh probe failed at line 8 with exit code 1; the baseline
and current CSV hashes remained unchanged. The corrected ordinary entrypoint
regenerated identical current bytes. The project [replay entrypoint](../../../build/verification/fluidbw-r43-multistate-screen-20260929/project/replay.ps1)
passed using the base archive and isolated venv extracted outside the SciRel
source tree, including 2→6 rows, independent readback, failure/recovery and
the 1/1 focused standard-library regression. The custom archive SHA-256 is
`8e2be18603f4cbf7673ed9114ffa968a2df424fbaba33e8940b0dee3dd5d0307`;
all 18 members passed individual hash and size checks. The
[case evidence](../../../build/verification/fluidbw-r43-multistate-screen-20260929/case-evidence.md)
and [manifest](manifests/2026-09-29-fluidbw-r43-multistate-screen.json)
bind the actual inputs, outputs and implementation.

The screen only prioritizes numerical follow-up. It does not tell which
method is accurate, prove arbitrary-input source parity for the new state,
find a dispersion root, infer growth/damping or decide stability. The
wheel/catalog remain `pending_unapproved`; no expert, license or public
release decision follows from this project.
