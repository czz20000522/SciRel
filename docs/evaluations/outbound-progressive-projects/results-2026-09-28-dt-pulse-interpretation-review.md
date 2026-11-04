# DT pulse interpretation review (2026-09-28)

This bounded blind variant tested the outbound usage-method change against a
different rate-to-inventory question. The [manifest](manifests/2026-09-28-dt-pulse-interpretation-review.json)
binds the pre-run request, inputs, method snapshots, dev58 wheel/catalog,
oracle, prompts, tool probes, raw traces, host checks and frozen project states.
The solver saw the request and a synthetic three-hold DT table, not the oracle
or reviewer prompt. Examiner separation used prompt/workspace layout, not OS
isolation. No SciRel scientific source or old frozen evidence was changed.

## Result and interpretation boundary

The input declared externally maintained density and temperature setpoints,
not an evolving inventory history. The selected exact asset was
`scirel.fusion.bosch-hale-reactivity` (DT branch). The user-provided source
note specified the project arithmetic `n_D * n_T * <sigma*v>` and a
file-order duration integral. Independent parsing of the written CSV matched
all 3 holds and 8 numeric columns against an oracle generated before the
solver ran. The final cumulative event density was `7.165954050900687e18
m^-3`; the CSV retained the same SHA-256 before and after interpretation
correction (`2eea87b6fb85451b48b810e40e7e390fe4057e89cb50e37e8f9dea20dd50664d`).

The solver's first user-facing draft nevertheless called `1 - cumulative
events / first-hold tritium setpoint = 0.9104` the fraction of *initially
present tritium* left. That divides an event integral at maintained setpoints
by one setpoint, without tracking which initial atoms survived fueling,
exhaust or transport. It also asserted a depletion correction of "at most
about two percent" without an evolution model. Passing numeric checks did
not justify either statement. The first draft and the green engineering
state before review were frozen separately.

A fresh read-only Agent reviewed the request, raw inputs, CSV, Markdown,
project code and exact asset document **before delivery**. It flagged both
interpretation claims. Its suggested alternatives included a survival value
of 1.0 under maintained setpoints and a different depletion percentage;
neither follows from these inputs, so the examiner passed on only the
supported findings. The solver removed the inventory answer and unmodeled
error bound, reported initial-tritium survival as **not determined**, and
retained `events / first-hold setpoint = 0.0896` only as a clearly labelled
arithmetic diagnostic. The final ordinary entrypoint exited 0, 9 project
tests and 9 standalone focused checks passed, and independent CSV/oracle
comparison passed. A further ordinary rerun left both final result files
byte-identical.

## Attribution

| Stage | Observed outcome |
| --- | --- |
| Solver before external feedback | Two visible code/test self-corrections (an undefined placeholder and a misleading test); zero self-detected inventory-interpretation corrections. First draft remained scientifically wrong. |
| Host execution diagnostics | The solver made one technical repair pass for pytest import and stub expectations. An interrupted continuation is retained. The examiner later fixed two test-only assertions concerning floating-point summation and Markdown line wrapping; neither changed scientific outputs. |
| Pre-delivery independent Agent | One review round, two material interpretation findings. The solver corrected both after the examiner removed unsupported proposed replacements. Final classification: **reviewer-assisted**, not autonomous first-pass interpretation. |
| User rescue | **0**. The correction happened before user delivery, not after a user complaint. |

## Tool constraint

The installed Claude Code 2.1.281 CLI exposed Git Bash, not a separate
PowerShell tool. A probe showed that `--allowedTools 'Bash(pwsh *)'` did not
exclude bare `pwd`: that command ran. The actual trial therefore used
`--tools Read,Edit,Write,Glob,Grep --disallowedTools Bash` for the solver and
read-only `Glob,Grep,Read` for the reviewer. The tool-init records and all
five trial traces show zero Bash calls. The tradeoff is explicit: the solver
could build and revise the project but could not run it itself; examiner-side
`pwsh` 7+ executed the ordinary entrypoint, tests and independent oracle
check and returned diagnostics. This run validates that division of work,
not autonomous execution inside Claude Code.

The changed usage method passed `scripts/check.ps1 -Mode affected` (7/7
selected documentation tests). This single synthetic case supports the
conditional interpretation-review method, not a universal claim that every
rate-to-population request will be caught. The dev58 catalog assets remain
`pending_unapproved`; the result is not expert approval, physical DT-fit
validation, a public release or a CodeFusion host comparison.
