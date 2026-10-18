# SciRel development lifecycle

This reference keeps daily SciRel work separate from candidate and public
release work. Read it when a task mentions wheels, documents, catalog counts,
platform matrices, version changes or release validation.

The current development baseline is Linux amd64 with CPython 3.14. Other
platforms remain `NOT_RUN` unless a named checkpoint or release claim exercises
them; a local macOS or Windows result must not be generalized to this baseline.

## Default: development

Use the current Git worktree as the development truth. New operators,
TaskGraphs, tests, benchmarks and documents may change the capability
denominator. Generate or update the development catalog only when a named
discovery handoff or another task actually needs that projection; do not rebuild
the full catalog after every source or document edit.

Treat the capability set as open during incubation. Counts such as
`267 documents = 235 operators + 32 TaskGraphs` describe one manifest at one
revision; they are not project-wide invariants and must never be copied into a
skill as a permanent gate. When a catalog, document selection or wheel is
actually requested, derive its members and counts from the same current
manifest. If several artifacts are produced together, bind all of them to one
exact Git revision and record the derived closure; if no artifact is requested,
leave the projections alone.

Run the smallest checks that support the claim: affected scientific and
reverse-dependency tests, public API/import and failure-contract checks, and
benchmarks when a performance claim is made. A documentation-only change needs
only the relevant schema, link, example or rendering check. Run an
installed-wheel smoke only when a named D3 or external consumer needs the
wheel.

Do not update `release/CURRENT.json`, platform receipts or a public version as
part of ordinary development. Do not treat a buildable wheel as a release
candidate.

If the project has not received an explicit first-public-release decision,
this mode is the only default. A legacy `0.1.0.devN` value, an old release note,
or a previous candidate in `release/CURRENT.json` does not create a new release
cadence. Do not increment `devN`, create a successor release note, or run
publication/platform gates because a task says to continue or to close the
current work. Record the Git commit and affected checks, then stop at the claim
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
