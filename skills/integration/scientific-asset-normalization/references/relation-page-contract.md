# Normalized scientific relation page contract

One page represents one normalized scientific relation or one indivisible normalized capability. It is an
internal scientific contract linked to an exact callable, not an upload page, review conversation, tutorial,
release API, or public catalog article.

## Required content

1. **Normalized identity**: relation/equation family, direction, quantities, and why the boundary is irreducible.
2. **Scientific definition**: equations or algorithmic relation, symbol definitions, assumptions, and the
   distinction between science and lossless adaptation.
3. **Inputs and outputs**: identifier, scientific meaning, units/normalization/sign, dtype, shape, axes/indexing,
   valid range, ownership, lifecycle, and terminal consumer.
4. **Applicability and variants**: model, geometry, coordinates, boundary/closure, discretization, branch,
   lifecycle, supported domain, exclusions, and every parameterized discriminator.
5. **Normalized implementation**: callable binding, how it realizes the relation, exact dependencies, and
   material numerical/failure behavior.
6. **Relationships**: exact duplicates, equivalence proposals, variants, adapters, compositions, conflicts, and
   unresolved comparisons with exact related ids.
7. **Transformation and lineage**: all source candidates, predecessor versions, actual change, rationale, and
   retained source-specific behavior.
8. **Evidence and claim ceiling**: inherited correctness refs, normalization-specific regression results,
   adapter/composition evidence, actual limits, and unresolved contradictions.

Project names, source files, and implementation symbols may appear in lineage. They cannot be the normalized
scientific identity or the only explanation of a port. A common namespace or signature must not hide different
units, axes, boundaries, models, state lifecycles, numerical methods, or applicability behind an undocumented
default.

## Parity checks

The page, machine records, implementation, and tests must agree on identity, callable signature, ports,
dependencies, variants, relationships, and content digests. For code candidates, derive the real signature from
the normalized implementation rather than comparing two generated records. For TaskGraphs, verify that every node
and edge binds an exact version and that the documented terminal fields match the actual final state.

If these disagree, fail the local normalization result. If the conflict concerns inherited scientific
correctness, preserve the exact input and report `input_correctness_conflict`; do not rewrite the scientific claim
inside this page to make the records agree.
