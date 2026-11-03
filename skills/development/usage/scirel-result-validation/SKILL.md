---
name: scirel-result-validation
description: Check a computed scientific result before delivering it — discriminating physics checks, boundary cases, readback, preserved failures and figure review — whether or not SciRel was used.
---

# Check a result before delivery

Use this after the calculation runs and before telling the user the task is done. Check the whole result, not only the SciRel calls. The `scirel-solving` skill has more background in its result checks reference.

1. **Independent physics checks.** Each expected value must come from a separate route: an analytic limit or known special case, an independent method, a conservation law, or a convergence study. It must be able to catch a wrong sign, normalisation or unit. A relation that holds by definition, such as a magnitude computed from its own components, is not a check. Symmetry alone is not enough, and the number of checks is not a goal. Fix tolerances from error estimates before looking at results.
2. **When a check fails,** find out why before going on. If the physics result is wrong, fix the calculation and rerun. If the check is wrong (reference formula, tolerance basis or comparison direction), fix it, rerun, and note the change in the appendix in a sentence or two. Only a failure still unresolved after that is reported as a failure; a check known to be wrong is not kept as one. Never widen a tolerance just to pass. Use the latest run.
3. **Limits of the inputs.** Where the problem has them, test the physical limits of the input range and any degenerate, branch or failure cases, with expected behaviour worked out independently. Do this for the cases that could change the result, not to fill a matrix.
4. **Glue code too.** Test your own code around SciRel calls: units, shapes, ordering, conversions and formatting. Where a contract's convention differs from the problem's (per radian or total, per unit area or total, eV or joule), convert at the call and test the call against a hand value that the missing factor would change. When the input is a file in a standard format, check the parse against something in the file that a misplaced field would break, such as a header quantity recomputed from the gridded data.
5. **Read back.** Open the saved outputs and stderr after running. Check that every requested point or case is present. Keep real typed failures and non-convergence as they are; do not replace them with a success.
6. **Figures.** Open every figure and look at it; pixel statistics do not count. Check that it shows physical quantities rather than code flow or tool use, that the axis range makes the key difference visible, that no legend or label covers data, and that it answers the question in its caption.
7. **Report structure.** Run `python <scirel-solving>/scripts/validate_report.py REPORT.md`. It checks structure only; read the method and discussion as a physicist would. Check every qualitative word in the text, such as everywhere, monotonic, about N times or dominant, against the saved data, and take numbers in the prose from the data files rather than retyping them.
8. **Record** the entrypoint, the SciRel asset IDs used, the checks with pass, fail or not-run status, and what remains uncovered, in the report appendix.

A result that merely parses proves only that the program reached its output. A step SciRel does not cover is done as tested ordinary code and stated as such in the report; it does not become a SciRel result.
