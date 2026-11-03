---
name: scientific-d2-decomposition
description: Decompose a frozen D1 delivery into independent scientific claims, correction candidates, and evidence gaps for a downstream developer; never modify or merge the development library.
---

# Scientific D2 decomposition

Read [the standalone decomposition contract](../scientific-computation-asset-extraction/references/scirel-skill-core.md).
For the packet shape, load [D2 claim packet](references/d2-claim-packet.md).
This stage analyses the exact D1 material supplied by the caller and emits
developer-ready raw material. It does not import a development checkout or
invoke development skills.

1. Bind the D1 manifest, target/dependency digests, complete received
   denominator, source issues, runtime identity and declared scientific claim
   scope. Missing input is `blocked`/`NOT_RUN`.
2. For each retained relation or operator, write the independent claim,
   variables/units/axes, assumptions, boundaries, failure semantics, oracle
   requirement and affected reverse dependencies. Separate source fidelity
   observations from scientific correctness hypotheses.
3. Select the smallest discriminating analytic, manufactured, invariant,
   convergence, composition or terminal-state observation. Preserve original
   grids, thresholds, failures and tolerances; do not repair a candidate here.
4. Return a digest-bound D2 decomposition packet: claim matrix, raw findings,
   candidate correction proposals, evidence gaps, untested scope, claim ceiling,
   and the next developer owner. A proposal is not an accepted correction or
   integrated asset.
