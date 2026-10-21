> Meta-rules for recording, reviewing and handing off work: [`../RULES.md`](../RULES.md).

# Asset contracts: single truth, audit and change rules

Every public capability is defined by one `catalog/examples/<asset-id>.json`
(`scirel.asset-document`). The contract is the public truth for ports, units,
axes, state/order, failure semantics, applicability and examples. The
implementation must satisfy it; tests, API pages, user-guide chapters and the
capability matrix are projections of the same truth.

Any agent changing a capability must read this file first.

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
