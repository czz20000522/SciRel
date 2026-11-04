# ASCOT5 source-first freeze boundary (2026-09-30)

Status: the historical `stage1-ASCOT5-20260919T173158Z` r6 `full_freeze`
self-report is not a qualified whole-source D1 handoff or D2 intake. Its
progress record has SHA-256
`62272c7e9d43b206f3a56be70729bd818936ba2c036be0ff1e4093d76645e0ba`.

A read-only run of the deployed `validate_capability_progress.py` (SHA-256
`5a1508803dddb543fe4810d29c0315ac50dcc581fb254170061c838ce98ca675`)
against r6's scope manifest, evidence matrix, the live extraction ledger and
candidate bundle, with `--require-closure-signal`, returned `valid=false`.
There were 23 errors: 22 v1 comparison receipts where delivery closure requires
v2, plus a missing `closure_signal.asset_entry_validation`. The old receipts
must remain historical; relabeling them does not create the required bindings.

The separate source-first reopen record,
`coordination/ascot5-source-first-reopen-20260925.txt` (SHA-256
`0ca648fdc236272dfa59b39e91e2c132e8bf5dac8665943d9f96d32bff934c4b`),
identifies a denominator gap. Frozen `a5py/__init__.py` (SHA-256
`5034f7b9cc9ab660b851298698ed23780dca37f49359e3046fde74960badc5e8`)
exposes `MarkerGenerator` as `Ascot.markergen`. In
`a5py/routines/markergen.py` (SHA-256
`9a6112040c7b1f09ef7878eff27019c54224013d0a2973eeb61d8ffdb22527ea`),
`generate` samples a 5D marker distribution, assigns physical weights,
computes phase-space coordinates and momentum, and optionally returns both
marker and weighted-particle distributions. `rhoto5d` maps a radial profile
to a normalized 5D distribution. The related
`a5py/routines/markergenerator.py` has SHA-256
`cf4cd1ee281573323390d571e16c434c018d654b7cbde443dfa135f9e897f2c0`.
The old blanket classification of `a5py/routines/*` as workflow glue does not
dispose of these executable physical outputs. Missing optional runtime
dependencies are not a scientific non-executability disposition.

Recovery must review the source routines as a whole and derive the physical
terminal/output denominator before a successor freeze. Each in-scope path
needs a source-free bundle entrypoint and same-input canonical plus
independently sealed holdout comparison. For randomized paths, bind the random
stream or draws in both executions; do not pass source-computed physical state
as candidate input. Preserve r6, its candidate and receipts, use the exact
successor bundle digest, and require independent source-first review and the
strict final gates before any D2 intake or export.

The later `ASCOT5-MARKERGEN-SAMPLING` lane ended with worker exit 0 and a
root-owned seal for attempt `marker-sampling-sourcefree-20260930-a1` (sealed
receipt SHA-256
`7a4477ab79c10a830631ada7885a11ffc92836aa1d7afa28e152baf2061a86da`).
Its handoff SHA-256 is
`549fe5216c16546b600d53e10cd33c8b3db329092f639f17b8364dc70def75b7`.
The sole probe invocation failed during `unittest` discovery because its
hyphenated start directory was not importable. No test case or source/operator
comparison ran, and the handoff itself makes no parity claim.

The independent versioned reviewer saved
`coordination/reviews/ascot5-markergen-sampling-supervisor-independent-20260930.json`,
SHA-256 `0c942fe226c75b367c0d5b858a50306f13314a11a34e08e4ea0edcfe79f0c36e`.
Its verdict is `rejected`: 29 of 34 checks passed. The five failures were a
coordinator assignment without the packet-bound launch snapshot, absent
handoff SHA bindings for both expected code/test artifacts, and the packet's
`source_digest` in place of the required `source_identity` plus a nonempty
`source_anchor_sha256` map. The actual frozen source tree matched the recorded
`source_digest`; the reviewer failure is an identity-contract failure, not
evidence of source mutation. Preserve this packet, attempt, handoff and seal.
A fresh packet and attempt must satisfy the versioned runner contract and run
actual source/operator tests before any scientific or integration credit.

Read-only review of the sealed test proposal (SHA-256
`c8cdd84d4951c718568488ae33177d90fb72f55b82c7db1a058bb37f45bfe3b2`)
found two test-harness defects to repair in that fresh attempt:

- The failed probe command names the host's source directory in `PYTHONPATH`
  and the host's attempt directory as the `unittest` start path. Its receipt
  binds the source at `/source` and writable scratch at `/work` inside the
  container. The next invocation must use those mounted paths, for example
  `PYTHONPATH=/source python /work/staging/operators/a5py-5d-marker-generation/test_scientific_operator.py`
  through the mandatory wrapper after staging the test in the fresh attempt.
- In `source_draw_patch`, line 33 passes `2*pi*draws["gyrophase"]` as the
  mocked return of `np.random.rand`. Frozen `markergen.py` (SHA-256
  `9a6112040c7b1f09ef7878eff27019c54224013d0a2973eeb61d8ffdb22527ea`)
  multiplies that returned uniform by `2*pi` at lines 156, 169, 182, and 201.
  The candidate also multiplies the raw uniform once. The patched source would
  therefore use `(2*pi)^2*u` while the candidate uses `2*pi*u`, causing false
  gyrophase and particle-velocity mismatches. Feed the same raw uniform to
  both paths and only then assess scientific differences.

These are review findings, not executed parity results. The sealed test and
attempt remain unchanged.

The fresh `ASCOT5-MARKERGEN-SAMPLING-R1` worker also failed without scientific
credit. Its packet SHA-256 is
`fac67b9497365cb9d20b74f3353443397e3be41fec70fa54c342c4aca15b3106`.
The first probe used host absolute paths inside the container, despite the
receipt binding source to `/source` and candidate to `/candidate`; both reads
failed and the probe exited 2. The packet attempt was then consumed. Worker
exit was 78 because `handoff.json` had an empty `tests_actually_run` array;
the postcondition error SHA-256 is
`6e7711059ecf86cc438b0f3126846109a83110e0ae416a0ffc33aa910d7f14d3`.
There is no sealed attempt. The handoff's claimed
`evidence/worker-attempt-failure.json` is absent from the terminal attempt.

The same versioned independent reviewer saved
`coordination/reviews/ascot5-markergen-r1-supervisor-independent-rejected-20260930.json`,
SHA-256 `a0af748e452a83e8b7d6f7b681510f11d10faff042b602a6c615db235493a362`.
Its verdict is `rejected` (23 of 34 checks passed). In addition to the
terminal, test, artifact and evidence failures, R1 again lacks the packet's
`frozen_inputs.source_identity` and nonempty `source_anchor_sha256`, and its
slot receipt lacks a packet-bound launch assignment. A successor must use a
new packet/work item/attempt with those identities and mounts fixed before
launch, plus an executed comparison and digest-bound handoff. R1 remains a
historical failed lane; do not patch it into an accepted review.

The next `ASCOT5-MARKERGEN-SAMPLING-R2` lane produced a private callable and
direct unittest proposal, but its only probe exited 127 before Python started.
The receipt (SHA-256
`f47f5adbc84b54e2ba769ec59fb747a26e8e5f9eabf9b1fb8e804ba5cee0570f`)
records the container command as `['--', 'python',
'/work/staging/operators/a5py-5d-marker-generation/test_scientific_operator.py']`.
The deployed `probe-container.sh` usage is `IMAGE COMMAND...`; after the image
it forwards arguments verbatim, so `--` became the attempted executable.
The R2 handoff (SHA-256
`b6b64289e4ff2ca0092a8f1ba21421e5759202f1d14192cfd1cb69f03762cdaa`)
correctly reports zero executed scenarios and no scientific comparison. A
fresh successor must omit that separator, stage the retained proposal under
its own `/work`, and run the direct unittest through a new wrapper attempt
before any canonical or integration credit. The R2 attempt and receipt remain
unchanged.

A separate read-only contract check found that R2's rho/theta/phi test uses
`rho` edges `[0.2, 0.6] * unyt.m` and its handoff describes the geometry port's
`rho` input in meters. Frozen `a5py/ascotpy/libascot.py:765-802` defines
`input_rhotheta2rz`'s `rho` as normalized poloidal-flux coordinates, and the
source use at `a5py/ascotpy/__init__.py:1429` constructs `rho` with
`unyt.dimensionless`. A fake geometry port shared by source and candidate can
pass parity while preserving this wrong input unit. The fresh comparison must
use dimensionless rho edges and an explicit length scale inside the fake
geometry mapping; retain the original R2 proposal as unverified evidence.

At read-only preflight, `ASCOT5-MARKERGEN-SAMPLING-R3` was still active and its
`handoff.json` was empty; no R3 scientific result is established. Its packet
(SHA-256 `2c151d6e4df7bbd1e9a8159b927b24f9be0c23d8d67a0047e6019afe40922f0f`)
uses a fresh attempt and states the corrected `IMAGE COMMAND...` invocation,
but `frozen_inputs` again contains `source_digest` without the versioned
reviewer's required `source_identity` or `source_anchor_sha256` map. The
coordinator should check that identity-contract failure after R3 terminates;
the running packet and attempt are preserved as issued.

R3 then ended with worker exit 0 and a root-owned seal (sealed receipt SHA-256
`f5f7ef92e6bbbe77b297f670c4867a9a0b20ffabefe08b6e58fbfe0b2275e2e1`,
handoff SHA-256
`ce88ca4dbaf413ee7d23e90fb4e3030974735e8b43fe3830978077c25475bf84`).
Its one corrected `IMAGE COMMAND...` probe did start the container, but exited
1 before unittest discovery: importing `a5py.ascot5io.dist` enters
`a5py/ascotpy/__init__.py` and raises `ModuleNotFoundError: No module named
'wurlitzer'`. The probe receipt SHA-256 is
`6ff8ebf3e7d792bdfa5fb54d847bf5965ddc51c095a6a21dcb2c0fb4a5e6b94d`;
the worker's canonical evidence SHA-256 is
`b8080e53a6177563dba45d73bca4b7181509e40940aa331ca851d0ea548d5cb0`.
The handoff truthfully records zero executed branch cases and no source versus
proposal numerical comparison. `wurlitzer` is a declared source dependency
in `pyproject.toml` (SHA-256
`dd196144dd537ccbe7eb4e8d80160fc49774c745526c8d8a558c38a39b6c80e8`),
not a scientific non-executability disposition. The retained R3 test proposal
does use dimensionless `rho` edges, correcting R2's unit error, but remains
unexecuted. A network-disabled, read-only `pip list` of the pinned
`ascot5-py311-unyt` image confirmed that `h5py`, `wurlitzer`, and `xmlschema`
are all absent, although all three are declared in the frozen source's
`pyproject.toml`; adding only the first missing import would leave the runtime
incomplete. A fresh packet and attempt need a probe image with the declared
source import dependencies, the required source identity/anchor bindings, and
actual executed comparisons before review can credit this path; do not replay
the consumed R3 attempt or alter its seal.

Independent static review of R3's sealed proposal found a separate source-free
execution defect. Its `_marker_template` uses `unyt.particles` and `unyt.e`,
which the frozen `a5py/__init__.py` defines as ASCOT-specific units. In the
pinned image, network-disabled candidate-independent checks of bare `unyt`
raise `AttributeError` for both names. The R3 comparison module imports the
proposal first but imports `a5py` before calling it; that source-package side
effect would create the units and mask the proposal's standalone failure.
The successor must make its own unit setup explicit, preserve the source's
charge and marker-weight units, and execute a candidate-only case in a fresh
process before any source import. This is a static/environment finding; the
R3 numerical comparison still never ran.

The versioned `handoff-20260929-v1/review-worker.py` contract identifies three
additional R3 review failures from immutable current artifacts, pending the
coordinator's formal verdict. Its packet omits `frozen_inputs.source_identity`
(the 64-hex source-tree digest) and a nonempty
`frozen_inputs.source_anchor_sha256` map of relative frozen-source files to
their SHA-256 values. Its `worker-slot-acquire.json` has no root-owned,
read-only `assignment_at_launch` snapshot bound to the packet SHA, attempt,
lane, candidate digest, and tool hashes. Finally, R3's handoff `evidence`
contains only prose strings. The reviewer accepts `{path, sha256}` records and
requires exactly one digest binding for each of the three absolute
`expected_artifacts` paths in the packet; none is supplied. A successor packet
must be complete before launch, and its handoff must bind actual artifact
bytes after execution. These mechanical findings do not convert R3's failed
probe into scientific evidence.

The coordinator's next private import-only shim probe,
`lanes/_coord-probe/attempts/marker-proposal-wurlitzer-shim-20260930-r1`,
also exited 1. Its receipt SHA-256 is
`8749dd2e263186505a19137d85681b2e5da40bf5faeef03bac727f8e76a4ac68`.
The receipt binds the same pinned image, network `none`, read-only source and
candidate mounts, and the staged direct test command with
`PYTHONPATH=/work/shims:/source`. It records no traceback or executed case;
the attempt contains no separate test output log. Therefore this result does
not establish why the import-only shim failed, that any scientific branch ran,
or that source and proposal agree. Await the coordinator's error audit and a
fresh executable comparison before crediting this path.

An independent source-only import audit now identifies a concrete earlier
runtime failure. Private attempt
`lanes/CF-SUP-IMPORT-AUDIT/attempts/import-shim-20260930-a2` used the same
fail-if-used `wurlitzer` shim (SHA-256
`3d0f63a27722f54b266d8bc465346e4edaf062c890e6fc7e3478d14838dcfc0c`)
with the pinned image, read-only `/source`, no candidate mount, and network
`none`. It ran `python -m a5py`, saving the complete output in
`evidence/import-output.txt` (SHA-256
`4dea42d0d9a7eab78025bfba517bdc95c3ec81422c9c99cbdf70f50c84d51700`).
The wrapper exited 1; its receipt SHA-256 is
`c617b16b69bb3a75759660c6c7de25fd4bdfa2452a11e3da1793bcd2de214409`.
This probe does not reproduce the coordinator's test invocation and cannot
assign its failure reason to that earlier attempt.

The saved traceback first reports missing `libascot.so`, then
`ImportError: cannot import name '_get_struct_class' from
'a5py.ascotpy.libascot'`. Frozen `a5py/ascotpy/libascot.py:23-85`
(SHA-256 `29955ee15faad75c087a8e30ff7fe3ba358887561c1bd2ee71d2c3d3f3c4b28f`)
defines `_get_struct_class` inside the successful `ascot2py` import block but
not the `except ImportError` block. Its caller at
`a5py/ascotpy/__init__.py:15` imports that name unconditionally. Thus the
pinned runtime cannot import the full frozen `a5py` package even with the
`wurlitzer` shim; it fails before the known absent `h5py` and `xmlschema`
imports are reached. This is an import/runtime boundary, not a disposition of
the executable marker relation. The next source-first test must use a runtime
with the native library and declared import dependencies, or independently
justify and audit a direct frozen-module test path whose import-only shims fail
if used. No marker case executed in this audit, and no parity or holdout credit
is claimed.

The coordinator then ran a fresh namespace-package bootstrap attempt,
`lanes/_coord-probe/attempts/marker-namespace-bootstrap-20260930-r2`.
Its wrapper receipt (SHA-256
`99e34741dc75057bcbf2fa4cab6869e04f68b693596cd1027ec251dd76ed1fc6`)
exited 1; retained `scratch/wrapper-output.txt` (SHA-256
`58507b32166b2725e8b0300cf9c022a70a3cecbbc56cd8606b872eaa1679ce0b`)
shows `AttributeError: module 'unyt' has no attribute 'e'` while importing
frozen `a5py/physlib/species.py`, before unittest discovery. The bootstrap
installed namespace packages to skip `a5py/__init__.py` but omitted that
module's ASCOT unit registration. Frozen `a5py/__init__.py:7-19` defines
`particles` and `e` and configures the ASCOT unit system; frozen
`a5py/ascot5io/marker.py:224-274` uses both units to construct markers.
The direct-source test path must reproduce those exact unit definitions before
loading source submodules, then prove every import-only `h5py`/native shim
remains unused during the tested relation. Separately, the proposal's
`_marker_template` also refers to `unyt.particles` and `unyt.e`; a fresh
candidate-only process must run it without importing `a5py` first. R2 supplies
no executed branch or parity evidence and remains a failed private attempt.

The R3 proposal's standalone failure is now executed, not only inferred from
the source. The sealed proposal was copied byte-for-byte into private attempt
`lanes/CF-SUP-CANDIDATE-AUDIT/attempts/marker-template-20260930-a1`
(proposal SHA-256
`f1d26256c8b379c8440e62e1ff2a6b4d23d51368f71bbe5c42afc738207d83d8`).
The mandatory wrapper used the pinned image with network `none`, read-only
source mount, and candidate mount unavailable. A fresh Python process imported
only the copied proposal and called `_marker_template("gc", 1)`; it exited 1
with `AttributeError: module 'unyt' has no attribute 'particles'`. The saved
`evidence/template-output.txt` SHA-256 is
`351bb67ba6f15b3b50da228c620c1abc3063f5ab9e273963d843fe56ef1b5f1f`;
the wrapper receipt SHA-256 is
`e2ffad06667a8e886f575f62dfd4e9d2de68accf0fe84f668cab707cce37f1f2`.
This is a candidate-only execution failure, not a source comparison. A
successor implementation must initialize its required custom units itself,
without relying on the source package's import side effects, then pass this
standalone check before paired numerical and holdout work.

A bounded scientific leaf comparison found another uncovered input boundary.
Frozen `a5py/physlib/__init__.py:90-98,126-130` (SHA-256
`ddd121997ec8fa6fd51c6287a5dd4227aa992dd6cd7ed99b63e9b6c71b89d709`)
interprets any momentum array whose first dimension is exactly 3 as a
three-component vector and sums its squared components before computing
`gamma_momentum`. `MarkerGenerator.generate` calls `energy_momentum` on the
length-`nmrk` `ppar/pperp` norm in its guiding-center branch. The R3 proposal's
`_momentum_norm` computes elementwise for all lengths. For `nmrk=3`, those
paths therefore have different output shapes and values; no declared marker
count restriction excludes this case.

Private wrapper attempt `lanes/CF-SUP-GAMMA-AUDIT/attempts/n3-20260930-a1`
executed the exact frozen source leaf and the sealed proposal leaf on identical
unit-bearing momentum arrays, without importing the source top-level package.
Its result SHA-256 is
`88e4e49bef7ebd46bef20803c900f171b5b76da4ef50ce4cc2a6acac5284fa77`,
wrapper receipt SHA-256
`d3c3a6081a98622d478c7be07c75362867636323ee3250a4f3ca525d00fd8755`,
and diagnostic script SHA-256
`7ddb6c02e8e939aa5f824b469bb58c8755c22c82a71ba7599cdfe261289a678b`.
At `mass=1 amu` and momentum components `1e-20,2e-20,3e-20 kg m/s`, source
gamma is scalar `1.0028206321671378`; the proposal gives
`[1.0002017375188472,1.0008067060840895,1.0018141751949268]`.
The four-sample control matched elementwise. This is a source/proposal leaf
comparison, not a whole-generator receipt. A source-first successor must
decide the intended scalar-versus-sample contract at `nmrk=3`; the full
generator counterexample below makes that decision unavoidable before claiming
the marker path is covered.

That full-function counterexample was then executed in a separate private
attempt, `lanes/CF-SUP-MARKER-N3/attempts/full-n3-20260930-a2`. The diagnostic
script (SHA-256
`745a59f33ebbc7d54c5cd780e8d5c17343861733fcc11cb5c7a8da3077484266`)
loads frozen `a5py/routines/markergen.py::MarkerGenerator.generate` through a
namespace-package bootstrap, supplies the exact frozen ASCOT unit definitions
and `src/VERSION=5.6.3`, and makes any HDF5 call fail. It compares the sealed
R3 proposal on the same 5D one-cell distribution, `nmrk=3`, guiding-center
`ppar/pperp` branch, and seven explicit random-draw calls. The wrapper used
the pinned image, read-only source, no candidate-bundle mount, and network
`none`; exit code was 0. Its receipt SHA-256 is
`01886de2eb1db163e16971accc6b25646b48e1ea09c84c14fcf258a5b2d49b0b`.

The machine-parseable `evidence/result.json` (SHA-256
`ddb156d410058544cec06addc9eb6670180198c5aae21ee5c82a2480fa014b05`)
records source `energy` as scalar `1389270.6084896035 eV` and proposal
`energy` as a length-3 vector
`[294097.0271026382,451931.8798540791,643570.5158476279] eV`.
Both emitted `ids=[1,2,3]` and identical pitch values. Optional plotting
warnings were retained separately in `evidence/import-warnings.txt` (SHA-256
`59842b4d1faf415a33764f115c470f8fa43dba64d020bdbb57cb3718ce54131e`).
This proves a reachable source/proposal terminal mismatch on the declared
input, beyond the earlier leaf result. It remains a private canonical-only
bounded experiment: no independently sealed holdout, exact successor bundle
binding, strict-v2 receipt, or project-level closure follows from it. A new
candidate must address the source behavior or receive an explicit source-first
scientific disposition before this target can pass.

The original coordinator's separate
`lanes/_coord-probe/attempts/marker-metadata-guard-20260930-r5` then became the
first successful proposed four-case comparison. Its wrapper exited 0 and ran
three tests; receipt SHA-256
`d2b7bd23e57d79d2f37541a18b233aaacc0800e094f91a12479ca3ba1f544543`,
test SHA-256
`c902c4034edb32e33591ed74804dad4c179ded8d5eb7ffaaf6f4ca702b74be36`,
and `evidence/marker-generate-canonical.json` SHA-256
`1d53e10995946d6e27fb774cc03308fb021d8f01c4699852abed61a0794a2580`.
For `nmrk=4`, the test compares every marker field and both reconstructed
distributions for `gc/prt`, `ppar/pperp` or `ekin/pitch`, and `r/phi/z` or
`rho/theta/phi` configurations with explicit draws. Its branch trace records
two cases per axis choice, eight rejection-loop passes, and actual geometry
and field-port calls. This is meaningful bounded canonical evidence.

The saved JSON records per-case pass labels and field names, not the source
and proposal numeric arrays or per-case execution hashes required for a
strict-v2 receipt. It states that no equivalent callable exists in the
current candidate bundle; the passed comparison is against the sealed private
proposal. The test imports source before calling that proposal, so it does not
replace the separate candidate-only failure above. It uses only `nmrk=4` and
does not cover the executed `nmrk=3` mismatch. No independently sealed
same-path holdout, successor bundle binding, D1 full freeze, or export is
established by this r5 pass.
