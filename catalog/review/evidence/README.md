# Review evidence

Minimal retained evidence for the audit verdicts. These files are copied from
the task scratch area into the review tree so a verdict can be replayed after
`/tmp` is cleaned. They are review evidence, not public contracts or package
data.

- `audit-d1.csv` .. `audit-d6.csv`: per-capability audit registers.
- `source-audit-collisions.md`: KN1DPy source parity/conflict/defect decisions.
- `source-audit-kinetic.md`: TORAX Coulomb and PDRK continuation decisions.
- `source-audit-equilibrium.md`: Pleiades axisymmetric/direct-inversion decisions.

When a verdict is superseded, update this directory and `VERDICTS.json` together.
