# Spectral-pair progressive project: method-loaded Claude trial

This development evaluation used Claude Code `2.1.281` with an unapproved
SciRel `0.1.0.dev39` wheel (SHA-256 `be5a2a2b...1eef9b8`) and the complete
126/126 development catalog (`434249fe...86e3fca`). CLI model label was
`claude-fable-5`; assistant messages said `GLM-5.3-Flash`. The underlying model
identity was not independently confirmed. No call or token budget was set.
The [manifest](manifests/2026-09-27-spectral-pair.json) binds exact requests,
fixture members, two skill versions, four raw traces, first-pass archives,
review feedback and the reviewed archive.

The initial three requests were fixed before solving and exposed one at a
time: (1) a synthetic hydrogen profile and historical JH coefficient payload
to report local Balmer-alpha and Lyman-alpha photon rates; (2) a synthetic
Balmer-alpha emissivity sheet to infer ground-state neutral density and
recompute both rates; (3) a second profile with K4 calculable, K5 lacking
electron temperature and K6 lacking neutral density. The user did not know
asset names or want an experimental-validation claim. The prompt explicitly
requested the local project and solving skills. Unlike the earlier Balmer
case, the first raw trace shows actual reads of those skill bodies and the
asset-navigation skill. This tests method use, not autonomous skill selection.
Examiner and solver still shared a host filesystem; this was not a security-
isolated blind trial. The historical KN1DPy table has no independent atomic-
physics oracle and its strict D1 qualification is withdrawn.

## First three autonomous turns

Claude found and actually called the SciRel Balmer and Lyman emission
TaskGraphs, then re-searched for the Balmer ground-state inversion TaskGraph
when the second request changed the relation direction. Independent wheel
calls on every row matched the delivered photon rates and recovered
`n0 = [1.2e16, 1.8e16, 4.8e16] m^-3` from the synthetic observations. The
second profile delivered K4 at approximately `1.588e21` Balmer and
`1.017e23` Lyman photons `m^-3 s^-1`; K5/K6 remained unavailable with the
correct missing-input reasons. The three staged CSVs remained byte-identical
through turn 3. Separate source-free project extractions passed 8, 18 and
18 focused tests; ordinary stage-2 and stage-3 commands replayed their CSVs
byte-for-byte using the installed development wheel.

The first pass was nevertheless incomplete. The project's source-to-port
"witness" checked only the first parsed row, so its claimed rerun coverage
did not establish every row's mapping; the evaluator separately checked all
rows against direct SciRel calls. An isolated changed-profile call to the
stage-1 output path silently replaced its CSV (SHA-256 `dbb8e2cd...6ba65c6ba`
to `27462631...66a2764`). Stage 2 also silently accepted a duplicate K1 in
its baseline CSV when a valid last row concealed a conflicting first row,
and a changed observation could overwrite the stage-2 CSV
(`2d2bf8c1...16a735c5` to `176cfba2...1a601499b6`). These probes used
separate extractions; the frozen first-pass archives were not edited. The
stage-2 answer attributed slight non-proportionality to "real physics" even
though the evidence established only the saved composition's arithmetic
on an unapproved table. Later comments on coefficient magnitude were internal
comparisons, not independent physical validation.

## Fresh method holdout

The SciRel solving skill received three narrow, conditional clarifications:
ordinary reruns must not silently replace a prior output still needed for
comparison; joins claiming unique IDs must check ambiguity in every joined
input, including a prior baseline; and a saved composition's numerical
departure from proportionality is not itself evidence of physical mechanism.
The revised skill SHA-256 was `41652cdd...d40c2a0e87` (the initial three
turns used `d1739f71...b403705`). Structural skill validation and six
scientific-request documentation tests passed.

A fresh Claude session loaded the revised skill and received a reordered,
quoted observation CSV plus an external comparison CSV with two conflicting
K1 rows. No failure hint was in the request. The first autonomous holdout
correctly joined by `sample_id`, computed all three densities and both
forward rates with direct SciRel calls, marked only K1's **baseline
comparison** as `conflicted`, and retained the useful K1 inference and K2/K3
comparisons. Independent wheel calls reproduced all three rows. Its 22 tests
passed, and the three older result hashes stayed unchanged. This is a bounded
forward success for the duplicate-baseline decision, not proof that all joins
are reliable.

The same holdout **did not** autonomously protect output ownership. In a
separate extraction, changing K1's observation from 340.0 to 360.0 while
targeting the old holdout output path exited 0 and changed its SHA-256 from
`9616770b...aa4f2beca11` to `b4ec8147...72f642682912dd7`.
One symptom-level reviewer message led Claude to add an existing-output
guard to both ordinary report entrypoints, a separate K1=360 result and
tests. It also corrected wording that could imply physical validation. The
[reviewed archive](../../../build/verification/spectral-pair-20260927-holdout-reviewed.tgz)
has SHA-256 `e1c929345d0ad1deab0e5ec4b07968e6e191592fb9cb5070912ec2aff1fc8925`.
After independent extraction, 24 tests passed. Both report commands rejected
a changed-input write to an old output path with exit 1 and unchanged hashes;
the new-path K1=360 result replayed byte-for-byte. All four earlier CSVs
remained byte-identical. This final behavior is **one-review-assisted**, not
an autonomous output-ownership pass.

The reviewed commands conservatively reject even an unchanged rerun aimed
at an existing output unless the user explicitly chooses `--overwrite` or a
new path. That protects old results but is less ergonomic than a verified
no-write idempotent rerun. The witness still samples the first source row;
the evaluator's all-row numerical checks do not make the project's own
witness complete. No transactional multi-file output, external atomic
oracle, expert approval, trusted/public v1, or CodeFusion integration is
claimed. The evaluator reused host scientific dependencies with a pinned
installed wheel, and the Claude trace includes Bash tool calls despite the
project's `pwsh` guidance. These limitations remain separate from the
demonstrated useful multi-graph project work.
