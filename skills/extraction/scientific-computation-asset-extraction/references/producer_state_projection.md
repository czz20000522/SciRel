# Producer-State Projection

Use this reference when a source parser, file reader, or external adapter produces values that a scientific setup routine then normalizes before they reach a solver, geometry kernel, or public state.

## Recognize the boundary

Treat the projection as a scientific producer when it owns any source-specific:

- sign convention or orientation correction;
- unit conversion or scale factor;
- array reversal, index-base, axis-order, or mesh construction;
- boundary/limiter/ghost fill policy;
- branch selector or current/toroidal-field sign state.

Do not collapse this into file parsing. Parsing emits the input representation; projection emits the source-consumer representation.

## Minimal contract

Model four stages explicitly:

`parsed input -> normalization -> ordered/state projection -> consumer contract`

The package should expose:

- caller-owned parsed state (mapping, not a path);
- normalized arrays/scalars with units and axis order;
- sign/orientation and profile-order diagnostics;
- explicit flags for fields still requiring spline coefficients, hidden solver state, or runtime configuration.

Reject or classify missing values instead of guessing them. A nonzero coordinate shift, missing profile derivatives, or unknown branch sign is a schema/oracle gap when the source semantics cannot be recovered safely.

## Evidence tuple

Record source anchors for each transform, input/output field names, shape, units, axis/order, sign policy, boundary policy, branch selectors, and numeric checks for at least one interior and one boundary case. Keep source probes and JSON evidence outside formal asset packages.

## Reuse rule

Wire the producer into a task graph before downstream sampling or solving. Do not duplicate its conversion in every consumer, infer hidden state from final outputs, or claim full common-block parity when only the explicit producer contract is emitted.

## Gap mapping

- missing source-specific transform: `extraction_gap`;
- missing runtime value/shape/unit/selector: `configuration_or_schema_need`;
- generic parsing/dispatch only: `ai_completable_glue`;
- missing comparable source/intermediate oracle: `validation_oracle_gap`.
