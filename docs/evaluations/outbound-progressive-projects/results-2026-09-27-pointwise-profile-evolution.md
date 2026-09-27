# Pointwise-to-profile demand evolution, fresh dev48 case

This Claude Code `2.1.281 --bare` case started from two **independent**
operating runs and then received a separate four-row sample set from **one**
simulated equilibrium branch. The [manifest](manifests/2026-09-27-pointwise-profile-evolution.json)
binds the original requests, inputs, three usage methods, raw traces, failure
counterexamples and frozen project archives. The run used the unapproved
SciRel `0.1.0.dev48` wheel (SHA-256
`284513daa5e4e6ed69c06e3706defd66c4887559fbf8d005b9ff7430b378afe3`)
and its 148/148 catalog (root
`sha256:0f6c5cf533016ad4a1b0d7d76cdc7d884cdabc8978e11b79d57931c6462f5f03`).
The CLI model label was `claude-fable-5`, assistant events said
`GLM-5.3-Flash`, and the underlying model was not confirmed. There was no
call/token cap. `--bare` disabled automatic memory and hooks, but the shared
filesystem was not a strict examiner/solver isolation boundary.

The first autonomous turn selected the pointwise firehose-margin asset and
called it separately for R-08 and R-19. The second autonomous turn reopened
the catalog, selected `scirel.diagnostics.firehose-mirror-margins` for the
new **shared** B-value sample set, and did not pool R-08/R-19 into that
derivative. Its four firehose margins were `-132070.38942485646`,
`380577.5195221761`, `606887.405705967`, and `896859.2691265158` Pa;
the mirror margins were `361929.61057514354`, `608577.5195221761`,
`918887.405705967`, and `1292859.2691265158` Pa. The literal
sampled-positivity flags were false/true. Independent arithmetic from the
raw CSV and the note's `p_perp(B)=100000+40000*B` law matched all eight
values. An external extraction installed the archived wheel from its own
venv `site-packages`, passed 12/12 tests, reran the ordinary entrypoint with
four result files byte-identical, and retained both earlier run outputs.

That autonomous delivery was **not** a complete pass. The first report
explained a positive mirror margin as magnetic-field compression suppressing
pressure growth, although the input only established B-value sampling, not a
spatial compression mechanism. More seriously, an external ordinary-entrypoint
probe changed S01 `p_perp` from 128000 to 129000 Pa against the unchanged
model note. The script exited successfully, wrote a 1000 Pa source-witness
deviation into JSON, and replaced the previous profile files; the downstream
formula checks stayed zero because they consumed the same wrong mapped value.
The first failure is preserved in
[`stage2-witness-failure-counterexample.tgz`](../../../build/verification/pointwise-profile-evolution-20260927/stage2-witness-failure-counterexample.tgz).

Reviewer feedback led Claude to enforce that witness before the asset call or
any output write, give a readable source-conflict error, distinguish changed
input deliveries, and remove the unsupported mechanism explanation. A second
external probe then changed only an editorial sentence in the model note from
Revision A to B. Because the new filename used the first eight characters of
the *CSV* digest, both versions wrote `profile_margins_549bb5ee.json`; B
silently replaced A. The overwritten A file had SHA-256
`af655122fd6759f3d61a99cdd42c4abe10e12245e930823f85f4a1de8da0deb4`;
the resulting B file had
`c4d7b7d8597853565e4c96228ad9c084892e1b135eb87a669098711a667994bc`.
The [second counterexample](../../../build/verification/pointwise-profile-evolution-20260927/stage3-note-collision-counterexample.tgz)
preserves that state. Two further, explicit review prompts produced a combined
CSV+note binding digest, then a full-digest filename and pre-write target
collision check. These are **review-assisted repairs**, not autonomous
first-attempt reliability evidence.

The [reviewed final archive](../../../build/verification/pointwise-profile-evolution-20260927/stage5-reviewed-final.tgz)
has SHA-256 `7f91f1031990a0fdae38bfd9acea5439a5cf1829103e5ab3f09c52425093290f`.
In a new external extraction its 18/18 project tests passed. The ordinary
unchanged-input rerun left all four archived result-file hashes unchanged.
Two note-only revisions produced distinct full-digest filenames, and the A
delivery was still byte-identical after B. Changing S01 `p_perp` to 129000 Pa
then gave the readable conflict and Python exit code 2 before any result
write; all eight existing result-file hashes remained unchanged. This checks
the user entrypoint, not just helper tests. The external venv inherited
system-site packages for NumPy/pytest, so this is a **source-free SciRel wheel**
check, not a fully hermetic dependency installation.

The scoped result is useful but narrow: two demand turns autonomously chose
different suitable assets, retained earlier outputs, and calculated a sampled
diagnostic; three reviewer interventions were needed for scientific wording
and repeat-run integrity. The case does not prove multi-graph composition or
general asset-selection reliability. The witness verifies only the note's
specific `p_perp(B)` law; it does not independently validate `p_parallel`, B,
or the scientific meaning of a revised note. The note's prose is bound by
digest but not parsed as an authoritative formula, so a material note change
requires renewed scientific interpretation. The first-turn
`run_diagnostics.py` still overwrites its own outputs if its input file later
changes; this evaluation only verified that the second-turn project left
those earlier files intact. No whole-device stability, expert approval,
trusted release or public v1 is claimed. The later dev49 exact-document
wording correction was not swapped into this frozen dev48 experiment.

Reviewed project changes relative to the stage-2 archive were confined to
`solver/run_profile_diagnostics.py`, `solver/README.md`,
`solver/tests/test_run_profile_diagnostics.py`, the new
`solver/tests/test_entrypoint_regressions.py`, and the two generated profile
result files. The SciRel scientific package, exact documents, catalog and
first-turn result files were not edited in this case. Evaluation records added
outside the project are this report, its manifest, the three reviewer prompts,
three review traces, two failure archives and the final reviewed archive.
The coordination handoff was updated separately.

Recheck the frozen evidence with
`python scripts/verify_outbound_evaluation_manifests.py` and
`python -m pytest tests/test_outbound_evaluation_manifests.py -q`. For the
reviewed project itself, extract `stage5-reviewed-final.tgz` outside the SciRel
source tree, install its included dev48 wheel, run
`python -m pytest -q`, then `python run_profile_diagnostics.py`. The external
replay in this evaluation used a venv with inherited NumPy/pytest and verified
that `scirel.__file__` resolved inside that venv's installed wheel package.
