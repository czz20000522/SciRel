# Boundary-Coverage Manual

## Coverage principle

Partition the declared input domain by behavior, not by convenient sample count. A case covers a
partition only when the source target branch is actually entered after its genuine predecessor
chain. Keep a coverage row for every meaningful branch, state transition, and failure boundary.

For each material partition, prefer:

1. one ordinary interior case;
2. both sides of every branch threshold plus the exact threshold when defined;
3. endpoint/minimum/maximum active-extent cases;
4. one invalid or fail-closed case when the contract rejects input;
5. one unseen holdout case;
6. one independent scientific or numerical check when applicable.

## Common boundary dimensions

- zero, sign change, positivity/nonnegativity, and very small/large finite values;
- first/last grid point, knot, cell, row, species, surface, harmonic, energy bin, or time step;
- 0-based/1-based conversion, ghost slots, periodic wrap, reflected index, and inactive extent;
- scalar versus broadcast array, singleton axes, empty active window, and smallest legal shape;
- singular/near-singular denominators, resonance/pole neighborhoods, and normalization floors;
- initialization, first update, restart/continuation, convergence threshold, maximum iteration,
  and non-convergence;
- symmetry and deliberately broken symmetry;
- missing/invalid external table identity, out-of-domain lookup, and threshold table switch;
- finite/nonfinite rejection and source-side semantic failure markers.

Do not add artificial epsilon, clamping, wrapping, extrapolation, or default state merely to make a
boundary case run. Preserve the source behavior and classify the failure.

## Mapping-specific coverage

### Matrix, row, and RHS producers

Partition by row family, boundary priority, column-width/stencil kind, storage mode, normalization,
RHS ownership, index base, active extent, ghost/periodic mapping, and scatter/gather path. Compare
row identity, columns, coefficients, RHS, and final assembled residual. A collection of explicit
rows does not prove the source-state-to-row producer.

### Iterative and time-dependent paths

Capture initial state, first transition, ordinary transition, branch-changing transition, terminal
transition, non-convergence/maximum-step behavior, and restart state. Each step must consume the
actual previous output. Keep diagnostics observer-only unless the source explicitly feeds them back.

### Stochastic paths

Separate RNG recurrence/continuation, sampling transform, event acceptance, state transition,
deposition, and reduction. Capture supplied or generated random values and final RNG state. Use
independent moment/statistical bounds in addition to exact frozen-history replay. A finite prefix
does not prove the full event stream.

### Parallel paths

First close a deterministic serial or fixed-event-order mapping. Then capture rank/thread ownership,
partition map, event order, reduction tree/order, and synchronization points. If the source does not
define a unique schedule or reads uninitialized shared state, retain a runtime/oracle boundary;
repeated outputs are observations, not a universal parallel contract.

When the source has no legal one-rank execution, preserve its explicit rejection as an
`expected_failure`; do not substitute an archived or separately compiled serial output as the MPI
control. Compare at least two legal rank counts using the same newly built executable, fixed input,
and preserved terminal fields. Require matching variable identity, shape, dtype and finite mask;
report rather than hide last-bit differences limited to declared floating reductions. Treat process
partitioning and collectives as runtime glue unless a scientific consumer cannot receive an explicit,
surface/event-indexed payload. Do not promote a scheduler trace itself into a scientific asset.

### Tables and external data

Cover table identity, axes, units, interpolation knots, endpoints, out-of-domain policy, floors,
signs, and physical selector transitions. If synthetic table values are used, they validate loader
and numerical behavior only. Do not claim fidelity to an unavailable physical database.

### Geometry and coordinate transforms

Capture the initialized basis/origin/frame, transform order, selected interpolation cell, axis and
index conventions, on-axis/near-axis behavior, inside/outside boundaries, and orientation/sign
changes. Probe the real consumer path rather than an isolated helper in a default frame.

## Holdout selection

Choose holdout cases after the partition plan but before implementing the candidate relation. Use
different numeric values and, where possible, a different legal grid/shape while preserving the
same declared mapping. Do not choose only random interior cases; include at least one material
boundary or state-transition holdout for fragile mappings.

Freeze the implementation hash and tolerance before revealing holdout target outputs. If the
implementation or tolerance changes, retire that holdout result and generate a new case.

## Coverage status

- `covered`: genuine source branch entered, required state captured, semantic status known, and
  replay/oracle usable;
- `partial`: branch entered but one required field, terminal record, or independent oracle is absent;
- `blocked`: source cannot reach stable capture without new input, external state, or runtime change;
- `inapplicable`: partition is outside the declared source input domain, with reason.

Never convert `partial` or `blocked` to `covered` from a plausible final output or inferred array
shape.
