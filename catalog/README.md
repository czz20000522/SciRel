> Meta-rules for recording, reviewing and handing off work: [`../RULES.md`](../RULES.md).

# Asset contracts: single truth, audit and change rules

Every public capability is defined by one `catalog/examples/<asset-id>.json`
(`scirel.asset-document`). The contract is the public truth for ports, units,
axes, state/order, failure semantics, applicability and examples. The
implementation must satisfy it; tests, API pages, user-guide chapters and the
capability matrix are projections of the same truth.

The project-level boundary between source behavior graphs, public composition
graphs and user-owned outbound task graphs is defined in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md). The `composition` field below is a
public SciReL composition contract; it is not an automatic copy of a source
project's task graph and it does not describe a user's private program.

Any agent changing a capability must read this file first.

## Review status

Each contract has one status in `catalog/review/VERDICTS.json`.
`scripts/review_gate.py --check` confirms that the registry and the catalog agree;
it checks structure only and makes no scientific claim. Human review decides the
status. See [`AUDIT.md`](AUDIT.md).

## One truth, no silent divergence

When contract and implementation disagree, choose one truth explicitly and
record the decision in the change:

1. If the contract encodes a scientific convention, a fail-closed requirement
   or a public promise, fix the implementation and add a regression test.
2. If the contract is stale, template-copied, or contradicts observed
   implementation/tests, fix the contract and the derived API/reader text; add
   a test if the behavior was previously untested.
3. Never leave both versions alive, never add a compatibility alias, and never
   let generated pages continue to state a behavior the code does not have.

Do not "fix" a behavior by only editing the Chinese translation. If the API
page is wrong because the contract is wrong, the contract is the thing to fix.

## Asset triad and projections

- implementation: `src/scirel/...`
- direct tests: `tests/<domain>/...` (bound through `verification.tests`)
- contract: `catalog/examples/...`
- projections: API reference pages, user-guide links, capability matrix

A behavior change updates all four layers; a contract-only metadata fix still
requires rebinding `tools/docs/zh/*.json`, docs execution evidence and running
the docs tests.

## Bilingual rules

- English contract fields (`title.en`, `summary`, `identity`, ports,
  `failure_semantics`, `applicability`, `verification`, `example`) must be
  English prose. Do not leave Chinese prose in an English page.
- `tools/docs/zh/*.json` is the Chinese reader layer: Chinese prose, but port
  names/order and clause counts must match the contract exactly.
- A Chinese page must not be an English contract dump; an English page must not
  retain Chinese contract prose. Symbols, formulas and identifiers are the only
  acceptable shared tokens.
- Every translated page is manually reviewed; generation + schema validation is
  not linguistic or scientific review.

## Required checks before accepting a contract change

```bash
.venv/bin/python scripts/validate_asset_documents.py catalog/examples
.venv/bin/python -m pytest -q tests/docs
.venv/bin/python scripts/build_capability_matrix.py --output /tmp/capability-matrix
```

Also run the direct tests listed in `verification.tests`, and execute the
contract example. If the contract has an API-reference page, inspect it after
rebuilding docs; do not accept "the generator ran" as review.

## Known contract-audit decisions

- Contract fields are English; Chinese only in reader sidecars.
- Examples must reflect the example code actually executed, not an intended or
  imagined stronger claim.
- Template-copied failure/boundary text must be replaced with function-specific
  text or a truthful "not computed/unsupported" statement.
- `rcond` is relative to the largest singular value; non-finite rotate inputs
  are rejected; these implementation choices are contract truths with tests.

## Capability discovery metadata and intake ownership

A contract must let a consumer **find and select** a capability, not only call it.
The discovery view uses nine fields. `ports` and `evidence` are deterministic
projections of `inputs`/`outputs` and `verification` and are deliberately **not**
stored in the contract; six reviewed fields are carried by the optional top-level
`discovery` block, and `aliases` stays the existing top-level list. Public and held
contracts normally carry this block. Its presence is
not a scientific approval or a generic-device claim.
The `asset_id` stays the only stable key, and `taxonomy` stays browsing
classification: this section defines how to read the contract, it does not create a
second one.

The `discovery` block is optional; its fields are independently optional so an
intake review can record `device_scope` before it authors the prose:

- `capability`, `operation`: non-empty arrays of strings (reusable short name plus
  one-line summary; relation plus input→output direction).
- `model`, `geometry`, `boundary`: strings; same meaning as the table below.
- `device_scope`: one of `generic`, `device-parameterized`, `device-bound`,
  `unclassified`. Absent means `unclassified`, never `generic`.

The schema file is `contracts/scientific-asset-document.schema.json`; the exact-key
validator in `scripts/validate_asset_documents.py` is the executable gate. Discovery
must never gain `ports` or `evidence` copies.

| discovery field | contract source | rule |
| --- | --- | --- |
| `capability` | `title.en`, `summary` | reusable noun phrase; not the symbol, not a domain, no quality claims |
| `operation` | `identity.relation`, `identity.direction` | what is done and input→output direction; never a title restatement |
| `model` | `identity.model` | equation/approximation and its level (analytic, empirical fit, iteration, interpolation) |
| `geometry` | `identity.geometry`, `identity.coordinates` | axes, order, grid, units; state what is *not* reconstructed |
| `boundary` | `identity.boundary`, `preconditions`/`excluded` | domain edges, boundary values, extrapolation or clamping; no invented support |
| `device_scope` | `discovery.device_scope` (optional; absent means `unclassified`) | `generic`, `device-parameterized`, `device-bound` or `unclassified` |
| `ports` | `inputs`, `outputs` | `name`/`units`/`shape`/`required`/`default`/`constraints`; structural match key |
| `aliases` | `aliases` | recall synonyms, legacy symbols, device names only when truly bound |
| `evidence` | `verification.*` plus intake decision | verified scope, tests, ceiling, limitations and status |

`evidence.status` is one of `bounded`, `partial`, `unvalidated`,
`needs-device-binding`. `bounded` is the normal catalog status and never means
"generally correct": always read it together with `evidence_ceiling`. A candidate
without a direct test or independent oracle is `unvalidated`; a capability that
needs named-device constants but has no device evidence is `needs-device-binding`.
Neither may appear in `applicability.supported` as a generic claim. Unvalidated
candidates may be kept in a submission, but they must not be published as callable
catalog assets.

### Device scope

- `generic`: model-level relation, no built-in named-device constants. Device names
  must not appear in `capability`, `identity.relation`, `identity.model` or
  `supported`.
- `device-parameterized`: accepts device-relevant parameters but ships no named
  device constants.
- `device-bound`: ships fixed named-device geometry/constants or is evidenced only
  on one device. It must list the device name and binding evidence, and it must not
  be described as generic.
- `unclassified`: no device-scope review has been recorded. It is the only safe
  default for an unreviewed asset and must not be treated as `generic`.

A device name is an alias and an applicability filter, never a retrieval primary
key: it may appear in `aliases`, must not enter the `asset_id` of a reusable kernel,
and must not boost or outweigh a ports/model match. `device_scope` records only the
binding level; the named device and its binding evidence stay in the contract text
and tests.

The schema carries `discovery.device_scope` directly; no external table is needed.
An absent `discovery.device_scope` still means `unclassified`, never `generic`.
Count the current classification with `scripts/scirel_docs.py query` rather than recording it here.

### Ownership and information boundary

The decomposition side submits only a candidate: neutral description, model,
geometry, boundary, ports, raw correctness evidence and unknowns. It does not write
`asset_id`, SciRel `taxonomy`, final `aliases`, a `device_scope` decision or any
acceptance conclusion. The SciRel intake owner is the sole author of the contract
discovery fields, the `evidence.status` decision, the overlap record
(`contracts/reception/`) and the generated discovery projection. Intake must not
ask a decomposition worker for receiver-side tags, search keywords or device-scope
judgements.

### Retrieval order

1. Grep/full-text over contracts and the documentation snapshot `search_text`
   (currently the contract plus its Chinese sidecar). Use synonyms, symbols and
   Chinese/English terms.
2. Browse filters: domain, taxonomy, handbook topic, asset kind.
3. Read the exact contract. Applicability is decided by ports, units, model,
   geometry, boundary, device scope and evidence — never by a name.
4. A structured index is a **build artifact generated from contracts** (source
   revision bound, diffable, not committed, never hand-edited). The schema's optional
   `discovery` block carries the reviewed discovery fields, while `ports` and
   `evidence` stay derived. Never hand-maintain the index or a second alias table.
5. A device-name hit only prompts a device-scope/evidence check; a zero grep hit
   does not establish a capability gap.

Before accepting a discovery metadata change, run the checks above and verify:
`capability` derived and unique; `operation` not a title copy; `model` states its
approximation level; `geometry` states axes/units and non-goals; `boundary` states
edge conventions; `device_scope` consistent with devices and evidence; device names
absent from reusable-kernel IDs and from `supported`; aliases unique and free of
claims/other asset titles/source identity; ports match the runtime signature;
`evidence` status matches tests and ceiling; no unvalidated claim in `supported`;
and the projection regenerates identically from the contract (no second truth, no
hand-maintained index or alias table).
