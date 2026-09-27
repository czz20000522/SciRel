# Unseen coil-grid probe sampling project (2026-09-28)

This synthetic, two-stage ordinary-user project used the frozen r81/dev58
development wheel and 169/169 catalog. Its exact evidence binding is in
[the evaluation manifest](manifests/2026-09-28-unseen-probe-sampling-dev58.json).
The solver received no SciRel source checkout. The opening workspace contained
only the first request, five source inputs, the wheel/catalog and three method
bodies. The examiner generated `expected.json` before the solver session. The
workspace boundary was by prompt and directory layout, not OS isolation.

## First stage

Claude Code 2.1.281 was launched with `--model fable` in a new session
`0a97ae81-7901-427e-bbed-97afdfdb67d4`; the trace labels the responding
model `GLM-5.3-Flash`, so the alias-to-model identity is not independently
established. The solver discovered the multi-coil TaskGraph and direct
dependencies through the visible catalog, built an ordinary `run.py` project,
and produced a vacuum-field table for each setting. It initially wrote a
textbook loop formula with a wrong factor of two, checked it against direct
Biot-Savart integration, corrected its formula, and retained that sequence in
the raw trace. It also repaired a draft table function and package-version
lookup within the first session.

The first delivered project passed 6 tests and its ordinary entrypoint exited
0 with 16 checks. The examiner verified 9 grid rows per setting against the
pre-run direct-wheel oracle and 3 independent on-axis loop-formula witnesses
per setting. The five original input hashes remained unchanged. The first
project was archived before opening the follow-up.

## Follow-up and rescues

The same session then received `probes.csv`, a deliberately reordered
`pressures.csv`, and the second request. Its autonomous result joined all 8
pressure rows by `(setting, probe_id)` and calculated the requested arithmetic
correctly, with 9 project tests passing. It interpreted "sampled field" as a
fresh vacuum-field calculation at the exact probe coordinates, including the
point outside the old grid. That is a meaningful alternative calculation, but
it differs from the pre-bound comparison based on componentwise bilinear
sampling of the delivered grid: 14 oracle comparisons failed (four interior
field/quantity triples and two outside-grid statuses). The autonomous archive,
raw trace and failing receipt were frozen before any clarification.

Rescue 1 stated the intended sampling rule and required the exact-coordinate
result to remain separately labelled. The solver added grid-sampled tables,
marked the outside point unavailable, kept the exact-coordinate evidence and
the old grid tables, and passed 10 tests. Independent comparison found zero
pre-run sampling-oracle mismatches; the five grid/difference files were
byte-identical to the first-stage archive. The auxiliary exact-coordinate CSV
still wrote all 8 `quantity_Pa` cells as `np.float64(...)` strings, which a
normal numeric CSV reader cannot parse. That failure was recorded against the
first rescue archive.

Rescue 2 reported only that concrete encoding defect. The solver wrote plain
decimal cells and added a parsing regression test. Independent verification
then found zero sampling-oracle mismatches and zero nonnumeric exact-evidence
cells. The final project passed 11 tests; the ordinary `run.py` exited 0 with
47 checks. Its 208 non-environment files were individually SHA-256 checked
against the final archive manifest. The archive excludes `venv/`; reinstall
the bundled wheel into a local environment before rerunning it. NumPy/SciPy
were inherited from the host, so the environment is not fully hermetic.

The session used Bash commands despite the opening prompt's `pwsh` 7+
instruction. That execution deviation remains visible in the raw traces.
Neither the formula self-correction nor the two follow-up rescues is counted
as an unassisted one-shot pass.

## Neutral-host handoff

`build/verification/unseen-probe-sampling-20260928/examiner/neutral-stage1.tgz`
contains the exact opening request, five inputs, dev58 wheel/catalog and three
method bodies (185 files). `neutral-stage2.tgz` contains only the later request
and two later CSVs (3 files). The corresponding `evaluation_prompt_stage1.txt`
and `evaluation_prompt_stage2.txt` fix the launch wording. The packages were
compared member-by-member with the final file manifest; neither contains
solver code, results, oracle, examiner materials or rescue prompts. They are
ready for a CodeFusion neutral-host comparison, which has not yet been run.

The result is a synthetic coil-produced vacuum-field preview and user-defined
pointwise arithmetic. It is not a plasma equilibrium, stability criterion,
device prediction, expert approval, public release, whole-catalog review or
CodeFusion product integration. All 169 catalog assets remain
`pending_unapproved`; the independent r81 review covered the multi-coil
contract clarification and three direct dependencies only.
