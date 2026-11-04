# Quasineutral leaf catalog closure

Status: development catalog documentation, not new scientific admission,
expert approval or public release. SciRel comparison base: `402f59a`.
The historical 52-entry Pleiades ledger and the clean intake snapshot
`647d5db` were read as development evidence. Intake r81-v1 remains
`pending_unapproved`, with no qualified L1 delivery root. The current SciRel
implementation and maintained tests define the runtime behavior documented
here; no scientific source module or public callable changed.

## Relations and scope

Two existing no-dependency leaves now have independent
`scirel.asset-document.v1` records. Quasineutral reference density evaluates
`n_e,ref=Z_i*n_i,ref`, accepts zero density and rejects an unrepresentable
product. Boltzmann electron state evaluates a supplied potential, applies
the saved `[-700,700]` exponent clip and float64 `tiny` floors, and returns
electron density, pressure and three neutrality residuals. The residual
named `charge_residual_m3` is a number-density difference in `m^-3`, not
charge density in `C/m^3`. Its derived values have no post-computation
finiteness guard. Both leaves broadcast fields without proving physical
coordinate alignment.

The selector resolves each newly documented callable to its canonical asset
ID and retains the historical mirror-quasineutral graph plus two outer graph
tests as reverse dependents. The iterative potential solver and graph itself
still lack exact documents; their feedback and failure contracts require
separate review before this relation family is represented as a complete
documented TaskGraph.

## Evidence and limits

Focused local regressions cover the Boltzmann zero-density floor and exponent
clip, and reference-density multiplication overflow. The isolated worktree
and main checkout each ran
`pwsh ./scripts/check.ps1 -Mode affected -BaseRef 402f59a`: 82 passed.
All 69 exact documents passed runtime-signature and executable-example
validation through that gate. A structured callable difference between the
historical ledger and catalog yields 45 still-undocumented ledger assets;
coverage is `partial: 69/114`. Main commits `d950285` and `0a0de05` carry
the documents, regressions, navigation and two README count changes.
Other owners' README and extraction edits remain unstaged.

These checks establish the stated current SciRel behavior on tested inputs,
not physical quasineutrality across arbitrary coordinate grids, all extreme
float cases, qualified D1 provenance, expert approval or distribution
licensing. No wheel or release was built.
