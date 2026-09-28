# Mirror plasma Green catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `070be32`.
The maintained implementation and direct tests were compared with the
frozen historical Pleiades mapping and pending intake candidate. SciRel
and intake implementation text matched. Intake r81-v1 remains
`pending_unapproved`; the qualified D1 delivery root was read-only checked
and contained zero entries. No qualified D1 input was consumed.

`build_mirror_plasma_flux_green` now has a current-version
`scirel.asset-document.v1` record. It evaluates first-plane circular
filament flux columns, then fills a dense C-order `[Z,R]` source/target
matrix using axial reflection indexing. Its grid requires strictly
increasing nonnegative R and uniformly spaced, reflection-symmetric Z.
Axis-source columns and nonfinite kernel elements use the implemented zero
convention. The matrix includes neither cell area nor current contraction.
No scientific source or public API changed.

A new direct regression compares the full reflected matrix on one symmetric
grid with separate dense circular-filament columns. Existing direct tests
cover the first-plane formula, axis-source zeros, reflection blocks, shape
and an invalid asymmetric grid. Catalog coverage is `partial: 83/114`;
structured callable comparison with the historical 52-entry ledger finds
21 matches and 31 assets without exact documents. The isolated worktree
and main checkout each passed 84 affected tests, with the latter using
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 070be32`. Runtime
signatures and examples executed for all 83 documents; the deterministic
catalog partition test passed.

These tests do not establish arbitrary-grid validity, resolved self-fields
or large-matrix suitability. This record uses `psi=R A_phi` and
`Wb/rad/A`, while the existing vacuum-field documents label flux response
`Wb/A`; public cross-asset unit naming remains for science-owner
adjudication. Distribution licensing and expert recognition remain pending.
No wheel or release was built.
