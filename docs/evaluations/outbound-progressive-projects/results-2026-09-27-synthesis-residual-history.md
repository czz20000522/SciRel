# Third readings sheet and result-history audit

This is the fourth staged request on the already two-review-assisted
[synthesis-to-residual project](results-2026-09-27-synthesis-residual-forward.md),
following the [first corrected sheet](results-2026-09-27-synthesis-residual-followup.md).
The user supplied `input/measurements-next.csv` and asked for all three
comparisons to remain openable, for later sheets to use the ordinary entrypoint,
and for unusable inputs to leave the last successful result intact. The
[manifest](manifests/2026-09-27-synthesis-residual-history.json) binds the exact
request, input, harness trace, review feedback and project archives.

The input was the same unapproved SciRel `0.1.0.dev39` wheel (SHA-256
`be5a2a2b40461ded5c486d9c9689ceaaed987923b9ba428da73ab59ca1eef9b8`),
126/126 development catalog and four pinned usage skills. Claude Code `2.1.281`
continued session `6f73b86f-24cf-4e39-a492-b68e87cb0f9c` without a call,
time or token limit. Its CLI model label was `claude-fable-5`, while assistant
events identified `GLM-5.3-Flash`; the underlying model is unconfirmed. The
evaluator and solver shared filesystem access, and the project is synthetic.

The **first autonomous fourth-turn delivery failed history protection** despite
reported 14+14+7 passing tests. The migrated original-sheet summary lacked
input digests. In an independent copy, changing only the original alpha psi
observation `2.5 -> 2.4` under the same filename let the ordinary entrypoint
exit 0, report `chi2=3.85`, and replace the original comparison CSV and summary.
The frozen first archive, raw trace prefix and replay are in
`build/verification/synthesis-residual-history-20260927/`.

After symptom-level feedback, Claude's first repair refused changed values
but inferred a historical input digest from equal output rows and chi-squared.
An unchanged original-sheet rerun then rewrote the delivered summary from
`49aadd41...` to `cdba6047...`. Output equality cannot prove input-byte
identity, so a second review rejected that repair. Claude removed the
backfill, restored the original summary byte-exact from the first frozen
archive, and made an ambiguous same-name legacy rerun fail closed. New
per-sheet archives with recorded digests remain idempotently rerunnable.
These are **two review repairs in this fourth turn**, on top of the earlier
project reviews; the final result is not autonomous history reliability.

An independent copy and a separate extraction of the final archive imported
the installed dev39 wheel from `site-packages`, not SciRel source. The extracted
project passed **38/38** tests and its ordinary `run_comparison.py` returned
0: six compared readings, one explicit `out_of_grid` exclusion and unreduced
`chi2=2.752777777777782`. The six displayed residuals are `1.25, 0.3, -0.1,
-0.25, -1, 0.1666666667`; their squared sum agrees to CSV precision. Both
old comparisons survived migration under per-sheet names with bytes matching
the stage-3 archive: original CSV/summary SHA-256 `801a7fec...02dc` /
`49aadd41...e9e`, first corrected `585cf93b...6f80` /
`6e6225ef...861c`.

In the independent copy, an unchanged original-sheet rerun exited **1**;
changing alpha psi to `2.4` at the same path also exited **1**. Each left the
two original archive files and both latest-result files byte-identical. After
restoring the input, the ordinary next-sheet rerun exited **0** and preserved
the original archive digests. The second-review archive is
`build/verification/synthesis-residual-history-20260927/stage4-second-review-final.tgz`
(SHA-256 `15924efa0495908baecbc2e6ff921404700ad8bc0ca9661e2f2c15e6ce7bf617`).
Final code review then corrected only a stale old-output path in the entrypoint
docstring; the frozen successor is `stage4-final-doc-corrected.tgz` (SHA-256
`9d7548d569ef0866da5f30613287a68c28878ab7e5607ceabfb26e5d1733ab24`).
The editorial correction was made by the evaluator, not Claude. The complete
Claude trace is `claude-session-final.jsonl` (SHA-256
`b2bf59c3587cc09aa86e4e505e81bd99ccf9d9a9d5a5b080928eda45811ac58b`).

The legacy original sheet now cannot be rerun under the same archive name
without independently establishing provenance and moving or renaming that
archive; the message explains why. Multiple output files are not written as
one transaction, so a mid-write I/O failure is not covered by this test.
The venv reused host scientific dependencies, not an offline dependency
install. Neither these synthetic scores nor the development asset versions
establish a physical equilibrium, expert approval, trusted release or public
v1. No SciRel-specific CodeFusion kernel change follows from this case.
