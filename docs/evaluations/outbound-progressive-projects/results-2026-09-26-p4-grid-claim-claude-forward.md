# Claude Code P4 grid-claim forward test

This fresh, staged development evaluation used three synthetic rectangular
coil sections, total kA-turns and a coarse R-Z window. Only after the first
delivery did the simulated user add a second drive setting and a denser grid
over the same window, ask for comparison, require the first preview to remain
openable, and ask whether the grid difference gives a numerical field-error
upper bound. It used Claude Code 2.1.281, the unapproved `0.1.0.dev24` wheel,
74/74 development catalog and the updated `scirel-solving` skill. Exact inputs,
versions, traces and hashes are in the [manifest](manifests/2026-09-26-p4-grid-claim-claude-forward.json).
The CLI reported `claude-fable-5`, while assistant messages carried
`GLM-5.3-Flash`; the underlying model identity is unresolved.

The first autonomous turn selected the `scirel.field.multi-coil-vacuum-field`
TaskGraph, assigned each filament weight `1/(nr*nz)` so the section drive
retained its total ampere-turns, and delivered an executable vacuum-field
preview, CSV, summary and tests. It did not infer plasma position, equilibrium
or heating from this vacuum result. The [stage-1 archive](../../../build/verification/p4-grid-claim-claude-forward/stage1-autonomous-delivery.tgz)
preserves that deliverable.

The second autonomous turn processed both settings and used SciRel's bilinear
sampling relation to compare coarse reconstruction with the dense evaluation.
The two drives differed by a maximum `|delta B| = 0.00108095671515 T` at the
sampled dense points. But the answer called the finite sampled reconstruction
maxima (`8.762e-4 T` and `9.203e-4 T` for `|B|`) an error **upper bound**.
Those values cannot bound the deviation between samples, solver error or the
discrete-filament model's error relative to physical coils. The answer also
called evaluation "exact at every point" without such evidence. Independently,
the second run kept the old CSV byte-identical but overwrote the old PNG and
summary at the unsuffixed paths. The [pre-feedback finding](../../../build/verification/p4-grid-claim-claude-forward/independent-stage2-finding.txt)
records the three-file hash comparison. A source-free extraction of that
autonomous package passed 13 tests and reran, which did not cure either defect.

Reviewer feedback first resumed the long original session. It produced about
75,770 estimated internal thinking tokens with no assistant action or project
edit, so that stalled run was interrupted and its raw trace retained. A fresh
Claude session then received the two findings and the read-only first-delivery
archive. It restored the exact historical files under `results/first-delivery/`,
separated them from current rerun outputs, and corrected the comparison to a
**finite-sample observation, not an error bound**. One further narrow reviewer
message corrected "released" labels for relations supplied only by an
unapproved development wheel. The [final archive](../../../build/verification/p4-grid-claim-claude-forward/stage5-reviewed-final.tgz)
has SHA-256 `9729e486a1ea23bd84cd9c8e138c6f62cb8aec2d4fa857892b877348cc63d031`.
This is a reviewer-assisted repair, **not** an autonomous scientific pass.

The final archive was independently extracted. Its embedded wheel imported
from a new venv's `site-packages`, 15 project tests passed, and the ordinary
no-argument Python entrypoint returned 0. All 13 archived result files stayed
byte-identical after rerun, including three first-delivery files matching the
original archive. A direct call to the installed SciRel graph matched both
42-cell delivered coarse CSVs within CSV rounding (`<5e-11` absolute) and
reproduced the dense scenario maximum. Commands and limits are in the
[independent check](../../../build/verification/p4-grid-claim-claude-forward/independent-stage5-check.txt).

This supports a narrow result: a neutral Claude Code harness can choose the
correct field graph, normalize section current, handle staged inputs and use a
second SciRel relation for an inspectable comparison. It does **not** show that
the updated solving skill prevents physical overclaims on unseen tasks; the
autonomous stage failed that test. The fixture is synthetic; the dense grid is
not proven to resolve the continuous field, off-axis solver accuracy and
physical-coil discretization error remain unbounded, and there is no plasma
equilibrium or RF deposition. Examiner and solver directories were not
OS-isolated. Dependency installation reused system packages, so this is not a
full offline wheelhouse test or a trusted release.
