# SciRel current handoff

## 2026-10-26 skill lifecycle and residue cleanup

The development package now has one executable artifact closeout reference at
`skills/development/references/artifact-lifecycle-closeout.md`. The cleanup
route uses it together with `catalog/RECORDS.md`, separates process records,
current results, temporary runtime products and frozen deliveries, and
requires exact disposition plus filesystem/Git/consumer readback. Stale skill
links were rebound to the current contracts and record policy; SciRel's
development route no longer asks for AOCI maintenance. The tracked policy
change is `fe87dddf` (`DOC: close artifact lifecycle and cleanup loop`).

The cleanup pass retired 42 exact targets: the stale 247-asset `.runtime`
documentation snapshot, superseded 2026-10-22 documentation/review snapshots,
synthetic query-maintenance output, package metadata scratch, an empty
maintenance directory, repository `.DS_Store` files and project
`__pycache__` directories. The safe-delete plan covered 4,788 files and
143,241,495 logical bytes; its apply receipt is outside the repository. The
canonical development `.venv` was retained. The remaining `dist` roots are
intentional: `acceptance/` (project acceptance), `reference-truth/` (external
oracle used by acceptance evidence), `famou-pure-20261022-20afa0cc/` (private
immutable integration delivery), and `contract-semantic-audit-20261023/`
(open remediation evidence). These retained roots are historical or frozen,
not the current source baseline.

The current source identity is always the live output of `git rev-parse HEAD`
and `git status --porcelain`; this handoff commit is the new clean baseline.
The public catalog is 249 assets, with one human-review hold
`scirel.inference.direct-anisotropic-inversion`. Docs tests and asset schema
validation are the current scoped checks; full suite, wheel, platform,
release, rights and human-scientific acceptance remain `NOT_RUN` unless a
future task explicitly opens those gates.

## 2026-10-25 modal numerics integration batch

Integrated the admitted reference-cell orthonormal modal basis and modal
projection capabilities under `scirel.numerics`. The public catalog is now 249
assets (the existing human-review hold remains separate); contracts, direct
tests, bilingual API reader records, handbook navigation, package exports,
license notice and mechanical verdict bindings are synchronized. The bounded
checks passed: 122 direct numerical tests, 210 architecture tests, 33 core docs
tests, 13 English-site tests and 168 delivery tests (2 skipped); the standalone
documentation snapshot build and asset validation also passed. No wheel,
`dist/`, frozen case or deployment artifact was changed. The tooling suite has
one pre-existing unrelated failure in the multi-coil-vacuum-field complex
mapping binding check; it is retained as `NOT_RUN` for this batch's scope.

Read `AGENTS.md`, `RULES.md`, `catalog/README.md`, and
`tools/docs/manual/README.md` before changing this checkout. The unique checkout
is `/Users/tomczz/Projects/SciReL`; use `git rev-parse HEAD` and `git status` for
current identity. Historical checkpoints and resolved work remain in Git.

## Current baseline and next outbound entry

This batch started from a clean `d9ca1001`; the 2026-10-26 baseline recheck was
`b49ab1ac3bfb4710349f490af1009485543a17cc` with a clean worktree. Read the
current identity live with `git rev-parse HEAD` and `git status` before acting.
The bounded maintenance gate is canonical in
[`RULES.md` section 12](RULES.md#12-baseline-and-outbound-batch-gate), and the
outbound worker entry is `skills/development/usage/scirel-solving/SKILL.md`.
This batch records the gate only; it does not rebuild a wheel, alter a frozen
case/package, or start a new scientific run.

The first candidate workflow for the next authorized user task is **axisymmetric
vacuum coil-field evaluation**: discover public field/geometry contracts, select
the complete contract, state any grid aggregation as explicit glue, execute in a
task-owned environment, read back field/profile artifacts, then independently
check symmetry/limit/shape constraints. Its status is `source-backed development
execution COMPLETE` here; `wheel-Famou acceptance NOT_RUN`. The completed task
used 84 already-expanded circular-filament inputs; the rectangular
`coils-to-filament` requirement is `NOT_READY` for this input. Scientific
correctness, rights, and human acceptance remain separate from structural
admission.

## Current public boundary

- Public capabilities: **249**; current contracts are `catalog/examples/`.
- Human-review hold: **1**, `scirel.inference.direct-anisotropic-inversion`.
  Its implementation and contract remain in the review tree and are excluded
  from the installed package, discovery index, API pages and runnable tutorials.
  Restore/bind the exact admitted direct graph artifact and rerun direct
  composition/physical closure before reconsidering the hold.
- The diagnostics/inference authored chapter references that unavailable API.
  Both language sites therefore show an explicit subset placeholder for this
  chapter. Do not count it as delivered runnable tutorial coverage.
- Source-based acceptance and scientific evidence remain in the existing
  catalog review records; do not infer scientific approval from test counts.

## Private consumer delivery

The formal consumer protocol and maintenance sequence are
`tools/docs/PURE_CONSUMPTION.md`. One standard-library query/Consumer core serves
four read-only tools (`describe`, `browse`, `search`, `get`) through the official MCP SDK over stdio and
Streamable HTTP. Computation stays in user Python with the installed wheel.
SDK dependencies are separately locked; scientific dependencies remain NumPy,
SciPy and mpmath on Python `>=3.14,<3.15`.

At an explicitly authorized integration checkpoint,
`scripts/build_pure_delivery.py --wheel PATH --output NEW_ROOT` exports one Agent
runtime from a clean source revision and exact wheel. It derives the lightweight
index directly from public contracts and bound Chinese sidecars, checks the
public set and source/wheel bytes, and binds the actual runtime inputs and
internal skill reference closure. It does not need a documentation snapshot,
Sphinx or HTML generation. Human API/tutorial/site generation remains the
independent `scripts/scirel_docs.py build` pipeline, with its documentation
bindings, examples, links and resources. Never overwrite an existing immutable
bundle.

The only outbound skill is the ignored local
`skills/development/usage/scirel-solving/SKILL.md`. The internal entry reads its
method notes as needed; the exporter copies the reachable internal references
and helpers unchanged under `skills/scirel-solving/`. Cross-skill references are
rejected. All used bytes are bound because Git SHA alone does not cover ignored
local skills. The exported `tools/query.py` is the real standard-library CLI;
MCP is optional and uses the same dispatch. `runtime.json` contains only generated
runtime identity, pins and member integrity. `get` returns one complete original
JSON contract with its byte digest and path; it has no language selector or
embedded Markdown, and the browse/search card budget does not truncate it.
The runtime contains no API/tutorial Markdown, tutorial index or human site
assets. Human reading is optional and uses only separately supplied actual
site/version/path bindings; no URL or “latest” wheel match is inferred.
Build checks remain internal; no
delivery receipts or separate protocol/quickstart are required at runtime.
Daily source discovery uses `scripts/scirel_docs.py query --source-root .`; it
needs no wheel or pure build, shares the delivery query core and binds current
public inputs rather than inventing an installed-wheel receipt.
The current structured-runtime batch record holds scope, candidate, verification
and cleanup:
https://app.notion.com/p/4011c0206a8781aeb2ccf15955414772

MCP retrieval does not establish physical applicability or composition. Keep
snapshot/wheel pins and continuation identity. Unknown ports/units/relations
remain unknown. Do not call a held implementation as glue. Disclose and verify
any scientific glue using only public inputs.

## Verification and recovery

Select tests with `scripts/test_scope.py --changed PATH...`, then run local and
affected domains/layers. No default wheel/release/full-suite work outside an
explicit checkpoint. Exact-wheel inspection is
`scripts/check_wheel_exposure.py --wheel PATH --source-root src`; it is static
and does not replace installed import/call verification.

Private technical integration is not public release, legal acceptance or
Famou/Linux validation. Keep `NOT_RUN`/`NOT_DEPLOYED` for unexecuted targets.
Authored tutorial dependency hashes are traceability; natural-language science
review is not inferred from generation. Existing execution-bound standalone
chapters and other hand-authored RST have distinct evidence scopes.

Record locations, retirement and actual task cleanup follow the single policy
`catalog/RECORDS.md`. Keep this entry current; history remains in Git and Notion.
