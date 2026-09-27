# Balmer inversion and forward comparison: unseen staged project

This three-turn synthetic user project tested a different TaskGraph pair on
the unapproved SciRel `0.1.0.dev39` wheel and its complete 126/126 development
catalog. A fresh Claude Code `2.1.281` session first inverted Balmer-alpha
readings into ground-state neutral densities, then found and called the
forward-emission TaskGraph for a separate check sheet, then handled a revised
check sheet while retaining earlier results. The [manifest](manifests/2026-09-27-balmer-forward.json)
binds inputs, wheel, skill files, raw traces, first-pass archives, review and
final archive. The three requests and later sheets were fixed before solving
and exposed in sequence; examiner and solver still shared the host filesystem.
Claude's init event listed the four bundled SciRel skills, but none of the
four traces shows a `Skill` invocation or a read of their bodies. Their hashes
bind what was available, **not** observed method execution; this case cannot
serve as a same-method harness comparison.

Before feedback, the ordinary project produced the correct numerical rows for
this fixture: B1-B3 invert to approximately `1e16`, `2e16`, `3e16 m^-3`; B4
has no electron temperature and remains unavailable. The first check sheet's
forward comparison is approximately `+9.993%`, `-9.998%`, `+9.999%`; the
revised B2 becomes `+4.999%`. The agent used the selected SciRel inversion and
emission graphs rather than writing their scientific equations. It delivered
three distinct CSV/report pairs; the older pairs remained byte-identical
through the three staged requests. A fresh extraction outside the SciRel
checkout reproduced all three CSVs byte-for-byte and passed 9 tests.

The first pass was **not reliable**. Its stage-1 report claimed small nonzero
forward/inverse residuals because an ad hoc verification call mistakenly
connected recovered neutral density to the forward graph's electron-density
port. The actual round trip with the recorded electron density and temperature
has zero relative discrepancy to displayed precision. The report also stated
physical premises not present in the exact development record. An independent
duplicate-ID probe showed the comparison silently joining to the last of two
conflicting B1 rows. A changed check sheet aimed at an old result path
silently replaced that CSV. The passing tests and correct nominal figures did
not detect these issues.

One symptom-level review led Claude to reject ambiguous joins, protect both
ordinary entrypoints against changed-content replacement, and publish a
separate maintained correction report without rewriting the six earlier
deliverables. The evaluator corrected one file-count typo in that new report.
The [independent replay](../../../build/verification/balmer-forward-20260927-independent-finding.md)
on the final extracted archive passed 14 tests, refused a changed-input write
to the old path while preserving its digest, accepted an unchanged no-write
rerun, and kept B2/B3 useful when a conflicting B1 duplicate appeared. This
is a **review-assisted repair**, not a first-pass autonomous success.

The final runnable project archive is
[`balmer-forward-20260927-final-evaluator-corrected.tgz`](../../../build/verification/balmer-forward-20260927-final-evaluator-corrected.tgz)
(SHA-256 `740c870838a90e1c63564a258debe403ac42066a7f493025238cc171cefb9fd6`).
Its payload is an unchanged saved KN1DPy historical L1 table; strict D1
qualification is withdrawn, the table lacks an external atomic-physics oracle,
and the dev wheel is not approved. This evaluation demonstrates useful
multi-graph project construction and result retention on one staged synthetic
case, plus a concrete source-to-port and output-ownership failure. It does not
establish physical correctness, autonomous generalization, trusted/public v1,
or CodeFusion integration. The venv reused host scientific dependencies and
the two roles were not security-isolated.
