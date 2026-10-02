# Scientific Contract Review Across Stages

Use [stage boundaries](stage_boundary_contract.md) to identify the current responsibility. D1 review inspects
the exact source-backed code, YAML, docstrings, scientific anchors and bound evidence. It does not require a
standalone Markdown page or require a reviewer to avoid opening code. Formal documentation is prepared after
D2 stabilizes the retained new/changed assets and before final review freeze.

## Questions that must be answerable in D1

1. What scientific quantity, numerical relation or directed state transform is computed, and which inspected
   source formulas, coefficients, branches and state transitions define it?
2. What exact callable is exposed and what are every real input and output, their physical meaning, units or
   documented unit uncertainty, axes/indexing, normalization/sign, domain and lifecycle?
3. Which source-specific boundaries, closures, clipping, convergence and failure behavior are preserved?
4. Which implementation comparisons and executed numerical checks establish the claim, on what inputs and
   applicability domain, with what predeclared oracle and tolerance?
5. Which full-source capabilities, branches and terminal paths are covered, excluded with evidence, or unfinished?

Use exact locators to existing authoritative representations. Do not demand a second narrative for facts already
reliably expressed in code or YAML. A missing physical convention or unobservable terminal output is a substantive
gap even if a page exists; an absent heading is not one.

## TaskGraphs

The YAML and implementation jointly state the black-box ports, exact dependency versions, scientific node roles,
required `producer.output -> consumer.input` handoffs, non-interchangeable order, state/branch/feedback semantics,
finite stopping bounds and failure behavior. Empty YAML ports cannot represent a graph that consumes real state.
Source call adjacency alone is insufficient, and hidden numerical work in glue remains an undeclared asset.

## Findings and later documentation

Return independent evidence-bound findings through
[scientific operator review](../../scientific-operator-review/SKILL.md). Preserve source parity, independent
scientific/numerical correctness and bounded functional reassembly as distinct claims. Missing evidence caps only
the claim it affects. A mechanical path or packaging failure with independently attributable scientific output is
repaired under the stage-boundary rule; it is not itself a demand for expensive recomputation.

Keep a known defect or source divergence once in a discoverable gap record with the inspected error, affected
domain, evidence, claim ceiling and reopen condition. Justified scientific corrections follow
[scientific correction](../../scientific-relation-implementation/references/scientific-correction.md); an unexplained
source mismatch cannot pass as a documentation correction. Never fabricate a source citation.

After D2 deduplication and assembly, only retained new/changed assets need the canonical asset document owned
by the receiving review process and its supplied scientific-document contract.
Those later-stage resources are not deployed with D1 and need not be loaded by its reviewer. The document must disclose their scientific
contract, actual ports, applicability and known limitations without relying on the producer's memory. Reference
the final exact code and evidence rather than embedding repeated raw logs or separate review copies. Duplicate
dispositions retain lineage and comparison evidence without extra pages or human review items.

Agent findings and development readiness do not grant human approval or public release. The human decision is
about the final frozen review version, not a routine prerequisite to each intermediate repair or draft.
