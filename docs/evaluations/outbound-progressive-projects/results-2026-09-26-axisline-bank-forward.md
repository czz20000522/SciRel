# Axisline winding-bank forward evaluation

This fresh Claude Code 2.1.281 session used a different file structure and
observable from the earlier saved-grid P4 case: two signed whole-bank
ampere-turn declarations in CSV and five points on the cylindrical axis.
The solver received only the user files, development SciRel wheel, complete
74/74 development catalog, and scientific skills. The examiner's analytic
oracle and prior evaluation records were outside its working directory. The
[manifest](manifests/2026-09-26-axisline-bank-forward.json) binds the exact
inputs, skill, wheel, traces, feedback, and three archived stages. The CLI
reported `claude-fable-5`, while assistant messages reported `GLM-5.3-Flash`;
the underlying model remains unconfirmed. No call, time, or token budget was
imposed.

The first autonomous delivery selected and invoked three SciRel Operators:
rectangular filament placement, dense axisymmetric Green response, and
current-response superposition. It divided each whole-bank current among
its six representative filaments and produced an openable axisline table and
plot. Its five total fields matched an independent raw-CSV circular-loop
calculation to at most `4.525e-13 T`; at `Z=0`, the result was
`0.002635461200 T`. The ordinary entrypoint and six focused tests ran.
This is a correct numerical result for the declared ideal vacuum model, not
validation of a real coil, plasma, or trusted SciRel release.

The autonomous project's stated "independent end-to-end oracle" was not
actually independent of current apportionment. Both the production path and
the check called the same `current_per_filament_a` property and SciRel
filament-placement helper. In an isolated mutation, changing that property
to apply each bank's total to every filament made all of the project's
checks still print PASS while the external raw-file oracle rejected the
sixfold field. The first archive and raw trace preserve this failure.

The first narrow review corrected a false `release` label and an unsupported
nearest-source distance; it did not alter the calculations. A second review
pointed out the shared mapping in the self-check. The final project derives
its oracle positions and equal current shares separately from the bank
facts, without calling the production mapping helpers. The same isolated
wrong-current mutation now causes the ordinary entrypoint to exit 1 on a
relative deviation of `5.000e+00`, while the unmutated delivered table and
PNG remain byte-identical to the autonomous first delivery.

The [final reviewed archive](../../../build/verification/axisline-bank-forward/stage3-reviewed-final.tgz)
has SHA-256 `ce7e130142a0fa6f2c863d1ca6cee21588b40058351dda37e4e6853f8d890222`.
In a separate extraction with the wheel force-installed in a source-free
venv, the user entrypoint passed its checks, seven focused tests passed, and
the examiner's standard-library raw-input checker matched all five rows.
Both result files reran to their original exact bytes. The examiner's
checker is evaluation evidence, not a SciRel workflow implementation.

This case supports a narrow observation: the Agent found the correct
whole-bank current mapping in one new axisline structure, but its first
validation would not have caught the prior class of scaling error. Two
review interventions were required for an honest, discriminating check and
trust wording, so the final project is review-assisted, not autonomous
complete delivery. The solver's own oracle still shares the production CSV
parser; the external checker supplies an additional independent raw-file
path. A later one-sentence skill revision forbids reusing the production
fact-to-port helper in an independent check; this exact revision was **not**
the one the solver loaded and still needs a separate forward trial. No
physical device, continuous error bound, public release, or CodeFusion
integration is established.
