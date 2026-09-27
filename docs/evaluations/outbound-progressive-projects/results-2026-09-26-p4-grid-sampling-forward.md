# Claude Code saved-grid composition forward test

This fresh, staged development evaluation required site readouts **from a
saved coarse R-Z preview grid**, not a fresh coil solve at each site. That
distinguishes the SciRel multi-coil vacuum TaskGraph followed by the existing
real-grid sampling Operator from the earlier direct-reevaluation case. The
synthetic input has three coil sections with different filament counts and
one opposing signed drive; a later user request adds a second drive and two
sites. The [manifest](manifests/2026-09-26-p4-grid-sampling-forward.json)
binds the exact fixture, two staged inputs, development SciRel artifacts,
four raw traces and archives, pre-feedback findings, review messages, and
independent checks.

Claude Code 2.1.281 ran in one new session with no token, time or call cap.
Its CLI init identified `claude-fable-5`, while assistant messages carried
`GLM-5.3-Flash`; the underlying model is unresolved. The bundled SciRel
`0.1.0.dev24` wheel, 74/74 catalog and solving skill were **unapproved
development artifacts**, not a trusted scientific release.

The first autonomous turn delivered a runnable project and correctly made
the outside site value-free. It calculated the preview using the SciRel
TaskGraph, then wrote its **own** bilinear sampler for the saved-grid site
table. Independent installed-SciRel calls showed the hand-written sampler
agreed at all four valid sites, but its 1e-9 m edge tolerance accepted a
point the SciRel sampler rejects. More seriously, the Agent omitted
per-filament weights. The user file defines each drive as a total for its
whole section, shared among 6, 6 or 4 filaments; the TaskGraph defaults an
omitted weight to one **per filament**. The delivered axis `B_z` was
`0.0317383405 T`, versus `0.00661397280115 T` when the same installed
TaskGraph and geometry use the declared equal shares. An independent
circular-loop axis calculation matched the corrected value. The project's
self-checks compared its internally consistent but wrongly driven grid and
table, so they did not detect the scientific error.

The second autonomous turn added the drive and sites and correctly refused
to treat the largest between-setting difference as a numerical-error bound
everywhere. Its ordinary entrypoint replayed all nine current files
byte-identically. But it kept both the wrong current normalization and
the hand-written sampler. Reference/survey axis values remained
`0.0317383405/0.0292655559 T`; equal sharing gives
`0.00661397280115/0.00620184203095 T`. It also claimed the first image
was untouched when its bytes and title had changed, without preserving
the first PNG in the user project. The second title collided with the
colorbar. These autonomous failures were frozen before any review feedback.

A first symptom-level review caused Claude to add `1/(nr*nz)` weights,
invalidate saved grids on scientific-code or wheel changes, call the actual
SciRel sampling Operator once for each field component, label the old
wrong-scaling results as superseded, and replace the misleading release
wording and Windows command. The extracted project imported the embedded
wheel and reproduced both corrected axis values. A spy at the installed
operator boundary observed two sampler calls per setting; the seven-row
comparison matched their values. All 39 output/history files stayed
byte-identical on an unchanged ordinary rerun. A near-outside point at
`R=0.4700000005 m`, however, was still silently clipped to the grid edge
`0.47 m` and marked available, contrary to the exact asset boundary.

A second review led Claude to remove that tolerance/clamp, restore **all
four** first-delivery files from its own frozen first archive with exact
bytes, and redraw the preview honestly: the actual coils lie outside the
displayed R range, so the final image no longer claims invisible outlines
or leaves a large blank strip. The final
[two-review-assisted archive](../../../build/verification/p4-grid-sampling-forward/stage4-reviewed-final.tgz)
has SHA-256
`d2c27669b768b169fa02c3f079d9f03d7cd9fc4e438c8ebbfad68e9f544def23`.

In a separate source-free extraction, the normal `pwsh` entrypoint installed
the embedded wheel into a new venv and passed the project's checks. Direct
SciRel TaskGraph calls matched both saved grids; installed-sampler calls
matched the current site and comparison rows. The `0.5 nm` outside point
was blank while the exact corner was available. All four first-delivery and
all nine second-delivery files matched their frozen archives. An unchanged
rerun left **59** current/history files byte-identical. In a further
isolated copy, changing only the survey drive rebuilt survey and comparison
while reference stayed byte-identical and the old survey grid was retained;
restoring the input restored the original result bytes, followed by a
byte-identical no-op rerun. The final PNGs were visually inspected for
legible titles, colorbars and truthful framing.

The case demonstrates a **review-assisted repair path** for TaskGraph to
Operator composition, input-change invalidation and result ownership. It
does **not** show autonomous correct asset selection or parameter binding:
two full user turns left the total-current error untouched until review.
The model's declared geometry spacing was held fixed in the independent
current-sharing comparison; the input's width-to-filament-center convention
was not physically adjudicated. The synthetic files and host-provided
scientific dependencies do not validate a real coil or a continuous error
bound. Examiner/solver separation was by directory and prompt, not OS
enforcement. This result is not a trusted release, stable generalization,
offline dependency reinstall, or CodeFusion integration.
