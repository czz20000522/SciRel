# r75 evidence corrections addendum (post-freeze, original bytes preserved)

Frozen snapshot: `build/verification/review-2026-09-27-r75-nbi-source-geometry-v1`
(commit `6f57c69…`, freeze record `783e4ee`). A read-only audit of
`build/test-evidence-r75.md` found three evidence wording errors. The
science, wheel, catalog and all measured receipts are unchanged; only the
wording below is corrected. The original evidence bytes and the frozen
snapshot (including the dossier copy bound by SHA-256 in the manifest) are
preserved unmodified; this addendum is the authoritative correction. The
same `+152/−151` sentence also exists in the dossier
(`docs/evaluations/review-version-2026-09-27-r75.md`, verification section),
whose bytes are frozen-bound — it is corrected here rather than by editing
frozen-bound files, which would force a refreeze without any content change
beyond this wording.

## Correction 1 — finding count

`build/test-evidence-r75.md` says "Three independent pre-freeze review
findings were resolved before the freeze" but lists four numbered items.
Correct statement: **four** independent pre-freeze review findings were
resolved (1 unit-ray norm overflow, 2 NumPy-bool source shape, 3 beam-grid
behind-origin pair semantics, 4 graph candidate-ray wording). The
resolutions themselves are unchanged.

## Correction 2 — installed-vs-r74 arithmetic

The evidence (and the dossier's verification section) describes the
installed delta versus r74 as "+152 passed / −151 skipped". Correct
arithmetic:

- r74 installed receipt: 1398 passed, 195 skipped (total 1593).
- r75 installed receipt: 1573 passed, 44 skipped (total 1617).
- Passed delta: 1573 − 1398 = **+175**, comprising **+24 new tests**
  (1550 → 1574 in source mode) and **151 tests that skipped in r74's
  installed run** (replay roots unset) and **ran and passed here** because
  the KN1DPy replay root was active.
- Skipped delta: 44 − 195 = **−151**, the same 151 converted tests.

The qualitative conclusion stands unchanged: the delta is a replay-root
configuration difference plus the new test population, not a test-set
regression. (The earlier "+152" came from comparing source-mode totals,
1550 − 1398, which conflates the new tests with the converted skips.)

## Correction 3 — catalog preservation claim

The evidence says "Prior catalog builds are preserved and unreferenced by
this freeze". That is not supported for this round: `build/catalog/r75` was
rebuilt **in place at the same path** after the review-correction commits
(earlier scratch build at that path, root digest `sha256:00e9e905…`,
superseded and not separately retained; the pre-review wheel
`9c2479b1…` was likewise discarded on rebuild, as the evidence already
states). Scratch/development builds may be superseded; only frozen
round material is preserved. What remains preserved and unreferenced by
this freeze: the r74 and earlier **frozen** snapshots under
`build/verification/`, including their bound catalog copies, and prior
rounds' wheel/catalog directories (`build/wheel-r74`, `build/catalog/r74`,
etc.).

## Status

No refreeze is required: the science code, exact documents, wheel
(`95515acb…`), catalog (`fa189331…`) and all other receipts are identical
to the frozen snapshot. `pending_unapproved` stands; no expert approval,
trusted promotion or public release is claimed.
