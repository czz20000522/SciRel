# Receipt anchors

One JSON file per green acceptance run. The full receipt (a few megabytes of per-test records)
is written to `.runtime/logs/check-<id>/`, which is gitignored, so it does not survive a cleaned
worktree; the anchor is the part that stays. It is small enough to commit and specific enough
that a rerun on the same revision can be reconciled with it.

An anchor proves **which run this was**, not that the run was correct. It records no verdict of
its own: `verify` answers "does this receipt agree with this anchor", never "is this acceptance
good".

## What a file records

| Field | Meaning |
| --- | --- |
| `schema` | `scirel.acceptance.anchor.v1` |
| `stage` | `release` or `dev`; the two stages select different tests, so each has its own floor |
| `checked_at` | UTC timestamp, used only to pick the newest anchor as the selection floor |
| `candidate` | `commit`, `tree`, `worktree_sha256`, `dirty` of the tree that was checked |
| `environment` | interpreter, platform, architecture, `numpy`/`scipy`/`mpmath` versions, and the digests of `uv.lock` and `.python-version` |
| `provenance` | digests of `check_all.py` and `scirel_pytest_counts.py`, i.e. the scripts that wrote the receipt |
| `receipt` | the receipt's own `result_sha256`, its `run_id`, and its evidence class |
| `tests` | the nine counts, plus `nodeid_set_sha256` and `per_test_sha256` |
| `skip_reasons`, `xfail_reasons` | reason string to number of tests, so a reader sees why without the receipt |
| `normalization` | the exact rules below, copied into every file |

The 8,000-odd nodeids are **not** stored. What is stored is a digest over them, which costs
nothing and still lets a rerun prove it ran the same set.

## Digest rules

Both digests are computed over nodeids exactly as the counts plugin recorded them, normalised
this way and no other:

- every backslash becomes `/` (a Windows run and a POSIX run must produce the same digest);
- a leading `./` is removed;
- nothing else changes: the path stays repository-relative (no drive letter, no absolute
  prefix), the `::` separators stay, and a parametrised id keeps its `[param]` suffix verbatim.

`nodeid_set_sha256` is the SHA-256 of the normalised selected nodeids, sorted with Python's
`sorted()` (code-point order, locale-free), joined by `\n`, with one trailing `\n`. Duplicates are
not collapsed; the counts validator already refuses a selected list that contains them.

`per_test_sha256` is the SHA-256 of one JSON array per test — `[nodeid, outcome, reason]`,
serialised with `separators=(",", ":")` and `ensure_ascii=False` — ordered by normalised nodeid,
joined by `\n`, with one trailing `\n`. `reason` is the phase's `wasxfail` when present, else the
phase's skip reason, else an empty string.

## Writing and checking an anchor

Both commands are read-only with respect to the repository except for the file `export` writes.
Neither starts a test and neither holds the acceptance lock; they are not a second entry point.

```sh
python3 scripts/dev.py run python -B \
    skills/development/scirel-acceptance/scripts/acceptance_anchor.py export <receipt.json> <anchor.json>
python3 scripts/dev.py run python -B \
    skills/development/scirel-acceptance/scripts/acceptance_anchor.py verify <anchor.json> <receipt.json>
```

`export` refuses a receipt that is not a complete, green run (`status: complete`, `exit_code: 0`,
no binding errors). `verify` prints `AGREEMENT  agree` or a `MISMATCH` line per disagreeing field,
and uses the exit status for agreement only: `0` agree, `1` disagree, `2` cannot check. It does
not print or imply a verdict on the acceptance run.

The receipt that `verify` reads must still be complete enough to recompute the digests; a receipt
copied without its sidecar is reported as `unprovenanced` in the output and compared anyway,
because a comparison is not a provenance claim.

## Why the newest anchor is a floor

`check_all.py` reads the newest anchor of the stage it is running and fails the tests step if the
run selected fewer tests than that anchor records. Re-anchoring is how a deliberate removal lowers
the floor, and that act is visible in the diff.

The reason is a specific observation, not caution in general: before the floor, a run of two
passing tests and a run of 8,347 passing tests produced the same verdict, because the counts were
checked for internal consistency and never against an expected value. Additions do not need a new
anchor (the count only grows); removals do.
