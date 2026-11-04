# Capability Evidence Matrix Template

Use this matrix when a request names multiple capabilities, branches, artifacts, invariants, or completion gates. It is a claim-coverage ledger, not a package manifest and not a validator.

## Row contract

Create one row for every named requirement, capability, branch, artifact, invariant, or gate. Do not collapse rows into package counts, "all modes", or "covered" summaries. Use concrete selector tuples so a later run can reproduce the demand.

Required fields:

```text
requirement_id/source_anchor |
target_path/equation_anchor_ids/scientific_node_or_edge |
capability/claim_scope/selectors |
acceptance_criterion |
asset_or_graph |
executable_demand |
evidence_attachment (provenance, metrics, source_access, digest, image, network/static transcript) |
status (proven | partial | unverified | blocked) |
canonical_gap |
missing_fields/next_capture
```

For caller-owned state, list every field explicitly with shape, axes, units, index base, optionality, and missing-value behavior. Do not use `dict`, `opaque_state`, `all_fields`, or wildcard schema entries as a substitute. A package test must name the demand; an external source-free attachment must prove the same demand with the bundle digest and runtime tuple.

## Hard gates

- A package gate, one smoke, one composition, final-output parser, or aggregate test count does not prove full-core coverage.
- Every non-terminal row needs an executable demand and an external evidence attachment. One composition can cover only its declared selectors and edges.
- A terminal row needs a canonical gap, evidence for the boundary, an explicit missing-field list, and a reproducible next capture route.
- Keep the project phase `partial_extraction` until every row is proven or terminally classified; never promote on package count alone.
- Reconcile rows with the current validated `capability_progress.json`. The matrix supplies claim-level evidence; it does not hand-author progress. A row absent from the equation-centered census, a census work unit absent from this matrix, or a different earliest unresolved node/edge is a consistency failure.
- Keep validation JSON and probes outside the formal asset tree. The matrix may reference them but must not turn them into task-graph packages.

## Minimal audit sequence

1. Copy every named claim into a row and bind it to a target path, central equation, scientific node or glue edge, and Level 0/Level 1 framework anchors.
2. Add concrete selectors and an executable bundle demand for each row.
3. Attach source-free evidence with provenance, metrics, source-access result, bundle digest, image identity, and network/static transcript.
4. Mark proven, partial, unverified, or blocked; classify every unresolved row with one canonical gap and its next capture.
5. Re-run the same-scope composition after formal changes, then update the matrix before making a completion claim.
6. Regenerate and validate the external progress snapshot from the census, matrix, evidence receipts, and reassembly results; do not edit its percentages to match report prose.
