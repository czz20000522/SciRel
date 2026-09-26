# r64 test evidence — KN1DPy convergence/accumulation family

Base r63 `10e1ee1` (116 assets, dev37) -> r64 `0.1.0.dev38` (120 assets).
Four new operators: neutral generation stopping criterion, accumulation
state update, outer seed convergence, and top-level kn1d convergence.
Saved arms reproduced bit for bit on the declared domain. The r63 freeze
(`build/verification/review-2026-09-27-r63-transport-v11/`) is untouched.

## Shell record

All counted gates, builds and the freeze ran under pwsh 7.6.6 with
`PYTHONDONTWRITEBYTECODE=1` and explicit `PYTHONPATH` /
`SCIREL_KN1DPY_REVIEW_ROOT` set in-process. Saved-tree imports read-only;
zero writes.

## Test delta (collect-verified, pwsh 7)

- `test_convergence_accumulation.py`: 8 direct tests
- `test_convergence_accumulation_l1.py`: 5 environment-gated replay tests
- Total 13 new tests; `pytest --collect-only` verified (13 collected).
- Independent oracle: stopping ratio-of-max formula
  Delta_n = max(gen)/max(acc); accumulation accumulation totals
  total_dist = sum of generation distributions; outer-seed discriminating
  regression seed_error = max(abs(diff))/max(curr), not per-node division;
  outer-seed threshold = 10*truncate, kn1d threshold = truncate.
- Pre-review corrections: stopping returns a 3-tuple (delta, done, reason),
  not a mapping; accumulation requires `state` as a positional argument;
  discriminating regression for ratio-of-max vs per-node formula added.
- All examples exercise the actual callable with verified values.

## Gates (final bytes)

- Source-mode full gate: **1410 passed, 43 skipped, 0 failed** (r63: 1397;
  +13; log line `1410 passed, 43 skipped, 7 warnings in 215.43s`).
- Document validation, source state: **120/120**, `runtime_origin: source`,
  `examples_executed: true`.
- Same validator from the clean venv with `--installed-runtime`: **120/120**,
  `runtime_origin: installed`, `examples_executed: true`.
- Installed full tree: **1276 passed, 177 skipped, 0 failed**
  (`SCIREL_INSTALLED_RUNTIME=1`, `python -I -B -m pytest -q -o pythonpath=
  -p no:cacheprovider tests/`; log line `1276 passed, 177 skipped,
  7 warnings in 184.77s`).
- Catalog `build/catalog/r64`: `complete: 120/120`, root digest
  `sha256:9060cedfd46ba988125882757a078b6d7d965aff87fe79eb191f1dc50a17ae92`.
- Internal wheel `scirel-0.1.0.dev38-py3-none-any.whl`, SHA-256
  `a4d8042e0f49abc11483e6fbe0ee067cc7dc054618b887bffc68b11d773b683d`.
- Candidate review-material index: batch r63 added (9 entries) and batch
  r64 added, every entry resolves and matches its recorded SHA-256
  (script-verified).
