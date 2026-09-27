# Corrected-readings continuation of the dev39 synthesis/residual project

This is a third, staged user request on the **already two-review-assisted**
[synthesis-to-residual project](results-2026-09-27-synthesis-residual-forward.md),
not a fresh autonomous project. The user supplied
`input/measurements-update.csv`, correcting two readings, and asked for the
new signed residuals and unreduced chi-squared while keeping the earlier
prediction and comparison openable. The user also wanted later sheets to be
selectable without editing Python. The [manifest](manifests/2026-09-27-synthesis-residual-followup.json)
binds the exact request, corrected sheet, raw Claude trace and project archive.

The same unapproved SciRel `0.1.0.dev39` wheel (SHA-256
`be5a2a2b40461ded5c486d9c9689ceaaed987923b9ba428da73ab59ca1eef9b8`),
126/126 development catalog root
`sha256:434249fe5f6df457b712992182a0d5631918a1002861db9d415723fcd86e3fca`,
and four pinned skills were retained. A fresh Claude Code `2.1.281` session
`6f73b86f-24cf-4e39-a492-b68e87cb0f9c` ran without a token, time or call
limit. The CLI label was `claude-fable-5`; assistant events reported
`GLM-5.3-Flash`, so underlying model identity remains unconfirmed.

The first Claude invocation misread an absolute `D:` working path as `C:` and
received read-permission denials, then recovered by using relative paths. It
edited the project, but the evaluator's `acceptEdits` setting denied every
command, including `python -V`; its first final answer correctly said tests
and the ordinary entrypoint had **not** run. The evaluator changed only the
isolated session's execution permission and resumed the **same** conversation,
without supplying a scientific result or code patch. Claude then ran its
tests. Two new assertions initially failed because they demanded 12 decimal
places from a ten-significant-digit CSV field; Claude corrected those test
tolerances and reran. These failures and the permission rescue remain in the
single raw trace. This is environment-assisted continuation, not a fully
unassisted first-pass result.

The ordinary `run_comparison.py` now reads path defaults from `config.json`;
command-line path flags still override them. It selected the corrected sheet,
called the existing SciRel TaskGraph and residual Operator, and wrote six
compared rows plus one `out_of_grid` exclusion. The two changed signed
residuals are alpha `psi: 1 -> 1.25` and beta `p_perp: 0.5 -> 0.1666666667`;
the other four remain `0.3, -0.1, -0.5, -1`. Unreduced chi-squared changed
from `2.6` to `2.940277777777781`. The earlier two-point CSV and original
comparison CSV/summary remain separate, with original SHA-256 values
`964028fd...8bd148f`, `801a7fec...0bce954`, and `49aadd41...8f05c022`.

Independent verification ran the project **outside** the SciRel checkout.
`python -I` imported `0.1.0.dev39` from the new venv's `site-packages`;
`python -I -m pytest -q tests` passed **32/32**. The saved state, point table
and original measurement sheet still match the parent manifest's digests.
An independent arithmetic check used the unchanged raw-grid predictions and
corrected observations to obtain `chi2=2.94027777777778`, confirmed only the
two expected rows changed, and kept gamma unscored. A second ordinary
entrypoint run returned 0 and left the five checked old/current result files
byte-identical. The archived original comparison CSV and summary match the
pre-continuation bytes exactly, not merely their numbers.
An independent CLI override sent `--measurements input/measurements.csv` and
all three output paths to a separate directory while `config.json` still
selected the corrected sheet. It returned `chi2=2.6`; its comparison CSV and
summary matched the original archived bytes exactly, while the corrected
root outputs kept their digests. This verifies the alternate-sheet route
without changing Python or the delivered files.

The final [project archive](../../../build/verification/synthesis-residual-followup-20260927/stage3-corrected-readings.tgz)
has SHA-256 `bb79f926635c611bf9e836d2e197ae31e95e5a608f5183342855c03174e351a2`;
the [raw Claude trace](../../../build/verification/synthesis-residual-followup-20260927/claude-session.jsonl)
has SHA-256 `99c23e8ae09a0c0a58c33529456d095f0a9c49895c6592e25bcba6852818b5f6`.
The original manifest miscopied one character in the archived
`input/measurements-update.csv` SHA-256. The [identity correction](manifests/2026-09-27-synthesis-residual-followup-identity-correction.json)
retains the original manifest and binds the correct archive-member digest
`ac1cdf522c25d7e4b98710a691233a11ae3bf8bcdd0b2ebe7223c3fbd0bce954`;
this changes no input or result bytes.
The archive excludes the generated venv; reproducing runtime checks requires
installing the exact wheel. Its venv reused host scientific dependencies,
so this is not an offline dependency-install proof. Examiner and solver
directories were not OS-isolated. The project preserves the *specified*
old comparison but does not automatically version every future changed-sheet
result or transact across all output files. Neither the synthetic state nor
its readings are a validated physical equilibrium, expert-approved asset or
public v1 release.
