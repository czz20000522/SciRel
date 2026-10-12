---
name: scientific-project-implementation
description: Use when turning a scientific-computing request into working files in the current user project, extending an existing scientific codebase, or integrating scientific capabilities. Does not extract, publish, or review assets, or define validation methodology.
---

# Scientific Project Implementation

Deliver the working project, not a prose-only code sample. Work in the current persistent user workspace,
follow its language and conventions, create or update actual files, run the relevant entrypoint and tests,
and read the resulting files and output before reporting success.

This project-level skill covers delivery inside the user's project. The application/project owner retains workspace
and request truth. The method may consume an authorized published capability, but it does not create or mutate plugin
candidate, review, catalog, or release state. A runnable user project is not automatically a reusable or published
scientific capability.

For evaluator-owned disposable copies in an outbound trial, put simulated user projects, negative probes and
independent reruns in the run's declared private persistent result area or a designated temporary area when appropriate. Reuse the pinned wheel, catalog and environment across copies when their runtime
contract permits; freeze trial states and traces through the existing case archive and manifest. This does not move
or replace a user's persistent project workspace.

## D3 stage boundary

Use the portable [stage boundaries](../../extraction/scientific-computation-asset-extraction/references/stage_boundary_contract.md) and the supplied project policy for D1/D2/D3 responsibilities.
Consume an exact development or trusted wheel/catalog with its trust status explicit; development use does not
wait for final human approval. Keep upstream deliveries read-only. Put task-specific assumptions, source references,
repairs and implementation notes in this project's code comments/docstrings or run record; write the human-facing
result from the actual stable implementation and observations.
D3 may start long after D1/D2 under a different owner. Use the saved exact development delivery; choose an actual
useful task over its integrated capabilities rather than create one application for every upstream operator/graph.
Return library gaps to the D2 integration owner and source-only evidence gaps to the D1 owner. Do not rerun valid D1
source comparisons or require new per-source formal documents for an application task.
Final library endorsement belongs to the receiving review process; a successful user case supports only its declared scope.
For installed-package evaluation, exercise the actual packaged Python entrypoints and any native components on
the declared supported platform without the original source checkout or implicit development dependencies.
Scientific defects found in application return to D2 with the exact input/version and failure evidence;
D1 receives only missing source semantics or fidelity questions, not a demand to repair original science.

## Decide once, then act

Inspect the current project and supplied material first. A complete request needs no confirmation. Concrete
geometry, profiles, parameter values, output formatting, numerical controls, and manufactured test data are
normally callable inputs or implementation choices rather than reasons to stop.

If the request admits materially different models, geometries, boundaries, closures, safety behavior, or
result claims and the user's intent does not choose among them, ask once through the host's available
user-input mechanism with one compact blocking decision. Present two or three meaningful alternatives, their consequences, and a
recommendation. Do not ask a sequence of small questions. For a request such as “给我写个平衡程序”, first
resolve what physical equilibrium and observable the user means; do not run a guessed solver before that
answer. If the user delegated the choice, select the narrowest defensible model and state its claim boundary.

## Execute in the project

1. Inspect the workspace tree, existing code, tests, dependency files, and runnable commands that matter to
   the request. Do not require a new framework or language when the project already has a suitable one.
2. Record the smallest project-native scientific contract needed for the current slice: requested output,
   model, inputs, units, geometry, boundaries, failure behavior, provenance, claim ceiling, and unresolved
   material choices. Use stable owner/project refs and revisions for ordinary identity.
   Do not add per-record hashes or confirmation/rehash steps for routine requirements, snapshots, receipts, or project revisions;
   use digests only at an actual package, transfer, signature, secret, or compare-and-set integrity boundary.
3. Reuse compatible project code and ordinary libraries first. When an authorized published scientific
   catalog is relevant, read only the matching manifest and capability detail needed for this request, then
   use `scientific-asset-navigation` for a real applicability decision. Do not browse internal
   candidates or require the user to know platform package names.
   An explicitly staged development wheel/catalog may be used for an isolated evaluation, but its results remain
   unapproved. When the task calls for a matched scientific relation, the ordinary rerun path must invoke that asset;
   project code may adapt inputs and outputs, not replace its equations with a handwritten approximation.
   If the request selects or composes scientific assets, read the owner-resolved `scirel-solving` skill body and use
   it for scientific normalization, renewed discovery when a later request changes the relation or evaluation
   location, and evidence-bounded interpretation; a skill name in a host snapshot alone is not method execution.
   This skill still owns the runnable project files.
4. Treat unit, field-name, dtype, axis, index-base, and lossless shape conversions as adapters. A change to
   equations, closure, boundary physics, interpolation, discretization, solver update, or reconstructed state
   is a scientific change; use `scientific-relation-implementation` for that bounded relation.
   For a file-backed scientific project with a scientifically material parse, join or unit conversion, decide how a
   source-file field will be checked against the actual asset-port value before building the adapter. The check
   cannot start from the same parsed object that production uses. If the project claims its ordinary rerun checks
   this mapping, run that check before replacing user-facing outputs; an optional passing test suite is not a
   substitute. Cover materially distinct input paths, such as different source units, when making that claim.
5. Create or update the actual source, tests, configuration, run instructions, and requested result files in
   the current project. Keep scientific relations in project-native modules and keep serialization and plots
   at their normal output boundary.
6. Run the user-facing entrypoint and focused tests. On failure, localize the earliest broken contract, add or
   strengthen a focused test, make the smallest correction, and rerun. Reopen the user decision only when the
   failure proves a new material scientific ambiguity.
7. Read back the primary user-facing files, not only test summaries. Trace a representative value and, when
   present, an unavailable row from supplied input through the declared units, applicability and displayed
   result or reason. Use the format's ordinary independent reader to parse written numeric columns, rather than
   trusting the serializer's in-memory values or its own round-trip helper. Rerun the user-facing entrypoint with
   unchanged inputs and check the files it actually regenerates. If the project promises this file check on every
   rerun, put it in the ordinary delivery path; an optional test alone does not establish that guarantee. Check that
   physical conclusions follow from quantities actually computed. For a consequential rate-to-probability, cumulative
   event or changing-inventory claim, request an independent interpretation review before user delivery when an Agent
   is available. Check each finding and proposed replacement separately against the original inputs, model state,
   and actual outputs; a valid criticism need not make the reviewer's substitute answer valid. Record whether the
   solver, that reviewer or later user feedback found the issue. Sampling a field at a new location does not establish
   that every other material input is defined there. Report only
   commands, exit states, output, and artifacts actually observed. Do not claim success from generated text alone.

Keep interim chat concise. Do not narrate every tool call, and do not substitute displayed snippets for
writing the requested files into the project.

For a complex normalization or reuse decision, read
[references/normalized-requirement-and-asset-match.md](references/normalized-requirement-and-asset-match.md).
Load `scientific-computation-validation` only when the requested scientific or numerical claim needs
independent acceptance evidence. Load `scientific-runtime-dataset-construction` only when a specific
source-side state or observation is otherwise unavailable. Do not load every specialist skill by default.

## Delivery boundary

Do not silently invent material physics or replace a requested source-parity relation with a simpler related
model. A reference example does not supply unstated case data. Keep missing case values as runtime inputs and
use admissible manufactured values for development when appropriate.

The final response names the changed project files, required inputs, selected model/resources, assumptions,
commands run, observed results, and remaining scientific limits. Use `delivered` only when the requested
artifact exists and the declared user-facing path was run. Use `bounded_candidate` when it runs but evidence
is limited, `needs_scientific_input` when a material choice remains, and `cannot_complete` when the available
information or environment cannot support an honest implementation.
