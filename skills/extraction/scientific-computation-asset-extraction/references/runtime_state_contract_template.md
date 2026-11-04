# Runtime State Contract Template

Use this template when a solver's public output omits intermediate state needed by an outbound bundle replay.

## Contract identity

- `contract_name`: `<project>_<solver>_runtime_state`
- `source_workcopy_provenance`: `<read-only snapshot + disposable workcopy + branch/config selectors>`
- `source_access_during_replay`: `false`
- `shape_and_index_base`: `<shape, one-based/zero-based convention, compressed dimensions>`

## Layered payload

### System metadata

Record solver mode, species/background selectors, surface/orbit selectors, mesh sizes, timestep, storage class, and tolerance.

### Row identity

Each row record must carry `i`, `j`, `eq_index`, `row_kind`, and any compressed-map identity. Do not infer row identity from a final output array.

### Dense numerical state

Record the caller-owned coefficient/metric/weight fields used by the emitted stencil or RHS operators, including units, axes, and finite-value policy.

### Edge/ghost state

For each boundary family, record `row_points[*].params`, `idistr`, `idistl`, column map, source-specific stencil parameters, and the branch selector that made the row applicable.

### RHS and normalization

Record previous distribution, source/spatial-source terms, effective timestep, RHS scale, row norm, sign/floor policy, and post-transform order.

### Velocity-zero state

Record either final rows or the complete source-backed pre-row contract required to produce fixed/scale or conservative aggregate rows. A final output file is not a substitute for this layer.

For a conservative zero-velocity boundary, a sufficient pre-row payload includes the branch-specific flux/stencil terms, raw RHS term, normalization, row/distribution selectors, compressed equation index, and mode selectors. If any are absent, keep pre-row emission caller-owned and fail closed.

Producer-boundary probe rule: capture raw terms immediately before source normalization, then compare emitted columns, normalized coefficients, and normalized RHS for independent row families and at least two cases. Only after that replay passes may the raw-term-to-pre-row mapping be emitted as an operator; final constraint/aggregate construction remains a separate operator.

## Replay obligations

- Serialize and reload the payload without source access.
- Reproduce row count, columns, coefficients, RHS, normalization, solve residual, and finite next state.
- Report `max_abs`, `max_rel`, aggregate norm, nonfinite count, skipped cases, and source-access counters.
- Run at least one bundle-only composition from reconstructed state into the downstream solver/diagnostic graph.

## Gap classification

- Missing source-specific formula, index map, boundary transform, or state-to-row mapping: `extraction_gap`.
- Missing value, shape, unit, selector, or declared state field: `configuration_or_schema_need`.
- Missing generic serializer, adapter, or dispatch: `ai_completable_glue`.
- Missing independent source/intermediate oracle: `validation_oracle_gap`.
- Damaged evidence that cannot be safely reconstructed: `cannot_complete`.
