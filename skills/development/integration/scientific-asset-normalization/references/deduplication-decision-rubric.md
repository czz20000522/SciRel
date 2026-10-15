# Deduplication and normalization decision rubric

The rubric treats the scientific contract as the organizing axis and compares scientific meaning before
software shape or project provenance. Every decision records the compared fields, the evidence refs, the
missing fields, and the claim ceiling. The result should read like a physical capability catalogue, not a
cleaned project directory.

## Comparison dimensions

Compare, in order:

1. relation identity, variables, assumptions, and implemented direction;
2. units, coordinates, axis order, shape, dtype, normalization, and index policy;
3. model, branch, approximation, geometry, and coordinate system;
4. boundary, closure, endpoint and initial-condition policy;
5. lifecycle, state ownership, update order, feedback, convergence, restart, and failure behavior;
6. discretization, interpolation, solver, matrix/RHS construction, and numerical tolerances;
7. applicability domain, provenance, and semantic/numerical/composition evidence independence.

## Allowed classifications

| Classification | Use only when | Required handling |
| --- | --- | --- |
| `exact_duplicate` | Explicit content identity is established by exact digest rules. | Preserve one source lineage for every duplicate; do not erase provenance. |
| `semantic_equivalence_proposal` | All material dimensions are aligned, but scientific equivalence still requires authorized evidence. | Keep as a proposal with rationale, evidence refs, and no automatic merge. |
| `parameterized_variant` | A material model, domain, geometry, boundary, lifecycle, discretization, or applicability dimension differs by declared parameter. | Keep separate and expose the discriminator in the contract. |
| `lossless_adapter_proposal` | The only changes are information-preserving naming, unit/dtype, axis/index, component, storage, or file-format conversions. | State direction, conversion, invertibility/information preservation, and failure behavior. |
| `composition_proposal` | Exact compatible dependencies produce a capability under a declared order and state contract. | Lock exact dependency refs, ports, ownership, lifecycle, feedback/convergence, and failure propagation. |
| `conflict` | Sources make incompatible claims or contracts for the same proposed identity. | Preserve both lineages and investigate with scientific-asset-correctness; keep separate while unresolved, reserving human judgment for genuinely unavailable facts or final approval. |
| `unresolved` | The available descriptors cannot decide the relationship. | Name the smallest missing fact and keep both candidates separate. |

## Never hide science in glue

The following are scientific or numerical work, not adapters:

- interpolation or extrapolation;
- boundary or closure completion;
- geometry conversion or reconstruction;
- dimensional reduction or projection;
- physics-specific normalization;
- discretization or quadrature changes;
- matrix/RHS generation;
- missing-state or lifecycle reconstruction; and
- any update, solver, convergence, or failure rule.

Record these as a scientific transformation or `input_correctness_conflict`, preserve the affected candidates,
and stop that normalization branch. A candidate graph edge cannot make the operation safe or equivalent.

## Evidence ceiling

Preserve the input evidence ceiling. Source parity proves behavior of the source implementation only. An
implementer test is not independent validation. A single matching output is not equivalence. When evidence
or applicability is missing, retain separate candidates with the bounded missing fact; normalization cannot
upgrade the claim.
