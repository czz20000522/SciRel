# Claude Code corrected-input forward test

This development evaluation continued the previously **reviewer-assisted**
complex-probe project from its frozen stage-3 archive. A new Claude Code
2.1.281 session received only a corrected station CSV and a lay request:
east was at x = 0.32 m, not 0.42 m; keep the old results openable, update the
normal result, and explain whether the physical field changed. The
[manifest](manifests/2026-09-26-complex-probe-correction-claude-forward.json)
binds the prior archive, input, three raw traces, three successive archives,
review feedback, findings and independent check. The CLI reported
`claude-fable-5` while assistant messages carried `GLM-5.3-Flash`; the actual
underlying model remains unresolved. The supplied SciRel `0.1.0.dev24`
wheel, 74/74 catalog and solving skill were development artifacts, not an
expert-approved release.

In the **first autonomous** turn Claude changed the operative station list,
preserved all six previous output files byte-for-byte under
`output/archive/east-x042-typo/` with the old input CSV, and generated six
corrected outputs. It correctly explained that the synthetic field volumes
were unchanged and only the sampling point moved. An independent installed
SciRel call and SciPy agreed at all six available corrected stations. The
station maximum `|delta E|` became `0.0083587292574 V/m` (previously
`0.00583251920532 V/m`), and the maximum absolute difference of field
magnitudes became `0.00618153361821 V/m` (previously
`0.00420420318728 V/m`). The finite 1053-point probe maximum stayed
`0.01108130995 V/m`. None is a continuous-domain or physical-truth error
bound.

The autonomous ordinary entrypoint nevertheless described a current NPZ as
"first delivery, unchanged inputs", although the station input and current
output bytes changed. That first-pass attribution defect was frozen in the
[finding](../../../build/verification/complex-probe-correction-forward/independent-stage1-finding.txt)
before feedback. One symptom-level reviewer message caused Claude to change
the label, add a correction-file preflight and provenance status to current
NPZ files. A separate negative replay then passed the prior input folder,
which lacks `corrected-stations.csv`: the entrypoint said "unverified" yet
still labeled the result "CURRENT corrected station list". Its README also
claimed a later station list could be replaced under one filename while the
new preflight required the correction file to match. The
[second finding](../../../build/verification/complex-probe-correction-forward/independent-stage2-finding.txt)
was frozen before a second narrow feedback message.

The [final reviewed archive](../../../build/verification/complex-probe-correction-forward/stage3-reviewed-final.tgz)
has SHA-256
`b7aca6a7d6a0cf162b521a80f7369be2ffe83836e5c117a473a0736450a0146e`.
Its ordinary corrected-input run labels current results as verified against
the supplied correction. Without that file, it labels outputs and both raw
NPZs **unverified**, not corrected. README now says a later station-list
revision must update both operative and verification CSVs. This is a
project-local rule for this correction history, not a general SciRel
contract; future revisions still require deliberate result/version handling.

In a separately extracted copy, the embedded wheel imported from a new
venv's `site-packages`; 12 project tests and the ordinary entrypoint passed.
All six current outputs were byte-stable on rerun. The independent checker
confirmed all six archived outputs and the prior station list remained
byte-identical, only east's coordinates changed, both field volumes were
unchanged, SciRel and SciPy agreed at every valid site, and the old-input
negative branch did not claim correction. The operative and supplied
correction CSVs are numerically identical but not byte-identical because
Claude reformatted decimal text and line endings. The comparison NPZ stores
the station points and volume digests but not a digest of the station CSV.

This supports a bounded ability to preserve old deliverables and repair an
input correction in a runnable project. It is **not** an autonomous complete
delivery: the underlying project was already reviewer-assisted and this
follow-up needed two additional reviewer interventions to make result
attribution truthful. The test used synthetic files, host-provided scientific
dependencies, and no OS-enforced examiner/solver isolation. It does not prove
future input revisions will be automatically versioned, physical field
accuracy, a continuous error bound, or trusted SciRel release behavior.
