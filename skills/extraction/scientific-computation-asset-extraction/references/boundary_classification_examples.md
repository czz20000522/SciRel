# Boundary Classification Examples

Use these as calibration examples, not project-specific rules.

## Extract Core Scientific Behavior

If source code computes a governing term, diagnostic normalization, stencil, row/RHS mapping, collision/source/RF/transport coefficient, boundary branch, or source-local unit/sign convention, emit an operator or task-graph internal kernel. Do this even when the code is short. A future agent should not invent source-specific science from memory.

Canonical gap when missing: `extraction_gap`.

## Keep External Shape As Configuration

If a run fails because an external file, netCDF field, user payload, or benchmark array has unknown axes, field names, concrete values, or units, but the core asset already declares the per-case scientific contract, classify the issue as schema or initialization work. Do not promote the file layout itself into a core operator.

Canonical gap when missing: `configuration_or_schema_need`.

## Let Generic Adapters Stay Glue

Parsing, field renaming, unit conversion when units are supplied, array reshaping, per-surface loops, DAG dispatch, simple scheduling, and error handling are adapter/glue unless they encode source-specific numerical semantics. Put required glue inside the nearest task graph or run-local adapter when needed for execution.

Canonical gap when missing: `ai_completable_glue`.

## Separate Validation From Extraction

If the emitted asset has the core formula or graph but cannot be compared to the original run because intermediate source arrays, random histories, residual traces, or full-runtime probes are absent, classify the issue as validation. Do not backfill hidden physics just to make a parity test pass.

Canonical gap when missing: `validation_oracle_gap`.

## Split Mixed Edge Failures

One framework edge may expose more than one missing thing. If a step lacks a source-specific index map and also lacks user-provided axis names, record the index map as `extraction_gap` and the axis names as `configuration_or_schema_need`. Do not collapse the whole edge to the harsher label unless the core scientific transform itself is missing.

## Bridge Source-Specific State, Do Not Handwave It

If two extracted nodes exist but the edge between them needs a source-specific row map, boundary selector, residual/RHS builder, scatter/gather rule, or hidden-state projection, that bridge must be emitted as an asset, internal kernel, or controlled task-graph glue. A future agent should not reopen the source to invent it.

Canonical gap when missing: `extraction_gap`.

## Treat Case Binding As A Contract

If a case provides arrays or fields whose axes, units, species/order, region labels, or time/radial indexing are not declared by the emitted package, add a schema/configuration contract. Do not bake one observed case layout into the core formula.

Canonical gap when missing: `configuration_or_schema_need`.

## Test Composition, Not Just Nodes

If every operator test passes but a primary framework path cannot move from one node's declared output to the next node's declared input without new source reading, the extraction is not complete for that path. The missing piece may be an internal kernel, task-graph glue, schema contract, or validation oracle; classify it with the canonical labels above.
