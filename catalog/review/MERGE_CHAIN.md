# Merge chain protocol

Status: held code and contracts live in the review tree and are absent from the
installed package. `HOLD.json` lists what is held. `SCIREL_REVIEW_HOLD` is only the
review-harness switch, not a containment boundary.

## Candidate layout

```text
catalog/review/
  candidates/       candidate code, never installed
  examples/         held contracts
  HOLD.json         what is held and why
  VERDICTS.json     one status per asset
```

## Merge order

1. Freeze the candidate and its evidence.
2. Resolve the dependency closure: contract dependencies + Python imports.
3. Run the closure in the review harness (contract, tests, examples, docs,
   adversarial probes, import surface).
4. Record the verdict. Any disagreement or human-owned decision keeps the whole
   closure staged.
5. Merge leaves first, then compositions. Regenerate exports/docs from the
   admitted manifest and run the closure again.
6. Do not delete the staged copy until the merged closure is green.

## Why a "guard" is not enough

A runtime import guard can be bypassed by direct module import, vendored code,
pickle/import hooks or packaging mistakes. Only omission from the installed
package and public manifest proves non-exposure. The guard remains only while
the quarantine refactor is in progress.
