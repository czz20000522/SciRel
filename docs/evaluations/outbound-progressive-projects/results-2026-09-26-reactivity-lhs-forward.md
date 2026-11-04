# Reactivity/LHS progressive project: forward evaluation

A fresh Claude Code 2.1.281 session received three out-of-order CSVs describing
six synthetic temperature/reaction cases. The first user turn requested a
re-runnable Maxwellian-averaged reactivity table and comparison plot. A later
turn added seven seeded, equal-width-stratified candidate temperatures and
both D-T and D+D -> He3+n rates at each point, while retaining the first
delivery. Exact input, skill, wheel/catalog, four archives, four raw traces and
reviewer feedback are bound by the [manifest](manifests/2026-09-26-reactivity-lhs-forward.json).
The CLI model label was `claude-fable-5`, assistant messages reported
`GLM-5.3-Flash`, and the underlying model was not independently confirmed.
There was no call or cost cap. Examiner files were outside the solver's project
directory, but not protected by an OS-level isolation boundary.

The first **autonomous** archive joined the source tables by identifier,
converted eV to keV, selected the SciRel Bosch-Hale asset and produced six
correct rates. A raw-CSV examiner independently checked the joins and all six
values. Its advertised source-to-port witness was incomplete: changing the
`ddn` row's reactants from D+D to T+T while leaving its products as He3+n let
the ordinary entrypoint pass and still call the D+D branch. The second
**autonomous** archive called SciRel's Latin-hypercube sampler and reactivity
asset, produced seven correct temperatures and 14 correct rates, and retained
the first output files. But after changing one source temperature from 8000 to
9000 eV and running only the second entrypoint, its new batch manifest falsely
assigned the unchanged first-stage files to the new input batch. These are
real first-delivery failures, not later-discovered successes.

The first explicit reviewer message described the contradictory reaction
identity, stale-batch attribution and positive-infinity check. The resulting
third archive rejected the contradictory reaction and used `math.isfinite`,
but an independent replay found that a changed-input run overwrote archived
files from the frozen first delivery. Invalid input also moved the last
successful files before raising. A **second** reviewer message prompted the
fourth archive: it validates and checks before replacing outputs, separates
current versus old input batches, and puts byte-distinct same-batch historical
sets under `again-N/` when a later input change archives them. These are
review-assisted repairs, not autonomous model performance.

The [final two-review-assisted archive](../../../build/verification/reactivity-lhs-forward/stage4-reviewed-final.tgz)
has SHA-256 `abe55f030788893008590c28434750de7dd832064a6bddd19b3802e84d42a3a2`.
In separate extractions, the installed development wheel was imported from
`site-packages`, not the SciRel source tree. The project suite passed 33/33.
The independent raw-input checker verified all six case rows; a second checker
reproduced the seven sampler strata and 14 reaction rates from the raw inputs.
Both ordinary entrypoints returned 0 on an unchanged rerun, with seven root
outputs byte-identical and no new archive. The six original CSV/PNG/check-log
members in history matched the two frozen autonomous archives byte-for-byte.
After the 8000-to-9000 eV source change, both ordinary stages and both raw
checkers passed for batch `438fff22fd3a`, without altering any of 16 earlier
archive files. The contradictory T+T input made the first entrypoint return 1
while all seven last-success root files stayed byte-identical. Exact replay
details are in the [independent check](../../../build/verification/reactivity-lhs-forward/independent-stage4-check.txt).

This establishes a bounded, reviewer-assisted reusable synthetic project
using two SciRel assets. It does **not** establish autonomous complete delivery,
external physical validation of the fit, expert approval, trusted/public v1,
CodeFusion integration or strict examiner isolation. Batch identity covers
input bytes, not code or result versions; same-input code changes, partial
write/crash recovery and missing historical provenance were not fully tested.
The result is a method-adherence and project-output ownership case, not a
reason to add a global blocking script for one observed defect.
