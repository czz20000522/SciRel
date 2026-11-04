# Claude Code two-setting coil project forward test

This fresh, staged development evaluation used a synthetic axisymmetric
two-section coil, total ampere-turns per section, a preview R-Z grid, and
off-grid probe sites. The later request added a trim setting and two sites,
required the earlier table and image to remain openable, and asked whether
the largest setting difference bounds numerical error everywhere. The
[manifest](manifests/2026-09-26-p4-probe-combo-forward.json) binds the exact
fixture generator, staged inputs, SciRel artifacts, raw traces, frozen
archives, pre-feedback findings, review messages, and independent checks.

Claude Code 2.1.281 ran in a new session without a token, time or call cap.
The CLI reported `claude-fable-5`, while assistant messages carried
`GLM-5.3-Flash`; the underlying model identity remains unresolved. The
supplied SciRel `0.1.0.dev24` wheel, 74/74 catalog, and `scirel-solving` skill
were development artifacts, not expert-approved assets or a trusted release.

In the first autonomous turn, the Agent selected the SciRel multi-coil vacuum
TaskGraph, divided each section's 4.2 kA-turn total equally among its four
representative filaments, and produced a runnable project. A separately
extracted copy imported the embedded wheel from a new venv, passed seven
project tests, and reproduced the three saved output files byte-for-byte.
Its on-axis circular-filament check was appropriate to the declared model.
But the site marked outside the preview was simultaneously called
unavailable and given a numerical field value. Its label also overlapped
the preview plot's colorbar. These first-pass defects were frozen before the
second user request or review feedback.

The second autonomous turn added the trim setting and sites. It preserved
all three first-stage outputs byte-for-byte, passed nine project tests in a
separately extracted copy, and correctly refused to treat a finite setting
difference as a continuous-domain numerical-error bound. Independent direct
SciRel calls and a circular-loop axis calculation reproduced both setting
tables and the seven-site comparison. Nevertheless, two outside-preview
rows had numbers, one of which set the reported 0.917254 mT maximum. A
changed `trim.high` input left the old trim table at 7.26701 mT on axis
while a new comparison reported 7.44003 mT for that same setting. The plot
had an obstructed colorbar and used a signed scale for nonnegative
`|delta B|`. The chat also asserted without support that absolute numerical
error would stay unchanged when both drives doubled. These issues were
recorded in the pre-feedback finding, not discovered after a rescue.

The first symptom-level review led Claude to blank outside-preview numeric
cells, limit the valid-site maximum to 0.597252 mT, repair the plot, and
rebuild changed settings while retaining the previous trim result. The
11-test reviewed archive still archived and rewrote outputs on every
unchanged ordinary rerun; even its HTML changed solely because redundant
history links advanced. A second, narrower review requested true no-op
behavior without sacrificing changed-input history. The final
[two-review-assisted archive](../../../build/verification/p4-probe-combo-forward/stage4-reviewed-final.tgz)
has SHA-256
`fbd34f41112f4167b010ff071e4faf1b4dce6f5d30d6145fb0a7ba44134c7178`.

The final archive was separately extracted, and its embedded wheel was
installed into a new venv. Eleven project tests passed. The independent
checker confirmed all three first-delivery files under
`outputs/archive/steady/001` were byte-identical; valid site rows matched
the earlier direct SciRel check; outside-preview numeric cells were blank;
and the valid-site maximum was 0.597252 mT. An unchanged ordinary rerun
left all 54 output/history files byte-identical. Changing `trim.high` from
4.8 to 5.0 kA-turns updated only trim and comparison, retained the old trim,
and reported 7.44003 mT on axis in both current tables. These are checks of
the delivered project and the declared ideal coil calculation, not a
validation of a real device's field.

This case is **not an autonomous complete delivery**: the autonomous stage
handled current normalization and the finite-bound question, but its
availability, result-history, plot, and scientific-explanation defects
required two reviewer interventions. The request did not require probe
values to be sampled from the already computed preview grid. Direct
TaskGraph reevaluation at the probe coordinates was legitimate with the
provided coil inputs, so the absence of a separate sampling Operator is a
fixture-design limitation, not evidence of a multi-asset composition
failure. Synthetic inputs, host-provided scientific dependencies, and lack
of OS-enforced examiner/solver isolation also limit the claim. No trusted
release, continuous error bound, physical-device validation, stable
generalization, or CodeFusion integration follows from this run.
