# SciRel development lifecycle

This reference keeps daily SciRel work separate from candidate and public
release work. Read it when a task mentions wheels, documents, catalog counts,
platform matrices, version changes or release validation.

## Default: development

Use the current Git worktree as the development truth. New operators,
TaskGraphs, tests, benchmarks and documents may change the capability
denominator. Generate or update the development catalog from the current
documents when discovery needs it.

Run the smallest checks that support the claim: affected scientific and
reverse-dependency tests, public API/import and failure-contract checks, and
benchmarks when a performance claim is made. Run an installed-wheel smoke only
when a named D3 or external consumer needs the wheel.

Do not update `release/CURRENT.json`, platform receipts or a public version as
part of ordinary development. Do not treat a buildable wheel as a release
candidate.

## Stable integration checkpoint

Use this mode when a scientific family, API change or handoff reaches a stable
development boundary. Recompute the current document and catalog closure from
the working tree and report its dynamic counts. Check affected reverse
dependencies, package imports, dependency boundaries and the claim ceiling.

This checkpoint can produce a development report or installed development
wheel for a named consumer. It does not freeze a public release and does not
require the full platform matrix.

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

Git commits identify ordinary development state. Do not advance `devN` for each
function, document or benchmark change. Select a candidate or public version
at the release freeze. A first public release may normalize the version line
once after the capability and compatibility boundary are understood.

## Transition triggers

Move from development to an integration checkpoint when the task names a
stable batch, handoff, D3 consumer or bounded installed-package check. Move to
release freeze only when the task names a candidate cut, publication, release
approval or an equivalent owner decision. A source change, performance
improvement or new capability alone stays in development mode.

Critical correctness, security or data-integrity fixes may justify an expedited
freeze; record the reason and keep the development and frozen evidence
separate.
