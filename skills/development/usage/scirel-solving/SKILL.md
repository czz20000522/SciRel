---
name: scirel-solving
description: Normalize a scientific request, select and execute applicable authorized capabilities, check the result, and explain evidence and limits for the declared scope.
---

# Scientific request solving

Read [the shared operating contract](../../references/scirel-development-core.md).
This is the D3 orchestration entrypoint: it produces a normalized problem, solution plan, execution evidence and
result explanation. It cannot approve assets, publish TaskGraphs or replace a selected relation with another model.
Normal runtimes expose released assets. An explicitly isolated development evaluation may bind an exact unapproved
wheel and matching catalog; label every result as development evidence and do not re-prove release approval per request.

## Normalize before discovery

State the requested quantity and relation direction, unknowns, model/geometry, coordinates/units/normalization,
initial and boundary conditions, closures/profiles, inputs, outputs, tolerances, stopping conditions and delivery
form as far as they affect this case. Distinguish user facts, file facts, exact-document defaults and proposals;
retain file references. If a later request adds a relation or observable, re-normalize and re-run discovery; an early
shortlist cannot prove the new relation absent.

Use [asset navigation](../scientific-asset-navigation/SKILL.md) against the bound catalog, then build a per-request
plan from visible Operators/TaskGraphs. Validate every node/edge's actual ports, units, shape, axes, coordinates,
state, order, branch and failure propagation. Ordinary dependencies are a DAG; iteration declares state, order,
stop condition, bound and nonconvergence outcome. Use [project implementation](../scientific-project-implementation/SKILL.md)
for persistent files and [computation validation](../../scientific-computation-validation/SKILL.md) when an
independent claim is requested. For an explicitly selected adapter-mediated run, read [the thin adapter example](references/thin-adapter-run.md)
and use the declared adapter operations; it is not a universal envelope.

## Material boundary checks

When connecting a vacuum-field output such as `psi_vac` to an equilibrium or material support consumer, matching
names, shapes and even `Wb/rad` units are only port checks. Verify the same flux definition, reference and boundary
conditions, closure, and additional physical inputs across the exact documents for that edge. A vacuum field alone
does not supply a separatrix, density support, plasma response or heating. If the bound catalog does not establish
the connection, deliver the bounded vacuum result, identify the unresolved science owner decision, and do not infer
a `2*pi` conversion or missing physics in glue. Reassess the edge when the catalog version changes.

Do not hide interpolation, closure, discretization, geometry reconstruction or scientific unit conversion in glue.
A capability gap remains a gap. Keep computed observations separate from physical mechanism explanations: a pattern,
zero crossing or finite response needs its own relation/check before calling it resonance, absorption or causation.

## Execute and explain

Execute only after the plan is valid, using the exact selected asset/runtime; do not silently retry with another
model, convention, tolerance or provider. Check dimensions, domains, boundaries, conservation/residuals,
convergence, limits and failure semantics that discriminate this request. Read written artifacts independently and
rerun the ordinary user entrypoint when repeatability is claimed.

Return the four linked products with exact identities, assumptions, selected capabilities, port map, checks actually
run, `passed/failed/blocked/NOT_RUN/inapplicable` counts, evidence-plane references, claim ceiling and capability
or human gaps. A successful call is not physical correctness; a local check cannot expand an asset's evidence ceiling.
