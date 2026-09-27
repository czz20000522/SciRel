# KN1DPy convergence and accumulation development integration

Status: development baseline candidate for expert review, not qualified
whole-source D1 intake, expert approval or public release. SciRel comparison
base: `c9c5b91`. The intake at `647d5db` remains `pending_unapproved`;
the qualified whole-source D1 delivery root is empty.

## Scientific boundary

Four distinct operators are added. Per-generation stopping computes
`Delta_n = max(generation_density)/max(accumulated_density)` and tests the
strict `truncate` condition before the strict `0.003*seed_error` condition.
The accumulation operator appends one generation to caller-owned state,
preserves signed distribution cells and nonnegative density profiles, and
returns a new state without mutating the old one. The inner seed-pass and
top-level outer-pass operators both use `max(abs(previous-current))/max(current)`
but compare with `10*truncate` and `truncate`, respectively. Equality does
not re-enter either loop.

These are scalar decisions and a single explicit state update. No TaskGraph
or feedback loop is added; an eventual orchestrator must define state
ownership, reset order, stopping and an iteration cap. The four callables
have no direct callable dependencies. Their input/output ports can be
composed by a future reviewed graph without hiding iteration in a leaf.

## Source comparison and limits

The saved `KN1DPy-631d0bf1` operator files matched their intake SHA-256
pins: generation stopping
`dd110cbdc804c0ee3c4fcadbe7fb5da5254ae0a829de40ffc65c901ad9c89cc3`,
accumulation
`77eca995baaf8b01a9454ecbe07f6d28f90d5ac5429f8b4fda949558d71e4f80`,
inner seed convergence
`25f4918ff0ff2d68429088d9f12ef8902aa8981eab6ceee884255ccbc60e9e03`,
and top-level convergence
`3a5913b26bdac6361461f37c5494050a9102d6c98a98e9cb2906c9761d3dbbe2`.
Their archived direct tests passed 1, 2, 9 and 9 cases. Five read-only
SHA-pinned intake replays against the isolated SciRel import passed on
bounded valid inputs and selected rejections.

SciRel additionally rejects boolean, string and complex coercions,
non-finite ratios or thresholds derived from finite inputs, and invalid
seed controls even when the ordinary truncate branch would return early.
For supplied accumulation state, SciRel checks the generation stacks,
aligned totals and completed index before appending. The source accepted
unchecked state; externally reconstructed totals that differ from source-order
floating addition are rejected. This is a deliberate state contract
tightening, not a claim of parity on malformed or overflowing inputs.
The intake accumulation document incorrectly mentioned a `truncate` input;
the dev5 exact document now describes the actual state and distribution ports.

## Verification

- The direct regression failed at import before implementation. Eight
  targeted cases also failed against the unchanged intake runtime, including
  non-finite and non-real truncate, missing seed control, inconsistent state
  and overflowed inner threshold. The final source-free file covers the four
  relations, strict threshold boundaries,
  signed cells, three successive state updates, caller immutability,
  inconsistent state, input types and overflow (23 passed).
- `pwsh ./scripts/check.ps1 -Mode affected` selected six test files without
  full-suite fallback and passed 104 tests.
- All 38 `scirel.asset-document.v1` records passed source-runtime and
  executable-example validation. The catalog remains `partial: 38/85` at
  `0.1.0.dev5`; no release was run.

The archived evidence is historical development comparison. It does not
establish a new strict D1 freeze, an independent transport-physics oracle,
expert acceptance, version-level trust or distribution licensing.
