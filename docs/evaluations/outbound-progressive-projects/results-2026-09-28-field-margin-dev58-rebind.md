# Field-to-margin project rebound to r81/dev58 (2026-09-28)

This is a compatibility replay of the frozen, two-review-assisted dev49
field-to-margin project. Its original `stage6-reviewed.tgz` remains unchanged
at SHA-256 `e80b298046bd4763e977545c04d505c9ace704ca16008c820c17c0cc0e8f3ca0`.
The new [manifest](manifests/2026-09-28-field-margin-dev58-rebind.json)
binds the exact r81/development runtime, new archive, raw replay transcript,
JUnit receipt and file manifest. No first-pass attempt was rerun or relabelled.

The intake r81 freeze has manifest SHA-256
`a9924e8926ad240b1e6c3aaaf57cc2896a262c3776ea33daa786cd6884ab4dc0`,
dev58 wheel SHA-256
`60ce811067e2c808b7ed0176bdb4572bf8bea322badc40b7eca3e8f42bc7090a`,
and 169/169 development catalog root
`sha256:61bb7e828098e244a0285bfb772f59a9f43e3d3576caa907d9ca769c09e5ae4d`.
An independent read-only Agent checked the frozen bindings, the changed
multi-coil exact contract, three direct dependencies and the discriminating
test. It gave a bounded go for resolving r80-v3's `current_a`/omitted-weights
ambiguity. The old r80-v3 no-go is preserved as the prior version's decision;
neither conclusion approves all 169 assets.

The dev58 wheel was installed into the project's local venv. An isolated
import resolved from that venv's `site-packages`. The ordinary `run_preview.py`
entrypoint exited 0, and all 24 project tests passed. The tests include
changed-coil and invalid-pressure ordinary-entrypoint copies, a repaired
retry, pressure-only evolution and identity collision. A separate installed
wheel probe confirmed that explicit `[0.25]*4` weights on a 2x2 section give
one quarter of the omitted-weight field at 1000 A for `psi_vac`, `b_r_vac`
and `b_z_vac`. The project uses those explicit weights for its declared
total-section current. The unchanged-input replay kept the vacuum CSV at
SHA-256 `37f94bb2d1e26cfdaf624c1c75dba3c13800984d861dd83ba4123b045515e416`
and the pointwise arithmetic CSV at
`844c007d99b440123d619c36051ed6f61028952a0774490a139eaade696ee454`.
The inherited history files were produced under dev49; equal bytes here do
not reassign their runtime lineage.

The new archive `build/verification/field-margin-dev58-rebind-20260928/field-margin-dev58-rebound.tgz`
has SHA-256 `e77513a4d73a2a4d46d8190bdadf43a010738a57bb4cee64d2a04896d78542f7`.
Its external receipt binds a manifest of 376 files; the archive has exactly
those files plus the manifest. A second independent read-only Agent pass
checked all 377 archive members against the manifest/receipt, the JUnit
result and the command transcript, and gave a bounded go to freeze this as
development compatibility evidence. The venv itself is excluded; reinstall
the bundled dev58 wheel before rerunning the project.

The result is a synthetic vacuum-field preview and a separately declared
pointwise arithmetic quantity. It is not a stability criterion, plasma
equilibrium, device prediction, fresh autonomous pass, expert approval,
trusted release or public v1. Host NumPy/SciPy were inherited rather than
installed hermetically. The project still has a crash window between its
final file replacements, and its delivery manifest does not bind wheel
version per delivery. This replay used the old project's mounted method
copies, not a new unseen solver context or a CodeFusion comparison.
