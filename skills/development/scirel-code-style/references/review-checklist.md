# Review a pull request

Judge the change as someone responsible for the library would: is a user who calls this function, knowing only what it documents, more likely to get a correct result than before? Read the diff, not just the description. Rerun what you doubt.

Send a PR back if any item below fails. Ask for the smallest fix, and say which item it fails.

## Evidence

- The PR pastes the end of `check_all.py`, run on the final commit, ending in `ALL GREEN`. There is no CI, so rerun it before merging anything that touches results.
- The issue's `Done when` is met, checked by you and not taken from the description.
- The scope lists only tighten: no asset left `contract_sync_scope.json`, and new `hazard_baseline.json` entries are each justified as documented behaviour.

## One source of truth

- The signature and docstring define parameter names, order, defaults, units, returns, raises and warnings. The contract is derived from them and agrees; `check_contract_sync.py` covers the asset.
- A fact appears in one place. Other places link to it or are checked against it, and nothing is restated by hand where it can drift.

## Docstrings

- Numpydoc layout as in SciPy: summary line, `Parameters`, `Returns`, then `Raises`, `Warns`, `Notes`, `References` and `Examples` where they apply.
- Every physical quantity has its unit. Every array has its shape.
- The docstring states the model, its valid range and what happens outside it.
- A citation from memory says so. The source of a formula can be found from what is written.

## Failing loudly

- Invalid input raises, naming the parameter and the value.
- A result outside the valid range raises or warns. A clamp, a fallback, or a flag that a caller can ignore must not return a wrong number without notice.
- `except Exception` has a comment saying why nothing narrower works, and does not turn a programming error into a result.
- No sentinel value or `NaN` stands in for a failure unless documented as the interface.

## Units and conventions

- Sign conventions, normalization, coordinates, and frequency versus angular frequency are stated.
- Input units are named in the parameter or stated in the docstring, and the code does not guess them from magnitude.
- A departure from a common convention or a source gives the conversion and the reason.

## Tests

- The expected value comes from outside the code under test: an analytic limit, a published number, or a different method. A number copied from the code's own output only pins behaviour, and has to say so.
- The test can fail: reverting the change or changing a factor of 2 makes it fail. Check one such case by hand.
- Tolerances come from an error estimate. No tolerance was widened and no assertion removed to pass.
- Failure paths are tested as well as the success path.

## Results and physics

- Interface and style changes leave every number the same.
- A result change is in its own commit, which gives the derivation or reference. It is not mixed with formatting or renames.
- Formulas, signs, units and numerical choices did not change without the maintainer's decision.

## What goes in the public repository

- Delivered skills under `skills/development/usage/` hold general method for any user's agent: no specific cases, numbers from them, or files of this repository.
- Nothing holds the answer to a specific question that the library will be used to solve: not tests, examples, skills, issues or PR text.
- No private paths, private repositories, personal notes, or secrets.
- Explanations are in commit messages. There are no change-log or hand-off files.
