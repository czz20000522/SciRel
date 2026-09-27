# Cold-plasma table-join project: forward evaluation

A new Claude Code 2.1.281 session received a synthetic three-species plasma
description split across species, setting, field-site and frequency CSVs. The
first user turn requested an openable local cold-plasma dielectric-tensor
comparison at two sites and two frequencies. A later turn added a collisional
setting and a third frequency, requested retention of the first deliverables,
and asked whether a larger imaginary tensor entry meant more absorbed power.
The solver had only the user files, a SciRel `0.1.0.dev24` development wheel,
the matching 74/74 catalog and scientific skills. Examiner scripts and prior
case notes were outside its project directory. The exact inputs, skill, four
raw turns, four archives, reviewer messages and findings are bound by the
[manifest](manifests/2026-09-26-stix-join-forward.json). The CLI reported
`claude-fable-5`, assistant messages reported `GLM-5.3-Flash`, and the
underlying model was not independently confirmed. No call or budget limit was
set.

Both **autonomous** turns used the catalog-selected SciRel cold-plasma tensor
Operator and produced numerically correct outputs. An examiner-only formula
that joins the raw CSVs independently matched the first four and later all 12
tensor rows, checking `eps_11`, `eps_12` and `eps_33`, to at most
`1.455e-11` absolute difference. The second turn retained the first CSV,
PNG and check log byte-for-byte in `output/archive/`. It correctly separated
large collisionless Hall-type imaginary entries from the dissipative part of
the tensor and refused to produce absorbed-power numbers without a wave
electric field. An unchanged run on the delivered second stage was byte-stable.

The autonomous scientific check was nevertheless **false-green**. Its
purported independent Stix calculation consumed the same production species
list already assembled for the asset call. In isolated copies of both
autonomous archives, multiplying only the production electron-mass port by
ten made every built-in check pass and the ordinary entrypoint exit 0 while
writing wrong CSVs and plots; the raw-input examiner rejected
`eps_11(original, axis, low)` as `+12.469739591834525` instead of
`-22.688009519422515`. The second-stage README also remained stuck at the
first-stage two-frequency collisionless description and gave a wrong
gyrofrequency for the doubly charged helium ion. After a legitimate density
correction, the immediately following no-change rerun created an extra
archive containing only `checks.txt`, because fresh-versus-cached wording had
changed. These first failures were frozen before feedback and cannot be
counted as autonomous complete delivery.

Two explicit reviewer turns repaired the user project. The first made a
separate raw-file read verify every used setting's species IDs and asset-port
values, changed the reference calculation to consume that raw read, corrected
the stale project documentation and stopped cache-status text from generating
a duplicate historical version. Independent replay of that intermediate
archive showed the wrong-mass mutation now failed with old user files intact,
and a changed-input/first-no-change sequence no longer added an archive. A
second review corrected a remaining scientific explanation: He2+ has roughly
twice the deuteron's charge **and** mass, giving nearly equal charge-to-mass
ratios, not twice the ratio. It also distinguished pre-digest archives from
later digest-bound ones, stopped rewriting byte-identical files, and added a
minimum-eigenvalue check before saying that every nonzero polarization is
dissipative at these evaluated points. The original errors, both feedback
messages and the actual repairs remain separately visible.

The [final two-review-assisted archive](../../../build/verification/stix-join-forward/stage4-reviewed-final.tgz)
has SHA-256 `b92fe35eb883b51469401f0ab4eb7783446ca225b2c616b4cd641ca3ae34df4d`.
In a separate extraction, its wheel installed into a new source-free virtual
environment. The ordinary entrypoint exited 0; the first no-change rerun
preserved all 23 output/history/cache files by both bytes and timestamp.
An examiner raw-input calculation matched all 12 rows within
`1.455e-11`. The six original cases had exactly zero dissipative eigenvalues;
the six damped cases had strictly positive minimum eigenvalues between
`0.0076902944217` and `0.0302531803957`. The first-delivery three files
matched their frozen first-stage bytes. In an isolated final-archive copy,
the same tenfold electron-mass mutation made the ordinary entrypoint exit 1
without changing the five user-facing files. A separate density edit
recomputed the affected cases, archived the old five files, and was followed
by a first no-change run with 28 files unchanged by bytes and timestamp; undoing
the edit recovered all five frozen baseline files. The exact commands and
limits are in the [independent check](../../../build/verification/stix-join-forward/independent-stage4-check.txt).

This establishes a bounded, **review-assisted** reusable project for
synthetic local cold-plasma response, not a wave-field or absorbed-power
solution. It does not prove model applicability to a real device, stable
autonomous generalization, expert approval, trusted/public SciRel release,
strict examiner isolation or CodeFusion integration. The current
`scirel-solving` revision was actually loaded, yet two autonomous turns still
failed to make the source-to-port check independent. More mandatory global
script rules do not follow from one case; the repeated failure is evidence
for improving method adherence and testing it on further unseen structures.
