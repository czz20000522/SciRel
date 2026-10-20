# Handoff layer packages

SciRel receives scientific capabilities from an external decomposition chain
(D0 source preparation -> D1 source-faithful extraction -> D2 correctness
decomposition -> D3 delivery). SciRel does not own or prescribe how that chain
is executed. It prescribes what each layer **hands over** and how the packages
interlock, so independent owners can deliver independently.

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
| `partial` | the library covers part of the capability or differs in ports, units, boundary or failure semantics | merge into the existing asset: reconcile contracts, tests and evidence; never add a second competing asset |
| `new` | the library has no counterpart | rename into the library namespace, relocate implementation/tests, add the contract, then regenerate the Chinese reader, manual projections and evidence bindings |

This comparison is scientific judgment, not a mechanical diff: relation
identity, ports, units, axes, applicability, failure semantics and test evidence
all matter. It is intentionally not automated. The review record for each asset
should state the disposition, matched existing asset IDs, the overlap and the
differences, the required changes, and the evidence behind the decision.

Only `partial` and `new` dispositions lead to code or contract changes in the
library; `existing` deliveries stay outside the repository.

## Versioning

Each layer schema and package carries `schema_version` (semantic version).
A layer owner may evolve its package without touching other layers. A parent
reference binds `schema_version` and `payload_digest`, so an incompatible
successor is rejected rather than silently accepted.
