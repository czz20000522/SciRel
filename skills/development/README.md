# SciRel development skills

This directory routes SciRel library development, D2 integration, D3 project
delivery and development-only claim validation. It does not grant human
endorsement, redistribution rights or release authority.

The [development lifecycle](references/development-lifecycle.md) is the single
source for modes, claim selection, evidence reuse, stopping, artifacts and
version decisions. Read it when the task changes code, tests, documents,
dependencies, packaging or validation. Load only the sub-skill reference that
matches the selected route; do not preload every route or copy the lifecycle
into another skill.

Choose the route from the requested work:

- **development**: the default for source, API, tests, documentation,
  benchmarks, CI and packaging changes. Use the direct product path unless the
  task supplies an exact D1 packet.
- **integration checkpoint**: an explicit request for a consumer, handoff or
  installed development artifact while the project is still in development.
  It does not create a release cadence.
- **release freeze**: an explicit candidate or public-release decision that
  freezes one Git revision and runs the declared release gates. Publication,
  rights and human endorsement remain separate decisions after the freeze.

## SciPy structural reference

Keep one Git source tree for `src/scirel/`, direct tests, public documents,
build/test tooling and `pyproject.toml`. Use Git history for older source and
wording instead of copying wheel, document or catalog trees into versioned
directories. Keep runtime, optional and development dependencies distinct.

Adopt SciPy's useful structure where it fits SciRel: each scientific domain has
explicit exports, direct regression tests and callable documentation; the root
namespace stays small; heavy or optional dependencies remain at their actual
call boundary. SciPy is a structural example, not authority for SciRel's
Python bounds, dependency pins, classifiers or native distribution.

Capability counts are properties of the current manifest and Git revision.
They may grow or shrink during incubation. Exact documents and catalogs are
derived projections for a named handoff, checkpoint, review preparation or
release; ordinary development can use docstrings, comments and direct tests.
When an exact-document projection is requested, check document-to-export and
function-export-to-document bindings together. Classes and exception exports
remain covered by the public-surface and asset-document tests.

Skill and `AGENTS.md` maintenance follows the dedicated decision point in the
[development lifecycle](references/development-lifecycle.md). Candidate code
review remains a separate read-only claim until a concrete product scope is
selected.

## Correctness ownership

SciRel owns the implementation, input/output contract, numerical result,
failure behavior and direct regression evidence for every public Operator and
TaskGraph. Agent code discovers, selects, composes and adapts those validated
capabilities; it does not reimplement domain mathematics or use a successful
composition as proof of capability correctness.

For import, dependency or performance changes, preserve the public and failure
contracts and measure only the claim supported by the affected checks. Add a
platform-specific wheel or native boundary only after measured ABI/runtime
evidence shows that the common distribution cannot cover the capability.

Routing shortcut:

- a task that consumes an exact D1 packet uses the D2 integration sub-skills;
- a real user scientific request uses the usage skills and an already selected
  capability;
- a named candidate cut, publication or release approval uses `release_freeze`.

An ordinary documentation edit stays in development. Mentioning a wheel,
document or catalog does not by itself trigger a release check.
