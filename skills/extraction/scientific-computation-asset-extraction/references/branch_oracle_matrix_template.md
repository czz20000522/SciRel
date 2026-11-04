# Branch and Oracle Matrix

Use this reference when a scientific project has multiple physical modes, boundary families, solver storage paths, or output schemas. The matrix is a migration aid, not a formal asset or validation report.

## One row per branch

| branch_id | selectors/config | producer chain | hidden/runtime state | emitted asset/graph + test | caller-owned contract | oracle/provenance + metrics | independent source-free attachment | static/source gate transcript | canonical gap | next action |
|---|---|---|---|---|---|---|---|---|---|---|
| `<one concrete selector tuple>` | `<mode, flags, mesh, species>` | `<state -> term -> transform -> output>` | `<rows/RHS/ghost/potential/etc.>` | `<relative asset path + test path>` | `<fields, shapes, axes, units, index base>` | `<capture command, tolerance, max_abs/max_rel/norm>` | `<evidence JSON path + demand + source_access=0 + digest>` | `<image, network, scan command/output>` | `<one of five labels>` | `<probe/package/schema/stop>` |

Never use `all modes`, `all boundaries`, `covered`, or a package count as a row. Expand nested selectors, species/surface combinations, storage modes, and edge families into concrete rows. Every non-terminal row must point to an executable package/test and an external evidence attachment; a terminal row must name the canonical gap, missing fields, and reproducible next capture. Do not use `dict`, `opaque_state`, `all_fields`, or wildcard schema entries: list each field's shape, axes, units, index base, optionality, and missing-field behavior. The matrix is not a validator and cannot replace package tests.

## Field-role ledger

For every intermediate field that crosses a graph edge, record its computational role separately from its name. This prevents a field that looks like a coefficient, source, or diagnostic from being wired into the wrong layer.

| field | producer | consumer | role | sign/normalization | allowed destination |
|---|---|---|---|---|---|
| `<exact field name>` | `<asset/node>` | `<asset/node>` | `<matrix coefficient \| RHS/source \| state \| diagnostic \| configuration>` | `<sign, scale, units, index base>` | `<explicit port or fail-closed reason>` |

Do not map by name alone. A matrix contribution, RHS/source load, hidden state, and diagnostic reduction are different roles even when their arrays share a shape. If a source-backed routine writes separate diagnostic accumulators and solver coefficients, keep them as separate ports. If a loss term belongs in matrix/stencil state rather than RHS, record that destination explicitly. If the role cannot be proven from source or oracle evidence, classify the edge as `configuration_or_schema_need`, `validation_oracle_gap`, or `extraction_gap`; never silently coerce it.

## Required branch questions

For every row, answer these before claiming coverage:

1. What selector or initialization state makes this branch execute?
2. Which source-specific producer, normalization, boundary, index, sign, or scatter rule changes?
3. Which intermediate state is omitted from ordinary final output?
4. Can the emitted bundle satisfy a custom demand without source reads?
5. What independent oracle proves the branch, and where is its evidence kept?

## Matrix gates

- A branch is not covered because an entry function or final-output parser exists.
- A matrix row is not evidence until its source-free attachment records the executed demand, `source_access=0`, bundle digest, image/network identity, and static/source scan transcript.
- One composition path never proves every matrix row. Run an edge-driven closure sweep and either execute each row or keep its evidence-bounded terminal gap visible.
- A branch with missing caller values or axes is `configuration_or_schema_need`, not an extraction failure.
- A branch with missing source-specific science or state-to-row/RHS transforms is `extraction_gap`.
- A branch with implementation but no defensible fixture or parity signal is `validation_oracle_gap`.
- Generic dispatch/shape/serialization glue is `ai_completable_glue` only when the emitted contract is sufficient to rebuild it.
- Damaged evidence that cannot safely establish the relation is `cannot_complete`.

## Stop condition

Keep the extraction phase `partial_extraction` while any package-worthy branch is unprocessed or any primary matrix edge lacks an emitted asset, explicit caller contract, validated glue, or evidence-bounded terminal gap. Do not turn the matrix into a package quota.
