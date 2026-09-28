---
name: scirel-solving
description: Use when turning a user's scientific request into a normalized problem, a SciRel-based solution plan, an executed result, and an evidence-bounded explanation using only the visible released catalog.
---

# SciRel Solving

## Purpose

Use the SciRel capabilities visible to the current runtime to answer a scientific request. First understand and
normalize the science, then discover and compose applicable assets, execute them, check the actual result, and explain
the result and its limits. Do not begin by guessing a function from the user's wording.

This skill is SciRel-owned and may run in CodeFusion, Claude Code, Codex or another capable harness. The harness owns
the session, permissions, tools, execution environment, artifacts and delivery; it does not own the scientific
semantics in this skill. This workflow does not inspect unpublished candidates, approve assets, publish TaskGraphs,
or substitute PINN/XNet training for SciRel computation.

Normal user runtimes expose only released assets. An explicitly scoped, isolated development evaluation may instead
bind an unapproved wheel and matching catalog; use the same applicability and invocation checks while labelling every
result as development evidence, not a trusted or public release. Do not add a per-request step that re-proves approval
of a released asset. A version identifier may be recorded for reproducibility without becoming part of the scientific
argument.

Read `docs/requirements/scientific-request-workflow.md` for user-visible requirements and
`docs/design/scientific-request-workflow.md` for workflow boundaries when changing this method.

## Normalize the request

State what the user is asking the system to compute before selecting assets. Capture the scientific model, relation
direction, unknowns, geometry, coordinates, units and normalization, initial/boundary conditions, closures and
profiles, supplied inputs, requested outputs, tolerances, stopping conditions, and delivery form to the extent that
they matter for this problem.

Separate user facts, explicit assumptions, defaults, and unresolved questions. Ask for clarification when an unknown
would change the model, applicability, boundary, closure, units, or meaning of the result. A harmless presentation
choice should not block the scientific work. Never silently choose a materially different model.
When two applicable ways to evaluate or reuse a result would give different numbers and the request does not choose
between them, treat the result definition as unresolved even if both calculations are scientifically valid. Ask one
focused question while continuing independent preparation. If the host cannot obtain an answer and a choice can be
reversed without losing prior work, state the narrow assumption before delivery, label the result by that choice, and
keep enough inputs and prior output to correct it later. A later clarification changes the requested result; it does
not retroactively make a correctly executed alternative calculation a scientific error.
When a request moves from a coefficient or instantaneous rate to a probability, cumulative amount, or remaining
population, identify the object being counted and the state that changes with time. Distinguish a prescribed profile
from a state evolved by the model, and identify any replenishment, depletion, transport or repeated-event assumption
needed for that derived quantity. An integral of a rate over prescribed states does not by itself establish the fate
of one initial object or the inventory left afterward. Apply this check where the requested interpretation depends on
it; do not turn it into a questionnaire for unrelated calculations.
For each material input, distinguish a user statement, a fact read from a user file, an exact-document default, and
your own proposal. Keep a file location or artifact reference for file facts. Connect the user's goal to the expected
outputs and checks; do not describe a proposed assumption as a user requirement.
When a later note or file appears to fill a missing scientific condition, read the claim in context, including
uncertainty, negation and conflicts with other sources. An allowed literal inside a tentative or contradicted
sentence is not a confirmed input. Ask one focused question about the material condition while continuing any
independent work. After clarification, version the normalized problem and link the accepted claim to its source;
if a repeatable tool needs a machine-readable field, write an explicit source-linked declaration for it to validate.
Keep case-specific accepted facts and source bindings in versioned data, not duplicated as constants in a reusable
converter. The tool can check structure, file identity and conflicts; it cannot prove that a new note's prose means
what the Agent declared. Do not make the user edit code or teach a parser to infer scientific certainty from prose.
When a later request adds an observable or changes where it is evaluated, update the normalized problem before
continuing. Reuse earlier work only for the portions whose scientific meaning and inputs remain unchanged.
If the later request compares with or reuses prior delivered charts or files, identify those outputs before writing:
keep the old deliverables distinguishable and accessible, and link old and new results to their actual inputs. Old
columns in an overwritten file do not preserve the earlier deliverable. An explicit replacement with no continuing
old-result dependency may follow the host's ordinary artifact update behavior. Verify what a user can open after the
follow-up; do not claim byte-identical recovery without a retained source. When handing off a reusable command,
check its ordinary rerun behavior too: changed inputs must not silently replace a prior output still used for
comparison. A distinct output path or an explicit replacement decision is enough; an unchanged rerun need not
create another copy.

## Discover applicable capabilities

Use `scientific-asset-navigation` for broad searches, competing models, adapters or multi-asset compositions. Search
the visible catalog progressively: route to a bounded shortlist, inspect summaries, then read the exact documents of
serious candidates. Decide applicability from relation and direction, model, geometry, coordinates, units, axes,
boundaries, inputs, output contract, failure behavior, and evidence ceiling.
Locate the catalog through the current harness's declared connector, mounted snapshot or environment resource; it
may be outside the user project. When the selected environment says it supplies a catalog, inspect that binding
before treating its absence from the project tree as an unavailable catalog or asking the user to upload it.
When the catalog is exposed through SciRel's thin adapter, use its declared request and response fields rather than
guessing connector envelopes from asset documents or implementation source. Read
`docs/requirements/thin-mcp-adapter.md` when that full contract is mounted.
When the selected task explicitly requires an adapter-mediated run, use the adapter's actual
`catalog.discover -> asset.read(detail=document) -> callable.invoke` operations for discovery, exact matching and
execution. Direct catalog-file browsing followed by `scirel` imports may be a separate useful project path, but it
does not satisfy that adapter-path claim. Keep compact evidence from the returned operation responses in the host's
ordinary tool record: operation, catalog root, selected asset ID, implementation version and result/check status,
without dumping full documents or private inputs. If the adapter path cannot run, report that boundary instead of
describing a direct call as equivalent. This condition does not require the adapter in tasks that did not select it.
If the full repository contract is not mounted in the user project, use the bundled
[thin adapter run reference](references/thin-adapter-run.md) for the core envelope and response shape; it does not
replace scientific matching against the returned exact documents.
Route and summary records are sufficient to discard clearly unrelated assets. Do not load every exact document to
prove absence; load exact documents only for serious candidates and scientific near misses whose detailed contract
materially affects the decision.
If a later request needs a new scientific relation, such as evaluating an existing field at specified locations,
or a selected consumer needs a scientific input not supplied by the user, search the same bound catalog again for
that relation or an applicable producer of the input. An earlier shortlist for a different output does not establish
its absence.

The catalog bound to the visible release is the only capability-discovery and applicability source for this workflow.
Once it is available, do not scan installed modules, package exports, source trees, tests, provenance, historical
admission records, or wheel manifests for additional capabilities or for facts missing from an exact document. Those
materials may diagnose a catalog/runtime consistency failure after a catalog asset has been selected, but they may not
create or widen a solution plan. Treat an importable but undocumented callable as unavailable to this workflow.
Do not enumerate or resolve runtime callables to prove that a capability is absent. Resolve only assets that survive
exact-document matching and enter a valid solution plan; invoke them only after that plan passes its preflight checks.
A rejected or missing candidate needs no runtime probe.

Names, source projects, keywords, and similarity may improve recall but cannot make an incompatible asset applicable.
If pagination is unfinished or catalog coverage is partial, report that no match was found in the inspected scope;
do not claim that SciRel as a whole lacks the capability. Exhausting every included record does not make a partial
catalog complete. Name this outcome an inspected-scope gap or incomplete catalog coverage, never a release capability
gap, even with a qualifier. If the complete visible release has no applicable asset, report a release capability gap.
Never replace a missing capability with a nearby weaker model.

## Plan and validate the run

Prefer one existing TaskGraph when it solves the normalized problem. Otherwise build a per-request run instance from
visible Operators and TaskGraphs. That instance is not a catalog asset and must not be published merely because it ran.

For every node and edge, check the actual applicability and port meaning, units, shape, dtype, coordinates, axes,
normalization, ordering, state, branch and failure propagation. Ordinary dependencies must form a DAG. Any iteration
must have explicit state, update order, stop/convergence condition, bound and nonconvergence outcome.
For a dynamic composition, identify the source of every node input and the exact upstream output-to-input port
connection. Before execution, keep the plan version and its intended checks with the run. If the user corrects a
material condition, normalize and validate a new version; do not reuse execution evidence from the old one.
For a relation that pools rows to estimate a derivative or other set-dependent quantity, establish why those rows
form the scientific sample set required by its exact document. Matching columns, shape, or apparatus labels alone
does not establish a shared physical coordinate or interpretation criterion. If that premise is unresolved, do not
turn the callable's numerical flags into even a provisional physical screen; ask the material question and continue
with independently useful input preparation or other applicable relations.
A separately calculated pointwise formula may be delivered as arithmetic, but its sign is not evidence that a
named physical condition is satisfied until that condition's model and interpretation premise is sourced.
If a callable returns both pointwise and set-dependent outputs, an inapplicable set-dependent branch cannot be made
applicable by computing it and hiding or disclaiming its numerical flags; a documented degenerate-input convention
does not establish the missing physical premise. Use a separately applicable asset for the pointwise relation, or
identify a project-local calculation and its own validation route without attributing it to the rejected callable.
When joining, converting or allocating source facts into scientifically material ports, plan the check's data path
before implementing the production mapping. Identify a raw source fact and the port value expected from the exact
contract; decide how the check will obtain that fact without consuming the production adapter's already-mapped
object. The production parser and join are part of that mapping too: an `Event` or species object returned by the
same loader is not a raw-file witness. Recomputing the scientific output from that object tests the relation
downstream, not the source-to-port mapping. Choose a witness that would change under a plausible wrong field,
join or conversion, or mark that mapping unverified and limit the result claim. Pure field renames and
serialization do not need a separate witness. If a join uses a supposedly unique identifier, check ambiguity
across every joined input, including a prior result used as a baseline; inspecting one representative row cannot
establish that other identifiers are unique.
When writing intermediate artifacts that may feed later user requests, include the axes, coordinate basis, support
masks and other metadata needed to reuse the values, or record strong digest bindings to the exact input files that
carry them. If an older intermediate lacks this metadata, a later stage may use the current configuration only after
checking shape and digest consistency, and must state that it cannot prove byte-identical coordinates from the
original run. Do not present such a derived result as stronger provenance than the artifact supports.
When a source quantity represents a whole object but the selected relation consumes discretized pieces, check how
the total is apportioned; applying the total independently to every piece changes the physical input. If a user asks
for values at stated coordinates, a nearby grid value is only a labelled approximation, not that location's value.
Distinguish sampling an already computed field from recomputing the relation at a new point. Recomputing requires
every material input and boundary/support rule to be defined there; do not extend grid-only values or masks by
assumption. If only grid values are supported, use an applicable scientific sampling relation. A geometric in-domain
result is still numerically unavailable when its required stencil contains undefined values.

When connecting a vacuum-field output such as `psi_vac` to an equilibrium or material support consumer, matching
names, shapes and even `Wb/rad` units are only port checks. Verify the same flux definition, reference and boundary
conditions, closure, and additional physical inputs across the exact documents for that edge. A vacuum field alone
does not supply a separatrix, density support, plasma response or heating. If the bound catalog does not establish
the connection, deliver the bounded vacuum result, identify the unresolved science owner decision, and do not infer
a `2*pi` conversion or missing physics in glue. Reassess the edge when the catalog version changes.

Glue may select fields or perform declared lossless representation changes. Do not hide interpolation, closure,
discretization, geometry reconstruction, scientifically material unit conversion, or another scientific relation
inside glue. If such a relation is required and no applicable released asset exists, stop with a capability gap.

## Execute and check the result

Execute only after the plan is valid. Preserve the causal SciRel exception and do not silently retry with another
model, asset, convention, or tolerance.
If an asset rejects a scientifically empty or invalid result, a downstream file format's ability to represent it
does not turn that asset call into success. Keep any separately useful mapped data as a labelled diagnostic, deliver
unaffected branches, and report the failed relation. A different implementation needs its own explicit validation
route; do not attribute its output to the rejected SciRel asset.
For each scientific relation in the plan, verify that execution actually invokes the selected asset. A project-native
replacement is a new implementation and validation route, not evidence that the catalog asset was reused.

Choose result checks that discriminate this request: finite/domain checks, dimensions, boundary conditions,
conservation, residuals, convergence, positivity, symmetry, limits, or another problem-specific invariant. Use
`scientific-computation-validation` when the requested claim needs independent validation design. Distinguish checks
that passed, failed, were inapplicable, or were not performed. A successful call is not proof of physical correctness,
and a local check does not expand an asset's evidence ceiling. Do not run the full repository test suite as part of an
ordinary user calculation.
For a numeric file or table delivered to the user, read the written artifact through a consumer path independent of
the production serializer and its in-memory values. Check that numeric cells parse as numbers, that representative
source-derived values and units survive serialization, and that missing or unavailable rows retain their declared
meaning. Rerun the ordinary user entrypoint with unchanged inputs and check the files it actually regenerates; a
passing in-memory result or optional test does not establish a readable, repeatable delivery. If every rerun is
claimed to enforce file quality, include this check in that ordinary path before promoting new user-facing results.
For a planned material source-to-port witness, compare the independently derived expected value with the actual
port passed to the asset, not merely with another result computed from that port. Repeat it for materially changed
input rows and, when available, compare a raw-source-derived observable with the delivered one. If independence is
unclear, perturb only the production mapping in an isolated copy and confirm the ordinary check fails. Otherwise
report downstream consistency only, not a verified source-to-port mapping. For a rerunnable project, distinguish
checks performed by its ordinary entrypoint from optional tests; if claiming that reruns reject bad mappings, run
the witness before replacing user-facing results. A separate passing test suite does not make that entrypoint fail.
Separate computed observations from physical interpretations. A zero crossing, a finite response, or a visually
suggestive pattern is not by itself evidence of resonance, absorption, or another mechanism; name the additional
relation or check required before making that claim. Likewise, a small departure from proportionality in a saved
composition is an observation about that composition, not evidence that the departure is physical without an
independent model or check supporting that attribution.

Classify a failure as an input/port or environment error, an applicability or capability gap, or a failed scientific
result check. You may repair a non-scientific execution error and rerun affected steps and checks, recording what
changed. Revalidate the plan when a repair changes a model, asset, unit, boundary, tolerance, or connection. Preserve
failed scientific checks and stop when the result cannot be justified; do not silently switch assets or relax checks.
Keep an unresolved or corrected user result definition separate from those failures. Preserve the first interpretation
and its checks, record the clarification or changed assumption, and validate the new result on its own terms.

## Explain and hand off

Return the requested result, chart, file or project together with a concise audit explanation containing the normalized
problem, assumptions/defaults, selected capabilities and applicability, material nodes/connections, executed checks,
evidence limits, untested properties and capability gaps.
Before delivery, check each nontrivial physical interpretation or numerical-error claim against the actual run: identify
the computed quantity, applicable relation and convention, and what was held fixed in any comparison. If a required
input, convention, matched domain or independent check is missing, report the observation without promoting it to a
mechanism, causal attribution or error bound.
For a consequential claim that crosses from a computed rate into an individual probability, accumulated event count,
or evolving inventory, have an independent reviewer challenge the draft explanation against the input state, exact
asset contract, and actual output before it reaches the user when such an Agent is available. Treat each reported
defect and each proposed replacement as separate claims: check both against the original inputs, the model's state
and evolution assumptions, and the computed quantity before changing the result. Accept a supported defect without
copying an unsupported numerical or physical replacement; leave an underdetermined quantity unresolved when the
missing state cannot be recovered. Recheck affected files. If no independent Agent is available, perform a separate
interpretation pass and say that it was not independently reviewed. Record whether a problem was found by the solver
before review, by the pre-delivery reviewer, or only after user feedback. A corrected result does not make an earlier
unsupported claim an autonomous pass. This review is conditional on the claim, not a gate on every simple calculation.
For an error-bound claim, name the error target and domain, its reference, and the argument that bounds it on that
domain. The maximum difference on a finite comparison set describes those sampled points; it does not by itself bound
unsampled values, solver accuracy, or physical-model error. If the user asks for a wider bound, answer that question
separately rather than relabeling the sampled maximum as the requested bound.

Expose decision provenance and observable evidence, not hidden chain-of-thought. Keep four logical products --
Normalized Problem, Solution Plan, Execution Evidence and Result Explanation -- but choose a task-appropriate format.
Do not require a universal manifest or script, and do not create empty artifacts merely to satisfy those names.
Make three linked views readable when useful: requirements, assumptions and gaps; capability nodes and port
connections; actual execution and checks. These are views of the same run, not a newly published TaskGraph.
