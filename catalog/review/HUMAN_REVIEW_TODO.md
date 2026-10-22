# Human-review decisions pending

Status: review in progress. Released rows remain as the decision record; pending rows are not exposed while listed.

| item | asset(s) | question | owner | decision | evidence required |
| --- | --- | --- | --- | --- | --- |
| Direct inversion release | `scirel.inference.direct-anisotropic-inversion` | restore/bind exact admitted direct-inversion graph artifact, then rerun composition + physical-closure | inference owner | pending | exact graph artifact id/hash + re-audited composition |
| Coulomb-log model | `scirel.physics.coulomb-ii` | resolved by TORAX source: Sauter 1999 Eq. 18e; no NRL reassignment | scientific owner | released 2026-10-22 | TORAX source + regression |
| Collision family | 15 KN1DPy collision assets | source parity / conflict repaired / source-defect repair accepted; no external physical calibration claimed | collision/atomic owner | released 2026-10-22 | source-audit-collisions evidence |
| Parallel-EM seed | `scirel.kinetic.parallel-em-continuation` | fail-closed continuation accepted as SciRel policy; explicit seed/branch declared | kinetic owner | released 2026-10-22 | source-audit-kinetic + regressions |
| Axisymmetric mask | `scirel.equilibrium.axisymmetric-anisotropic-picard` | strict bool mask + floor-before-closure accepted as SciRel policy | equilibrium owner | released 2026-10-22 | source-audit-equilibrium + regressions |
| Quarantine refactor | all held code | completed: review tree outside installed package; wheel proof zero held | maintainer | released 2026-10-22 | wheel-exposure proof |

Released rows are retained as decision history; they are not pending work.

When a decision is made: update `HOLD.json`/`VERDICTS.json`, add the evidence,
run `scripts/review_gate.py --check`, rebuild docs, and only then expose.
