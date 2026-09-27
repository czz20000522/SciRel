# Saved-state predictions to observation residuals: Claude Code forward trial

This fresh two-turn synthetic user project tested a different graph edge from
the coil/grid cases. The user first supplied a four-node saved R-Z simulation
table and two diagnostic locations, asking for rerunnable point predictions.
The later request added measured values with sigmas and an outside-grid point,
asking for signed normalized differences while retaining the first result.
The [manifest](manifests/2026-09-27-synthesis-residual-forward.json) binds
the exact inputs, unapproved SciRel `0.1.0.dev39` wheel and complete 126/126
catalog, copied skills, four project archives, raw Claude traces, review
messages, independent checkers and mutation copies.

Claude Code `2.1.281` used one new session
`a7fb6038-9404-417e-9914-0dc89d63cf0a`, with no token, time or call cap.
The CLI init said `claude-fable-5`, assistant events said `GLM-5.3-Flash`;
the underlying model was not confirmed. The solver project and examiner
expectations were in separate directories, not OS permission domains.

In the first **autonomous** turn, Claude found the host catalog and selected
`scirel.diagnostics.equilibrium-synthesis-diagnostics`, whose dependency is
the SciRel bilinear-grid sampling Operator. It produced an ordinary Python
entrypoint and CSV with alpha `(2.7 Wb/rad, 10.65 Pa, 20.9 Pa)` and beta
`(4.9 Wb/rad, 11.55 Pa, 22.3 Pa)`. A separate extraction passed 9 project
tests; the ordinary run was byte-stable. An independent raw-four-corner
calculation matched all six output numbers within `3.553e-15` absolute.

The first turn did **not** validate its own source-to-port claim. The
[independent stage-1 finding](../../../build/verification/synthesis-residual-forward/independent-stage1-finding.md)
preserves two post-freeze mutations: swapping the pressure arrays at the
actual TaskGraph ports left the witness green and delivered swapped columns;
adding a point just beyond the R edge but within the project's tolerance
made the exact SciRel sampler reject the entire run instead of marking only
that point unavailable. Neither mutation was shown to Claude before the
second autonomous user turn.

The second **autonomous** turn reopened catalog discovery for the new
relation and selected `scirel.diagnostics.observation-residuals`, connecting
it to the earlier TaskGraph predictions. It preserved the first prediction
CSV byte-for-byte, scored six supported measurements, excluded outside-grid
gamma, and produced unreduced `chi2=2.6`. In a source-free extraction,
18 project tests and the ordinary comparison entrypoint passed; the
independent raw-grid/observation checker matched all six residuals within
`7.106e-15` absolute. The stage-2 output kept the Wb/rad psi point sample
distinct from a physical integrated loop flux and did not claim real-device
agreement.

The second turn's witness was also false-green. The
[stage-2 finding](../../../build/verification/synthesis-residual-forward/independent-stage2-finding.md)
shows that multiplying only the flux-channel sigma values actually passed
to the SciRel residual Operator by 10 left the ordinary command exiting 0,
reporting witness PASS and writing `chi2=1.3625` instead of the raw-file
value 2.6. Its witness re-parsed the observation strings but did not inspect
the actual call port.

One symptom-level review caused Claude to add TaskGraph and residual
call-boundary witnesses, with failures before writing user results. It also
introduced an 8-ULP local boundary slack. Independent replay confirmed the
sigma mutation now failed closed, but a point about five ULPs beyond the
R edge still passed the precheck and aborted the whole comparison when
SciRel correctly rejected it. The [stage-3 finding](../../../build/verification/synthesis-residual-forward/independent-stage3-finding.md)
preserves that new failure. A second narrow review removed the slack and
matched the sampler's exact closed-grid domain.

The [final two-review-assisted archive](../../../build/verification/synthesis-residual-forward/stage4-reviewed-final.tgz)
has SHA-256 `9d86c39bd77fb1a049cf20e5861101e30d076a05c0294647a3e8a26a9991bffe`.
The [independent final check](../../../build/verification/synthesis-residual-forward/independent-stage4-check.md)
extracted it outside the SciRel checkout: 27 project tests passed, the
ordinary comparison reran byte-stably, the raw-source checker again found
six values and `chi2=2.6`, and the old two-point CSV retained SHA-256
`964028fd341a3762b53e0e0ac68cacdc9f825354f2c2c05a17c06b7089bd148f`.
An outside point at `R=1.000000000000001 m` was now reported per-row while
the other comparisons remained usable. The tenfold actual sigma-port
mutation exited 1 before changing any prior output. These repaired behaviors
were independently replayed, not counted as autonomous first-pass success.

The fixture establishes a bounded development path from evolving user input
through a real SciRel TaskGraph-to-Operator connection to a reusable result.
It does **not** establish robust autonomous source-to-port validation,
arbitrary-grid reliability, physical correctness of the synthetic state,
expert approval, license disposition, public v1 release or CodeFusion
integration. The final user project does not contain a general transaction
over all output files or an immutable copy of every earlier source input;
the evaluation archives retain those bytes. The venv reused host scientific
dependencies, so this is not an offline dependency-install proof. No new
global skill prohibition or CodeFusion-specific kernel change follows from
this one reviewed case.
