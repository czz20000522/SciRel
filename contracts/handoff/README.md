# Handoff layer packages

## The whole chain

```text
external owners (independent)                 SciRel receiver                 user
D0 freeze -> D1 extract -> D2 claims -> D3 delivery
      isolated packages, each binds its parent digest
                                   -> admission gate (structure only)
                                   -> per-capability disposition
                                      existing -> record, do not import
                                      partial  -> merge into existing asset
                                      new      -> rename/relocate/add contract
                                   -> library triad: implementation + tests + contract
                                   -> derived bilingual manual (zh/en)
                                                                    -> installable
                                                                       package + docs
```

The user is the last layer and sees only a SciPy-like package: importable
functions, tests, and a bilingual manual. Decomposition, delivery and merge
records never enter the user-facing surface. SciRel does not own or prescribe
how the external chain is executed; it prescribes what each layer **hands over**,
how the packages interlock, and how the receiver reviews them.

## Independent packages, one interlock

Each layer is its own package with its own schema and version:

| layer | schema | owner delivers |
| --- | --- | --- |
| D0 | `d0-package.schema.json` | frozen source identity, digest, delta, retained/excluded scope, licence notices |
| D1 | `d1-package.schema.json` | callable package digest, declared denominator, source issues, coverage/`NOT_RUN` |
| D2 | `d2-package.schema.json` | claim packets, assumptions/boundaries/failure/oracle, evidence gaps |
| D3 | `d3-package.schema.json` | asset documents, source-free implementation, tests, evidence, runtime closure, application evidence |

The only cross-layer contract is `parent_handoff`:

```json
"parent_handoff": {
  "layer": "d2",
  "package_id": "acme-plasma-d2",
  "payload_digest": "<sha256 of the parent payload>",
  "schema_version": "1.0"
}
```

D0 declares `"parent_handoff": null`. A package never embeds the parent's
method or internals; it only binds the exact parent bytes it consumed.

## Package layout

```text
<package_root>/
  handoff.json            # the manifest validated against the layer schema
  <payload artifacts>     # any layout; every artifact is listed in the manifest
```

`declarations.artifacts` lists every payload file with its sha256. The manifest
digest is computed from those entries:

```text
sha256(concat(sort_by_path("sha256  path\n")))
```

`scripts/validate_handoff.py <package_root> --layer d3 [--parent-dir <d2_root>]`
checks the layer schema, artifact digests, payload digest, licence notices and,
when `--parent-dir` is given, the exact parent binding. It never inspects how
the producer worked.

## D3 admission gate (is the package reviewable?)

A D3 package is admitted to review only when:

1. the D3 schema passes and the declared parent chain is bound;
2. every asset contract parses as `scirel.asset-document` and its `asset_id`
   matches the delivery entry;
3. implementation, test and evidence paths exist; tests are runnable;
4. `example_policy` is explicit (`execute` or `declared_not_run`);
5. runtime closure and licence notices are declared; `application_evidence`
   contains no declared `fail` case;
6. `declarations.not_run` and `claim_ceiling` are truthful.

Admission is not acceptance into the library.

## Capability disposition (receiver-side, per asset)

Each delivered capability is compared with the current catalog, one asset at a
time, by an agent/reviewer. The outcome is one of:

| disposition | meaning | receiver action |
| --- | --- | --- |
| `existing` | the library already provides this capability | record the duplicate and the matching asset(s); do not import |
| `partial` | the library covers part of the capability; a merge is worthwhile **only when the delivery extends capability** (new boundary, edge case, port, semantics, accuracy or coverage) | if `capability_gain.extends=true`, merge into the existing asset; if false, record the overlap like a duplicate and **do not change the library** |
| `new` | the library has no counterpart | rename into the library namespace, relocate implementation/tests, add the contract, then regenerate the Chinese reader, manual projections and evidence bindings |

This comparison is scientific judgment, not a mechanical diff: relation
identity, ports, units, axes, applicability, failure semantics and test evidence
all matter. It is intentionally not automated. The review record for each asset
should state the disposition, matched existing asset IDs, the overlap and the
differences, the required changes, and the evidence behind the decision.

A convention-only difference (different units, weights, names or failure wording
with the same numerical relation and no new coverage) is **not** a capability
gain. Such a delivery is recorded as `capability_gain.extends=false` and does
not change the library, even if its disposition is `partial`. Only a declared
extension makes a partial merge meaningful.

Only `partial` and `new` dispositions lead to code or contract changes in the
library; `existing` deliveries stay outside the repository.

The review itself is a durable record (`disposition.schema.json`), not an
automatic merge:

```json
{
 "schema": "scirel.disposition-review",
 "package": {"package_id": "...", "payload_digest": "...", "layer": "d3"},
 "reviewer_role": "...",
 "summary": {"existing": 1, "partial": 1, "new": 1},
 "dispositions": [
  {"incoming_asset_id": "...", "disposition": "existing",
   "matched_asset_ids": ["scirel.field...."], "overlap": "...",
   "differences": [], "required_changes": [], "evidence": ["..."], "notes": "..."}
 ]
}
```

`scripts/validate_disposition.py review.json --package-dir <d3>` checks the
record shape, the `existing`/`partial`/`new` rules and the binding to the exact
D3 package bytes. It checks the record, not the scientific judgment.

## Versioning

Each layer schema and package carries `schema_version` (semantic version).
A layer owner may evolve its package without touching other layers. A parent
reference binds `schema_version` and `payload_digest`, so an incompatible
successor is rejected rather than silently accepted.
