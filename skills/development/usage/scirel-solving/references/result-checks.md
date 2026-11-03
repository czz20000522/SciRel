# Check the result that will be delivered

Choose a check that can distinguish a plausible wrong answer: a reference with known independence, an analytic limit, conservation, symmetry or numerical refinement. Finiteness and a successful import are insufficient. Check contract diagnostics and all nontrivial connections as well as the final quantity.

Classify a failure before changing anything:

| failure | consequence |
| --- | --- |
| invalid user data/domain | identify the inconsistent datum and required correction |
| interface mismatch | adapt a scientifically equivalent representation or report the mismatch |
| numerical/applicability limit | give the conditioning/range limit and a bounded alternative |
| implementation defect | preserve the exception or failed diagnostic on valid inputs |
| environment/integrity failure | repair the supplied installation/input boundary before relying on it |

Read delivered tables back, checking quantities, units, row/coordinate coverage and failed points. Generate numerical prose, threshold decisions and plot labels from saved values. The optional [delivery helper](delivery-tool.md) performs bounded CSV-to-report consistency checks; it does not establish physical validity. Inspect requested figures and actually run a requested code entrypoint.

Preserve original criteria and failures. A terminal-point diagnostic does not validate a scan; a partial spectrum does not establish agreement of the full spectrum. If representations differ, establish the requested scope before comparing. Do not explain a failed reference away with a generic limitation unless that explanation is checked for this run.

Report which checks passed, failed or were `NOT_RUN`, and separate self-consistency from independent evidence. Rerun affected computations and reporting after an input or assumption changes.
