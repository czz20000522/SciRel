# Reviewer-claim adjudication variant (2026-09-28)

This bounded follow-up tested the decision exposed by the [DT pulse trial](results-2026-09-28-dt-pulse-interpretation-review.md):
the earlier solver received only examiner-filtered feedback because an
independent reviewer's valid defect findings came with unsupported replacement
values. The [manifest](manifests/2026-09-28-reviewer-claim-adjudication.json)
binds this variant's pre-run inputs, unfiltered challenge, method snapshots,
attempt traces, saved outputs and test receipt. All trial files are under the
ignored `build/verification/reviewer-claim-adjudication-20260928/` directory.

The new three-hold input stipulates externally maintained DT states and event
rates. Its independently checkable event density is `1e18 + 3e18 + 2e18 =
6e18 m^-3`. The first draft wrongly calls `1 - 6e18 / 1e20 = 94%` the survival
of the initial deuterium cohort and asserts a `1%` depletion-error bound. The
examiner wrote a mixed-quality reviewer note before the solver ran: it correctly
flags both defects, then recommends `exp(-0.06) = 94.18%` as a Poisson survival
probability and retaining the `1%` bound. The source supplies neither a
per-atom hazard nor cohort evolution, so that substitute is unsupported.

The solver saw the complete note without filtering and did not see the
prewritten oracle. Its saved `review_decision.md` accepts both findings and
rejects the exponential replacement and error bound against the original
source. Its corrected report retains `6e18 m^-3`, labels initial-cohort
survival undetermined, and makes no depletion-error claim. Examiner-side
`pwsh` parsed the raw CSV independently and checked the report and decision;
the three hold contributions, total and interpretation checks passed. The
successful trace shows the solver read both method bodies and all task inputs,
wrote both requested files and read them back. It used the local `node_repl`
file tool for its own check, with no shell command or SciRel callable. The
examiner did not edit its output or filter the reviewer note.

The first Claude CLI attempt stopped before inference with `Not logged in`.
A Codex CLI attempt that ignored the configured local provider reached the
public API and stopped with `401`; it also made no project change. The final
consumer run used the existing local Codex proxy and completed. These failed
attempts are retained, not counted as model or method outcomes. The reviewer
note in this variant was examiner-authored, so this run tests **solver
adjudication of mixed feedback**, not the quality of a newly sampled reviewer
or autonomous first-pass detection. The initial error was planted in the draft;
the solver corrected it after reviewer feedback, with zero examiner filtering
of that feedback and zero user rescue. The original DT pulse classification
remains reviewer-assisted with examiner-filtered advice.

The conditional usage-method edit passed `scripts/check.ps1 -Mode affected`
(31 selected tests, including seven workflow-documentation tests). This one
synthetic variant supports the narrow claim that this solver instance
separated a supported criticism from an unsupported numerical repair under
the stated inputs. It does not establish general reviewer reliability,
independent physical validation, expert approval or a public release.
