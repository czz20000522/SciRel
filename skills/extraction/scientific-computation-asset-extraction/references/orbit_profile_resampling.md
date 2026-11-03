# Profile-to-grid resampling reference

Use this reference when a source computes a scientific state on one explicit coordinate table and later queries it on another mesh or branch-specific coordinate list. Typical signals are `coeff1`/spline production, `terp1` queries, endpoint `iop` selectors, and a post-query normalization such as `field / reference_field`.

## Extract the edge, not the file routine

Record the full producer-to-consumer edge:

`source_coordinate + tabulated_state + interpolation_state -> target_coordinate + queried_state + diagnostics`

Before emitting code, make these fields explicit:

- coordinate meaning, monotonicity, units, and whether out-of-range queries clamp or extrapolate;
- table shape and field-to-table mapping;
- interpolation selector and endpoint boundary policy (`iop`, natural, four-point, or caller-owned second derivatives);
- query selector (`itab`, derivative order, interval index) and post-query normalization/sign/unit rule;
- hidden indices or surface selectors required by the consumer.

If the interpolation formula is generic but the boundary, normalization, index map, or units are source-specific, keep the generic kernel as a reused operator and emit a small task graph for the source-specific contract. Do not duplicate the interpolation formula in the graph.

## Minimal package shape

Prefer:

1. an existing parameterized interpolation operator;
2. one task graph that binds each source field to its boundary policy and target mesh;
3. explicit output diagnostics for interval selection, extrapolation, normalization, and supplied versus produced coefficient tables.

The graph must fail closed on non-monotone coordinates, mismatched field shapes, zero normalization, and non-finite values. It may accept caller-owned coefficient tables; if it produces them, return the boundary mode and source-equivalent selector in the state snapshot.

## Evidence and tests

Use the smallest executable evidence that proves the edge:

- polynomial or source-derived table replay with explicit second derivatives;
- one test for each source boundary selector used by a consumer;
- one normalization/sign/unit invariant;
- one path-loaded bundle-only smoke with no source mount;
- an evidence attachment naming the source anchors, numeric deltas when an oracle exists, and the remaining hidden-index or absolute-unit boundary.

Do not call a final-output parser a task graph. If the source does not expose the intermediate table, classify the missing table as `validation_oracle_gap`; if the table shape/axis/units are missing but the mapping is known, classify it as `configuration_or_schema_need`; if the mapping itself is absent, use `extraction_gap`.
