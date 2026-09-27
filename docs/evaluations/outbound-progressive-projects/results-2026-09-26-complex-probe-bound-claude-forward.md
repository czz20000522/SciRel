# Claude Code complex-probe bound forward test

This fresh, staged development evaluation tested a narrow change to the
`scirel-solving` method: an error-bound claim must identify the error target,
domain, reference and actual bounding argument. The new input shape was a
synthetic **three-dimensional complex-vector NPZ** plus a station CSV, rather
than the earlier coil field grids. A second request later added a denser NPZ
covering the same box and three more stations, asked to keep the first
deliverables openable, and asked whether the largest station difference was a
guaranteed error upper bound throughout the box. The [manifest](manifests/2026-09-26-complex-probe-bound-claude-forward.json)
binds the exact staged inputs, wheel, catalog, skill, raw traces and archives.

Claude Code 2.1.281 ran in one new session without a token, time or call cap.
The CLI reported `claude-fable-5` and assistant messages carried
`GLM-5.3-Flash`; the underlying model identity is unresolved. The supplied
SciRel `0.1.0.dev24` wheel and complete 74/74 catalog were **unapproved
development artifacts**, not a trusted release. The updated skill SHA-256 was
`443384b6748a731dc450a4945477a4319f938334a146cdb5bcf9cd5070d97b4e`.

The first autonomous turn selected
`scirel.geometry.complex-rectilinear-interpolation`, delivered a runnable
project, a CSV, chart and NPZ, and left the one out-of-box station explicitly
unavailable rather than zero. It refused wave-propagation, heating and device
claims from synthetic samples. The [first archive](../../../build/verification/complex-probe-bound-claude-forward/stage1-autonomous-delivery.tgz)
was independently extracted; 4 project tests and its ordinary entrypoint
passed, and its three output files were byte-stable on rerun.

The second autonomous turn consumed the later files without reviewer help,
retained all three first-delivery outputs byte-identical, and processed six
valid and two out-of-box stations. Its answer correctly rejected the requested
guaranteed field-error bound: the station maximum is only a sampled difference
between two reconstructions, not an error against a true physical field or a
bound over unobserved points. It used a further **finite** 1053-point probe
to demonstrate that a larger difference exists away from the six valid
stations. Its final chat response and CSV correctly separated the complex
vector difference `|delta E|` from the difference of magnitudes
`delta |E|`.

The inspectable README nevertheless labeled the station `0.0058 V/m` and
probe-grid `0.0111 V/m` values as `delta |E|`. Both numbers actually describe
`|delta E|`; the station maximum of the magnitude difference was
`0.0042 V/m`. This primary-artifact inconsistency is frozen in the
[pre-feedback finding](../../../build/verification/complex-probe-bound-claude-forward/independent-stage2-finding.txt).
The source-free autonomous archive passed 7 project tests and ordinary rerun,
which did not detect the prose/metric mismatch. One symptom-level reviewer
message led Claude to correct the README and add a report-to-data test without
altering any numerical output. Thus the [final archive](../../../build/verification/complex-probe-bound-claude-forward/stage3-reviewed-final.tgz)
is **reviewer-assisted**, not a complete autonomous scientific delivery. Its
SHA-256 is `78e636e94244b0a7d781d677ca555c4ec84ef0143a17a196bf577b808d600705`.

The final archive was separately extracted and its wheel installed into a
new venv. Eight project tests and the no-argument user entrypoint passed; all
six result files stayed byte-identical on rerun. An independent direct call
to the installed SciRel relation matched SciPy at all six valid stations,
confirmed both unavailable stations, all shared nodes, and the original
output bytes. It measured station max `|delta E| = 0.00583251920532 V/m`,
station max absolute `delta |E| = 0.00420420318728 V/m`, and finite-probe
max `|delta E| = 0.01108130995 V/m`. See the
[independent check](../../../build/verification/complex-probe-bound-claude-forward/independent-stage3-check.txt).

The reviewer-added README test guards the specific corrected phrases, but it
is not a general report-to-data validator. It requires exact prose even when
an equivalent wording would be correct, and its finite-probe assertion rounds
to three decimal places although the README quotes four. The independent
numeric check above, not that project test alone, supports the quoted values.

This single unseen structure gives **bounded positive evidence** that the
revised method can help distinguish finite observations from a guaranteed
continuous bound while delivering an evolving user project. It does not prove
stable generalization: the first-pass README still confused two related
observables, requiring review. Static example numbers in that README refer
to the current inputs and would be stale after another input revision unless
updated; the entrypoint does not regenerate prose. There was no OS-enforced
examiner/solver read isolation or full offline dependency reinstall. The
synthetic export provides neither a physical truth reference nor evidence of
wave propagation, device field accuracy or a continuous error bound.
