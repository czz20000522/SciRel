# Anisotropic toroidal current catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `19e1fc0`.
The maintained implementation and direct tests were compared with the
historical Pleiades development mapping and pending intake candidate;
SciRel and intake source text matched after LF normalization. Intake
r81-v1 remains `pending_unapproved`; the qualified D1 delivery root was
recently checked read-only and contained zero entries. No qualified D1
input was consumed.

`compute_anisotropic_toroidal_current` now has a current-version
`scirel.asset-document.v1` record with the force-balance Operator as an
exact dependency. It evaluates the latter with full parallel and
perpendicular pressures, then again with both pressures set to `p_perp`.
The second `J_phi` is `gradp_term`, and the anisotropy term is the
difference. That named remainder is not an independently discretized
pure-curvature formula. A new direct regression checks the zero axis
column and rejection of negative pressure. Prior numerical assertions
and tolerances remain intact. No scientific source or public API changed.

The selector regression retains the free-boundary anisotropic Picard
graph as a reverse consumer. Catalog coverage is `partial: 88/114`;
structured public-callable comparison with the 52-entry historical
ledger finds 26 matches and 26 assets without exact documents. All 88
runtime signatures and examples validated in the isolated worktree.
The isolated worktree and main checkout each passed 88 affected tests;
the latter used `pwsh ./scripts/check.ps1 -Mode affected -BaseRef 19e1fc0`.

The regressions cover selected discrete isotropic and rotating-field
states. They do not establish a general pressure closure, plasma-domain
masking, containing-graph convergence, expert recognition or public
distribution licensing. No wheel or release was built.
