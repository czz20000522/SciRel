# SciRel development lifecycle

This reference keeps daily SciRel work separate from candidate and public
release work. Choose exactly one lifecycle mode before editing or running a
claim-matched check:

- `development` (default): optimize the current source tree and run the
  smallest checks for the named claim. Do not build a wheel, refresh release
  projections, run a platform matrix or advance a version.
- `integration_checkpoint`: an explicit consumer, handoff or owner-requested
  artifact needs a scoped install/closure check. It is still development work;
  it does not freeze a release or advance `devN`.
- `release_freeze`: the owner explicitly cuts a candidate or public release.
  Freeze one revision, derive all projections from it, build the artifacts and
  run the declared release gates.

Read this reference when producing or binding artifacts, choosing gates, or
changing version/release state. A simple read-only status lookup can use the
routing shortcut directly.

The current development baseline is Linux amd64 with CPython 3.14. Other
platforms remain `NOT_RUN` unless a named checkpoint, explicit platform claim,
or release claim exercises them; a local macOS or Windows result must not be
generalized to this baseline.

## Default: development

Use the current Git worktree as the development truth. New operators,
TaskGraphs, tests, benchmarks and documents may change the capability
denominator. Generate or update the development catalog only when a named
discovery handoff or another task actually needs that projection; do not rebuild
the full catalog after every source or document edit.

Before the first public release, unqualified work remains in `development`.
Ordinary optimization does not produce release projections or a full
acceptance run. A request to continue, finish, review or verify is not a mode
change; select a named checkpoint or `release_freeze` only when that output is
actually needed.

Treat `integration_checkpoint` as an explicit artifact request inside the
development route, not as a default stage or a release cadence. Use this
impact rule for the daily loop:

- a local implementation or import change runs its direct and affected tests;
- a shared API, dependency, or TaskGraph boundary adds its known reverse
  dependencies and a focused contract check;
- a packaging, platform, or native boundary adds a measured closure/install
  check;
- only a named `integration_checkpoint` whose consumer or handoff needs an
  artifact, or `release_freeze`, creates a wheel/document/catalog closure; only
  `release_freeze` runs the complete release matrix.

In `development`, “验收” means the smallest check that decides the named
claim. Release acceptance means the frozen wheel/document/catalog and platform
closure produced by `release_freeze`; do not use that term for every local
optimization check.

Do not repeat a larger gate merely because a smaller check passed, and do not
start a release projection to make a development count look current.

### Work triage and evidence reuse

For a non-trivial task that edits files or executes validation, identify the
lifecycle mode, the primary claim (and directly related subclaims), the owned
paths and the output that claim needs before editing or rerunning a check.
Record the pre-existing worktree state and keep files outside the owned scope
out of the change set. This is especially important when the tree already
contains an unfinished candidate or a user's local changes. A read-only
question or simple status lookup does not need this record.

Reuse a previous result when the source revision, dependency/runtime identity,
checker, target scope and claim are unchanged. Rerun it only after one of those
inputs changes, the evidence is known to be stale, repeatability itself is the
claim, or the owner explicitly asks for a fresh observation. A status request
or a continuation with no new change does not by itself justify replaying the
same validation or rebuilding a wheel.

For a continuation of the same active claim, reuse the previous triage binding
when the Git base/head, worktree ownership/status, runtime/dependency identity,
checker, target scope, primary claim and stop condition are unchanged. Perform
only a lightweight identity check; do not repeat full triage, selector
discovery or validation. Rebind when any binding changes, evidence becomes
stale, or the owner asks for a fresh observation.

Ordinary development may update an existing work-management record only when a
new decision, blocker, durable result or next action was produced. Do not create
per-iteration release records or repeat an unchanged status merely because a
long-running task continued.

Use one minimal pass for ordinary work: select the mode and claim, run the
initial claim-matched check set (the affected selector for code, or the relevant
document/schema/link check for documentation), inspect the result and stop at
the supported claim ceiling. Add a wider test only when the first result
changes the affected scope or exposes a concrete blocker. Add a wheel,
document/catalog projection or platform route only when the named checkpoint or
`release_freeze` requires it; generic requests to continue, review, verify or
refresh do not create that route. A work-management closeout remains
appropriate when this task produced a durable decision, blocker or next action
under the repository's closeout convention. Tool availability and elapsed time
are not reasons to start a companion route.

### Skill and `AGENTS.md` maintenance

When a task changes this development package or `AGENTS.md`, treat maintenance
as one bounded claim: identify the observed routing failure or repeated cost,
change its owning decision point, and run the lightweight skill contract and
structure checks. Close that claim before promoting an existing candidate diff
into a product claim. Candidate code stays read-only during this review unless
the task also names a concrete product scope. Skill maintenance alone does not
build a wheel, refresh release projections, or start a full acceptance route;
run one applicable AOCI maintenance pass after the final stable managed-file
batch.

### Coordination and stopping

For each active change set, assign one coordination owner and one editing owner
to each mutable source path. Parallel agents may inspect independent paths, run
read-only checks or measure separate baselines, but they must not edit the same
source/test/document set or run maintenance against it concurrently. Freeze the
source batch before AOCI maintenance, catalog generation, manifest/document
closure or another source-bound projection; a later edit invalidates that
result and requires one new final maintenance pass.

A long-running goal is a queue of possible claims, not an execution scheduler.
It does not widen the current task. At each continuation,
reconfirm the mode, primary claim, owned scope and stop condition from the
previous binding; perform only the lightweight identity check above and rebind
only when a binding changes. “Continue” or “keep going” resumes that scope; it
does not authorize a wheel build, version
change, platform matrix, catalog regeneration or a new optimization search.
When the claim reaches `passed`, `failed`, `blocked` or `NOT_RUN` and no new
scope or blocker is present, stop with the reviewable diff and evidence already
obtained. A new claim requires a new owner request or a later task turn.

### Change-set loop

Treat one coherent change as the working unit. Before editing, inspect the
current Git base, worktree status and affected selector; for a behavior or
performance change, capture a focused baseline when it will help distinguish a
regression from an existing failure. Work in an isolated branch or worktree
when the change can overlap another route, and keep unrelated files out of the
change set.

Keep the implementation and its evidence together. A public API or behavior
change updates the callable docstring and the focused regression/contract test
in the same change set; add the relevant user-facing page or example when the
change is large enough to need one. A performance claim adds or updates a
comparable benchmark and records the before/after result. Formal exact
documents and the catalog remain checkpoint/release projections, so this loop
does not require rebuilding them for every edit.

When the current batch already has exact asset documents, or a named handoff,
checkpoint, review preparation or release requires them, keep the public
surface and documents aligned in both directions. The document-to-export check
catches stale bindings; the function-export-to-document census catches public
functions with no discoverable scientific contract. Class and exception
exports remain covered by the public-surface and asset-document tests. A new
function may stay on its callable docstring and direct regression while the
batch remains ordinary development; the missing exact document becomes a
bounded documentation claim only when an exact-document projection is needed.

When a task reveals several related public surfaces in one domain or affected
closure, stabilize them as one batch before the final selector run, commit and
AOCI maintenance. A function or document by itself is not a required batch
boundary. Keep exploratory edits in the working tree; split the batch only for
different ownership, risk, dependency boundaries or stop conditions. Do not
repeat the same setup, selector discovery, work-management update or
source-bound maintenance for each sibling.

The evidence level follows the claim: a public API change needs import,
failure-contract and focused behavior checks plus its docstring/user-facing
explanation; an internal performance change whose public contract is unchanged
needs the affected correctness checks and a comparable before/after benchmark.
The claim owner chooses the smallest reproducible benchmark that exercises the
changed path. A repository-wide benchmark runner is not required: the owner
may provide a minimal command or script for the changed path. If no such
command or runtime can run, mark only the performance subclaim `NOT_RUN`,
retain the affected correctness result, and stop at that evidence ceiling; do
not turn the missing benchmark into a release or platform route.
Neither claim requires a wheel or catalog during ordinary development.

Routine docstring and public-document edits stay in `development`. They do not
create exact asset documents or rebuild the catalog; those projections are
created only when a named handoff, integration checkpoint, review preparation
or release freeze requires them. A prose-only document with no schema, example
or rendered-output contract can close with the scoped diff/link review and no
scientific test selection; do not invent a wider gate just because the file is
under `docs/`.

After editing, run the affected selector once. Add known reverse dependencies
only when the selector shows a shared boundary or the claim names them; add a
narrow API/import/failure check only when the selector does not cover it or the
claim requires it. Unknown ownership fails closed to a wider test layer.
Finish with a reviewable diff and the recorded checks; commit the coherent
change set when the requested handoff or repository workflow calls for it. Do
not stage an unrelated work-in-progress file merely to make the tree look
complete.

Put a new regression in the canonical direct test path that the affected
selector recognizes, or update the selector mapping in the same change set. A
test file that the daily selector cannot reach cannot support an automatic
affected-test conclusion; a manually run, scope-matched test may still support
the claim when its command and coverage are reported.

Several compatible local fixes may share one change set and one validation
round. A function-level edit, a new capability or a changed count is not a
version boundary; Git history records the intermediate state until a named
checkpoint or release freeze is requested.

Treat the capability set as open during incubation. Any operator, TaskGraph,
document or catalog count describes one manifest at one revision; it is not a
project-wide invariant and must never become a permanent skill gate. When
producing or binding a catalog, document selection or wheel, derive its
members and counts from the same current manifest. If several artifacts are
produced together, bind all of them to one exact Git revision and record the
derived closure; if no artifact is requested, leave the projections alone.

Run the smallest checks that support the claim: the affected selector first,
then the relevant reverse dependencies or public API/import/failure checks only
when the selector or claim requires them, and benchmarks when a performance
claim is made. A documentation-only change needs only the relevant schema,
link, example or rendering check. Run an installed-wheel smoke only when a
named D3 or external consumer needs the wheel, or an integration checkpoint
explicitly requests it.

Do not update `release/CURRENT.json`, platform receipts or a public version as
part of ordinary development. A previous release tuple, wheel, document
selection or catalog may therefore be stale relative to `HEAD`; record that
state and leave the projection untouched. Do not treat a buildable wheel or a
successful alignment check against an older tuple as a release candidate.

If the project has not received an explicit first-public-release decision,
this mode is the only default. A legacy `0.1.0.devN` value, an old release note,
or a previous candidate in `release/CURRENT.json` does not create a new release
cadence. Do not increment `devN`, create a successor release note, or run
publication/platform gates because a task says to continue or to close the
current work. Record the Git state and affected checks, then stop at the claim
supported by that evidence.

## Named integration checkpoint

Use this mode only when the task names a consumer, handoff, or owner-requested
checkpoint. A stable batch by itself is not an automatic transition. Report
the current dynamic scope and recompute document/catalog closure only when the
consumer or handoff needs those artifacts. Check affected reverse
dependencies, package imports, dependency boundaries and the claim ceiling.

This checkpoint can produce a development report or installed development
wheel for the named consumer. It does not freeze a public release, advance
`devN`, update `release/CURRENT.json`, or require the full platform matrix.
Source-only smoke may use a dirty working tree. An installable wheel,
document/catalog selection or receipt must come from one exact clean revision;
an explicitly requested dirty artifact is labelled `source_dirty`/`unbound` and
cannot establish a same-revision closure. When a checkpoint emits multiple
artifacts, every artifact and manifest must carry that same exact
`source_revision`; a clean artifact from another revision is not a valid
checkpoint tuple.

## Development output budget

Keep ordinary output proportional to the change:

- source, API, test or packaging change: changed scope, checks actually run,
  and exact failures or unknowns;
- performance change: the affected correctness checks plus a comparable
  benchmark when a performance claim is made;
- document-only change: the relevant document/schema/link/example check;
- named checkpoint: the current manifest, dynamic counts and installed smoke
  only when requested;
- release freeze: complete manifest, hashes, receipts and platform gates.

Do not create a release receipt, platform matrix, full closure report, or
Notion release record for ordinary development merely because the repository
contains those tools.

If a change concerns imports, optional dependencies or native files, add only
the narrow evidence needed for that claim: an import guard or affected import
test for import cost, a dependency-boundary check for packaging, and a
reachability audit for native resources. Static non-reachability is a deletion
candidate, not deletion evidence; retain a resource until dynamic dispatch,
external entry points and ownership have been checked.

For capability-level dependency work, use the fresh-process capability runtime
probe when the question is which public callable or caller-owned probe loads
which external roots. Treat import-only output as import-closure evidence and
probe-run output as runtime dependency evidence; neither establishes numerical
correctness or justifies changing core/optional dependencies by itself.

## Build and test shape

Keep the Git tree, build/install directories, rendered documentation,
benchmarks and receipts as separate layers. If an installed development wheel
is needed, build it into a task-local output directory for the exact source
revision; do not reuse a release artifact or let a cache define the version.
Keep different platform or toolchain configurations in separate build roots.

Use the smallest useful test layer first: affected tests, then the relevant
module/file or consumer smoke, and only `release_freeze` gates for the full
platform/scientific matrix. Unknown change ownership fails closed to the wider
test layer; an ordinary known-scope change does not expand to full validation.

For performance work, measure the affected path before and after the change and
keep correctness checks in the same scope. Delayed imports are appropriate when
they remove an optional or heavy dependency from an unrelated path; they must
preserve the public import contract and the failure behavior when that optional
capability is actually used.

## Explicit release freeze

Enter this mode only when the owner explicitly decides to cut a candidate or
public release. Then:

1. freeze one exact Git revision and reject unbound working-tree changes;
2. generate the manifest and exact documents/catalog from that revision;
3. derive the operator, TaskGraph and document counts from that manifest;
4. build the wheel and documentation artifacts;
5. run only the platform and scientific gates required by the declared claim;
6. bind receipts and update the current release tuple once;
7. preserve the resulting artifacts and receipts as immutable evidence.

The counts are properties of this frozen revision. A later development change
creates a new development manifest and may change all counts; it does not
rewrite the frozen tuple.

## Version rule

Git commits identify ordinary development state. Before the first public
release, do not advance or normalize the package version at all; existing
`devN` labels are historical working metadata. Select the initial public
`major.minor` line and any maintenance suffix once, at the first
`release_freeze`, after the capability and compatibility boundary are
understood. Later compatible fixes can be batched on that line; a broad
capability or compatibility boundary can start the next line. A commit, document
edit, benchmark, count change or buildable wheel never advances a version by
itself.

## Transition triggers

Move from development to an integration checkpoint only when the task names a
consumer, handoff, or owner-requested checkpoint. Move to release freeze only
when the task names a candidate cut, publication, release approval or an
equivalent owner decision. Words such as “continue”, “finish”, “review”,
“verify” and “close” are progress instructions, not lifecycle triggers. A
source change, performance improvement, new capability or document edit alone
stays in development mode.

Critical correctness, security or data-integrity fixes may justify an expedited
freeze only when an external or public consumer depends on an existing frozen
candidate and needs a correction or withdrawal. An internal development tree
without such a consumer remains in `development`, with impact-matched checks;
record the reason and keep development and frozen evidence separate.
