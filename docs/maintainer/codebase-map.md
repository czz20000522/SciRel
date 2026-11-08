# Current codebase maintainer map

This map is an orientation aid, not a second source of truth: the implementation
is the truth, contracts are its derived record, and documentation derives from
the contracts. The contracts in
`catalog/examples/` own scientific behavior; this page shows where to read and
how the layers connect.

## Snapshot

- Captured on 2026-11-05 from the tree immediately after `029aac0b`.
- Source: 224 Python files, about 29,900 lines, across 19 public scientific
  namespaces.
- Tests: 253 `test_*.py` files, about 36,900 lines.
- Public API inventory: 251 non-module names, made up of 214 functions,
  36 classes and one data value. The inventory also exposes 19 public modules.
- Contracts: 256 exposed contracts and 5 held contracts under
  `catalog/review/`.
- Review decisions: 49 `pass`, 207 `pass-with-limits`, and 5 `human-review`.
- Composition contracts: 22 exposed contracts carry an explicit composition
  graph.
- Every count above is structural. It does not establish complete scientific
  review or coverage.

Refresh the structural inventory from the local container:

```sh
python3 scripts/dev_container.py shell
python -B skills/development/api-design-method/scripts/api_inventory.py scirel --src src --json \
  > /tmp/api-inventory.json
python -B scripts/build_capability_matrix.py \
  --catalog catalog/examples --output /tmp/capability-matrix
```

## What the project is

SciRel is a pre-release Python library of reusable scientific relations. Public
functions use ordinary Python call signatures and return NumPy/pathlib-compatible
values. Importing `scirel` itself is lazy: it does not load the scientific
backends.

The repository separates three responsibilities:

```text
source line       source behavior -> self-contained candidate packet
maintenance line  candidate packet -> public contract + implementation + tests
outbound line     user requirement + public package -> user-owned program/result
```

The boundary and information rules are canonical in
[`ARCHITECTURE.md`](../../ARCHITECTURE.md) and [`RULES.md`](../../RULES.md).
External evidence, extraction history and reference answers must not become
runtime dependencies of the public package.

## The main chain

```text
catalog/examples/<asset>.json       derived contract: model, ports, limits, evidence
        |
        +--> src/scirel/<domain>/   implementation and public lazy exports
        +--> tests/<domain>/        direct numerical and failure tests
        +--> tools/docs/            generated API pages and authored bilingual guides
        +--> discovery/query tools  derived capability index and search cards
```

The contract's `verification.tests` list binds the asset to its tests and the
`public_api.python` block binds it to the implementation. Do not infer any of
those facts from file names alone.

When code and contract disagree:

1. fix the code when the contract states a scientific convention, public promise
   or fail-closed behavior;
2. fix the contract and every derived projection when the contract is stale;
3. never leave two live answers or add a compatibility alias.

Read [`catalog/README.md`](../../catalog/README.md) before changing any asset.

## Scientific areas

The package is broad, but the maintenance surface clusters into these areas:

| Area | Public names | Exposed contracts | Review shape | Start with |
| --- | ---: | ---: | --- | --- |
| Geometry, numerics and finite volumes | 57 | 52 | 13 pass, 39 pass-with-limits | `geometry/`, `numerics/`, `fvm/`; field lines, meshes, interpolation, basis functions and conservative operators |
| Fields, coils and device configurations | 25 | 24 | 12 pass, 12 pass-with-limits | `field/`, `electromagnetism/`, `configurations/`; Green responses, filament/coil geometry and WHAM/BRB/TREX data |
| Equilibrium and closure relations | 22 | 21 | 21 pass-with-limits | `equilibrium/`, `closures/`; Grad-Shafranov/Picard steps, pressure flux, ambipolar and quasineutral closures |
| Kinetic and neutral transport | 94 | 112 | 7 pass, 105 pass-with-limits | `kinetic/`; waves, spectral solvers, generalized dispersion, Vlasov-Poisson, mirror and neutral transport |
| Collisions and atomic data | 22 | 20 | 1 pass, 19 pass-with-limits | `collisions/`; hydrogen cross-sections, reaction rates, collision matrices and stopping increments |
| Diagnostics and inference | 10 | 10 | 6 pass, 4 pass-with-limits | `diagnostics/`, `inference/`; residual diagnostics, stability margins and bounded anisotropic inference |
| Physics, neoclassical, fusion, plasma and dielectric | 13 | 11 | 5 pass, 6 pass-with-limits | `physics/`, `neoclassical/`, `fusion/`, `plasma/`, `dielectric/`; small algebraic relations and bounded model assemblies |
| I/O and source profiles | 8 | 6 | 5 pass, 1 pass-with-limits | `io/`, `source/`; EQDSK/GEQDSK interchange and normalized 1-D profiles |

The public-name and contract counts do not have to match one-for-one. A contract
can bind a canonical package export to a child implementation; that relationship
is defined by `public_api.python` and `public_api.python.canonical_*`.

### Kinetic is the largest and first maintenance boundary

`kinetic/` contains roughly half the source lines and 94 public names. Treat its
subareas as separate reading units:

- dispersion and root finding;
- generalized dispersion, Faddeeva/GPDF and Vlasov-Poisson;
- fluid spectra and modal evolution;
- mirror/kinetic closures and pressure moments;
- neutral generation, mesh interpolation and transport;
- terminal moment reductions;
- Frank-Egedal pressure-state relations.

Do not rename or regroup these modules until the API issues have been narrowed.
The planned kinetic split in issue #8 is a large structural batch, not a starter
task.

## Review-stage work

`pass-with-limits` in a contract means the result has explicit evidence
boundaries; it is not a synonym for a known wrong answer.

Five contracts under `catalog/review/examples/` are not part of the public
catalog: their implementations are not in `src/`, so they are neither packaged,
documented, indexed nor counted by the capability matrix. They stay readable as
review input and are promoted by moving the contract into `catalog/examples/`
once its implementation lands:

- `scirel.equilibrium.finite-frc-feedback`
- `scirel.equilibrium.finite-limited-boundary`
- `scirel.inference.direct-anisotropic-inversion`
- `scirel.kinetic.atomic-slab-transport`
- `scirel.kinetic.multiscale-sat123`

## Public API signals that need work

The API inventory is a review prompt, not a defect verdict. Current signals:

- 13 public callables still take an `inputs` mapping.
- 5 public callables still take a `params` mapping, and one takes a `case`
  mapping.
- 23 public callables or classes show `**kwargs` interface flags.
- 7 public kinetic functions have no docstring in the inventory.
- The hazard baseline has 182 accepted hits. Most are 82 ignored error states, 38
  clips, 37 `**kwargs` signals, 8 mapping defaults and 7 conditional zeroing
  paths. Each still needs contextual review before being called correct.

These signals explain issues #1, #2, #3 and #6. Do not change scientific results
while addressing them. Keep formatting and API-shape changes separate from
physics changes.

## Cross-domain compositions

There are 22 composition contracts. They are the bridge between reusable
operators and bounded end-to-end scientific tasks. Read the graph nodes and
edges in the contract before reading the implementation. The graph records
ordering, branching, state transitions, convergence and controlled glue.

Representative entry points:

- `scirel.equilibrium.axisymmetric-anisotropic-picard`
- `scirel.equilibrium.free-boundary-anisotropic-picard`
- `scirel.field.multi-coil-vacuum-field`
- `scirel.geometry.axisymmetric-equilibrium-grid-support`
- `scirel.kinetic.generalized-root-scans`
- `scirel.kinetic.vp-landau`
- `scirel.kinetic.kinetic-dispersion-relation`
- `scirel.closures.mirror-quasineutral-closure`

Compositions inherit the contracts of their member operators. A composition
pass is not evidence that every possible user task is covered.

## Review, docs and delivery

- `catalog/examples/` is the public contract set.
- `catalog/review/` contains held contracts, candidate code and the verdict
  registry; it is not installed.
- `tools/docs/manual/` contains authored bilingual user guides.
- `tools/docs/zh/*.json` contains Chinese reader records bound to contract bytes.
- `src/scirel/_result.py` defines the named `Result` mapping used by public
  multi-value returns.
- `scripts/build_capability_matrix.py`, `scripts/capability_query.py` and
  `scripts/scirel_docs.py` derive discovery and documentation projections.
- `skills/development/usage/` contains the three delivered consumer skills.

Generated pages, indices and matrices are not reviewed science by themselves.

## Suggested work order

The current open issues are not all equally urgent. Use this order unless new
evidence changes the harm or reach:

1. **Issue #11** — stop returning a misleading H charge-exchange value above
   20 keV. This is a known wrong-result path.
2. **Issue #10** — decide the remaining reproduced physics/accuracy limits and
   record the applicable range or fail-closed behavior.
3. **Issue #7** — close reproduced validation/documentation gaps with tests
   before changing prose.
4. **Issues #2 and #3** — return named results and make public inputs explicit.
   Split these into small reviewable batches.
5. **Issue #1** — complete docstrings and extend the docstring/contract sync
   check for each newly covered asset.
6. **Issues #4, #5 and #6** — private helper naming, formatting/lint and hazard
   baseline review. Keep formatting separate from behavior.
7. **Issue #8** — split `kinetic` by physics only after the API and naming
   batches have stabilized.
8. **Issue #15** — update GitHub Action runtime versions as a low-risk CI
   maintenance task.

Issue #9 is the tracking issue for API/style priority. Issue #14 is this map.
The order is a recommendation, not a waiver of the issue-specific method or
acceptance rules.

## Reading a capability safely

For any one asset, use this sequence:

1. Read the complete contract and its `verification` block.
2. Read the implementation and public export binding.
3. Read every test path named by `verification.tests`.
4. Read the Chinese reader and generated/API documentation if they exist.
5. Run the direct test and the contract example.
6. Run the affected domain or cross-domain check before the full local check.

Do not infer behavior from a function name, a generated page, a test name or a
single successful numerical example.

## Evidence boundary

This map was built from repository structure, public API introspection, contract
metadata, review status, authored documentation and the open issue queue. The
local full acceptance check establishes structural and regression health. It
does not independently validate every scientific formula, every stated physical
domain or the rights of all source material.

NOT_RUN for this map: independent scientific review of all 256 exposed
contracts, manual review of every generated API page, and reference-answer
parity for the systems outside the public package.
