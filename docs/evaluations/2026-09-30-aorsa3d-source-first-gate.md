# aorsa3d source-first freeze boundary (2026-09-30)

Status: D1 `full_freeze` is unproved. This is a read-only D2 follow-up to the
historical `stage1-aorsa3d-20260915T170735Z` r20 claim, not a replacement for
its frozen records or an intake decision.

The r20 progress record has SHA-256
`0444d35e4610f0c49784ecf39e2bc4bb0a5c37c0b9dc311993f6d4cd2b7f9705`.
On 2026-09-30, the deployed `validate_capability_progress.py` at SHA-256
`5a1508803dddb543fe4810d29c0315ac50dcc581fb254170061c838ce98ca675`
returned `valid=false` against r20's own scope manifest and evidence matrix,
the live extraction ledger and candidate bundle, with `--require-closure-signal`.
Its 42 errors consist of a missing `closure_signal.asset_entry_validation` and
41 v1 comparison receipts where delivery closure requires v2. The old receipts
remain historical evidence; changing their schema labels would not supply the
execution and input bindings required by v2.

The validator result is not the whole scientific objection. The independent
source-first veto at
`coordination/aorsa3d-source-first-reopen-20260925.txt` (SHA-256
`732d9df4ec540b253c45b5645b13150bb20fac0a42c3a83f43b08d4a4ec893e2`)
identifies physical source producers missing from r20's 16-target denominator:

- `fullwave/engineering_ports.py:299-420`, SHA-256
  `8748ed111c95e11db2237c00e565713a81e2621f9359e6d057fb134b033cea5a`:
  `compute_two_port` returns impedance, scattering, drive current, per-port
  power and physical diagnostics on both full-wave V/I and coupled RLC routes;
  optional Touchstone input adds deembedded comparison outputs.
- `fullwave/equilibrium_endplug.py:376-414,446-517`, SHA-256
  `a16f7f6ca62211870f1b775e1e4d16af27852013d6ab7dc803edf205de9a16c5`:
  `compute_equilibrium` returns field, pressure, current density and residual
  terminals; `compute_end_plug` returns potential, electric fields and sheath
  drops for its declared routes. An input map to another graph does not close
  these source producers.
- `fullwave/power_closure.py:319-552`, SHA-256
  `9115f4b7bda326f4fd4a9df44494cd54c3f9c1ef126cbe072fd4bf1dae163b76`:
  `evaluate_power_closure` computes control-volume eligibility and masks,
  source power, outward Poynting flux, cold and optional hot absorption,
  passivity, formal closure and augmented accounting from primary field and
  material arrays. `tests/test_kmax_power_closure.py:136-310` exercises the
  one-way/final-field and failing passivity or support branches. The current
  `operators/内控制体门控功率闭合` accepts these independently evaluated terms as
  caller inputs and explicitly does not compute them. The r20 target list and
  reassembly records contain no terminal path for this source producer. Its
  source-first disposition and complete output/branch mapping are still due.

The power report is also a reachable user-workflow terminal, not merely an
unreferenced helper. `fullwave/user_workflow.py:678-687,808-811` (SHA-256
`a332ced768f5ddfe6de5375a292af1413dc84dda1bf0c4378be05c141a44b50e`)
calls `run_power_closure_from_artifacts`, writes `power_closure.json`, and
records its closure and PML statuses in the stage summary. That runner at
`fullwave/power_closure.py:631-904` snapshots and validates the solution,
equilibrium, end-plug, two-port, summary, and hot-current artifacts before
feeding their primary arrays to `evaluate_power_closure`. It currently accepts
one-way hot-current artifacts only. Direct `evaluate_power_closure` also
supports `FINAL_FIELD_INCLUDES_HOT_CURRENT`: in that branch species hot power
enters formal closure; in one-way mode it remains augmented accounting.

The source report contains the control-volume gate and mask hashes, source and
outward flux, cold and per-species hot absorption, local/tensor passivity,
formal closure, augmented accounting, explicit non-evaluation of PML loss,
and optional RF-chain assumptions. Source tests (SHA-256
`2997fa24cfe204b4a80e3327ced45b94769dea5c7b35191455b5aa34664e613c`)
exercise one-way versus final-field roles, local cold and hot gain despite
zero integrated loss, source support on a control face, strict shapes, and the
artifact runner. A successor scope must dispose of both the direct physical
producer and the workflow's reachable report terminal. Its comparison must
start from identical primary field/material/current inputs (or bound source
artifacts), including blocked branches, rather than passing source-computed
power terms to the candidate closure leaf.

Recovery must first derive the complete source-backed terminal and branch
denominator, including these paths and any other executable physical outputs,
with explicit source dispositions. Then reassemble each in-scope path on the
current candidate through source-free entrypoints and obtain same-input
canonical and independently sealed holdout comparisons with exact v2 bindings.
Preserve r20 and prior receipts. The original run's veto also requires the
provider/model authorization or isolated preflight condition before resuming
its remote model session. No D2 intake, export or full-source freeze follows
from this evaluation.
