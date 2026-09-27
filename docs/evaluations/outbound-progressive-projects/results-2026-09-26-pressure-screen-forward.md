# Pressure-table screening: progressive project evaluation

A fresh Claude Code 2.1.281 session received a shuffled synthetic 3x3
`(B, psi)` pressure table and four requested positions. A second user turn
added three positions, one outside the tabulated domain, and a data-owner
note requesting sampled firehose and mirror margins. The solver's project
contained an unapproved SciRel 0.1.0.dev24 wheel, the complete 74/74
development catalog, and **three** usage skills. The evaluator had intended
to stage a fourth validation skill, but it was absent; do not attribute the
result to it. The exact user input, wheel/catalog/skills, four frozen project
stages, raw traces and feedback are bound by the [manifest](manifests/2026-09-26-pressure-screen-forward.json).
The CLI label was `claude-fable-5`, assistant events reported
`GLM-5.3-Flash`, and the underlying model was not independently confirmed.
There was no call or cost cap. Examiner files were outside the solver project,
without OS-level read isolation.

The first **autonomous** turn found `scirel.closures.tabulated-pressure`,
reconstructed the shuffled table by coordinates, invoked its 2-D branch,
and delivered four ordered positions with eight correct pressure values.
The second **autonomous** turn reopened catalog discovery for
`scirel.diagnostics.firehose-mirror-margins`, composed it with the pressure
interpolation, delivered six in-domain sampled results, and marked the seventh
point unsupported without extrapolation. It retained the first prediction
CSV byte-for-byte. A standard-library [raw-input examiner](../../../build/verification/pressure-screen-forward/examiner_raw_check.py)
independently recomputed all pressures, the B-sorted finite derivative,
per-point margins and aggregate flags. The sampled minimum firehose margin
was `-10665.50377176 Pa`, the sampled minimum mirror margin
`38524.29622824 Pa`; these are synthetic screening values, not a general
stability result.

The autonomous project was **not** a complete reusable delivery. Three
isolated ordinary-entrypoint probes on its frozen second stage found:

- Replacing the screening note with an explicit withdrawal of its scientific
  criterion still exited 0 and delivered the screen.
- Changing one valid query (`P-E` psi `0.30 -> 0.35`) overwrote the earlier
  screen CSV with no result/source archive.
- Perturbing the production pressure-column mapping made its raw-row witness
  correctly fail, but the first-stage entrypoint had already overwritten the
  last successful prediction CSV before exiting 1.

A first [reviewer message](../../../build/verification/pressure-screen-forward/review-feedback-1.txt)
led to project-local note-byte binding and validate-before-replace result
delivery. In separate extracted copies, all three original failures then
closed: changed note and wrong mapping exited 1 with five current and five
historical file hashes unchanged; a valid point change archived the old
screen and restoring the original input recovered the original three user
CSV hashes while retaining both histories. The reviewer found one remaining
provenance overclaim: the new contract included an invented review actor and
fixed `00:00` timestamp for a synthetic fixture. A [second message](../../../build/verification/pressure-screen-forward/review-feedback-2.txt)
removed those fields and labelled the pin as development-evaluation source
binding, not expert recognition. The final result is **two-review-assisted**.

The [final frozen project](../../../build/verification/pressure-screen-forward/stage4-second-review-final.tgz)
has SHA-256 `c0d65c545580f52d537e4937070b607f45d43ad9ca857a443ad30841e9e57aa5`.
Its separate source-free extraction imported the wheel from `site-packages`.
Both ordinary entrypoints returned `unchanged`, the three user CSVs kept their
frozen hashes, no-op reruns added no history, the independent raw-input
examiner passed, and the project suite passed 21/21. The [check record](../../../build/verification/pressure-screen-forward/independent-stage4-check.txt)
separates autonomous failures, reviewed probes and final replay.

The exact note pin proves which synthetic declaration was used, not its
physical truth or a human science approval. The multi-file output replacement
is not an atomic transaction, and reports refresh timestamps on no-op runs.
This case does not establish autonomous end-to-end reliability, a trusted or
public v1 asset, real-equilibrium physics, strict examiner isolation, or a
CodeFusion full-path comparison. The current `scirel-solving` guidance already
asked for raw-source witnesses and pre-write checks, so its observed
autonomous defects are primarily adherence failures, not a basis for another
global blocking script.
