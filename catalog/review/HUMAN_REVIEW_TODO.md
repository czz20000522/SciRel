# Human-review decisions pending

Pending assets are not exposed. Resolved decisions show up in `VERDICTS.json` and Git history.

| asset | question | what is needed |
| --- | --- | --- |
| `scirel.inference.direct-anisotropic-inversion` | Can the composition be released? | The exact admitted graph artifact, then rerun composition and physical-closure tests |
| `scirel.equilibrium.finite-frc-feedback` | Are model and contract right? | Human review. The contract example uses an undefined `inputs`, and its import path must be restored on release |
| `scirel.equilibrium.finite-limited-boundary` | Are model and contract right, and which public name is canonical? | Human review. The module exports two different functions, `solve_limited_boundary` (in the contract) and `solve_finite_limited_boundary` (undocumented), plus four undocumented helpers |
| `scirel.kinetic.atomic-slab-transport` | Are model and contract right? | Human review. The contract example uses an undefined `inputs` |
| `scirel.kinetic.multiscale-sat123` | Are model and contract right? | Human review. The contract example uses an undefined `inputs` |

`scripts/review_harness.py --check` fails until these examples are repaired; the failure is expected while they are held.

To release an asset: record the decision in `VERDICTS.json` and `HOLD.json`, move its contract to `catalog/examples/` and its code to `src/scirel/`, restore the domain exports and the canonical binding, repair the example, restore its reader and handbook entries, then run `scripts/check_all.py`.
