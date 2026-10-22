# Human-review decisions pending

Status: review in progress. Released rows remain as the decision record; pending rows are not exposed while listed.

| item | asset(s) | question | owner | decision | evidence required |
| --- | --- | --- | --- | --- | --- |
| Coulomb-log model | `scirel.physics.coulomb-ii` | Sauter 1999 fit vs NRL 2013 Eq. c; current +0.4388 lnΛ difference | scientific owner | pending | chosen formula, reference, regression |
| Collision fits | 15 held collision/rate/matrix/omega assets | accept fit limitation or supply external physical reference | collision/atomic owner | pending | external fixture or written limitation |
| Parallel-EM seed | `scirel.kinetic.parallel-em-continuation` | define seed/branch policy or restrict envelope | kinetic owner | released 2026-10-22 | fail-closed policy + regressions + docs/validator |
| Axisymmetric mask | `scirel.equilibrium.axisymmetric-anisotropic-picard` | unified strict-bool policy or documented coercion | equilibrium owner | released 2026-10-22 | strict-bool policy + regressions + docs/validator |
| Direct inversion release | `scirel.inference.direct-anisotropic-inversion` | restore/bind exact admitted graph; re-audit with released axisymmetric forward | inference owner | pending | exact graph artifact + re-audited composition |
| Quarantine refactor | all held code | move candidates out of `src/scirel` and public catalog | maintainer | pending | package/import-surface proof |

When a decision is made: update `HOLD.json`/`VERDICTS.json`, add the evidence,
run `scripts/review_gate.py --check`, rebuild docs, and only then expose.
