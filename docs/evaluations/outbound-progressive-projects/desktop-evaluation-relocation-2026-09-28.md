# Desktop evaluation workspace relocation (2026-09-28)

The 75 `scirel*` directories left on the two user Desktops by the September
26-27 outbound trials occupied 3,208,414,475 bytes (D: 71, C: 4). Running
process command lines showed no reference to those paths at cleanup time. The
original trial traces, frozen stage archives and manifest bindings were left
unchanged.

The cleanup plan is
`build/verification/desktop-cleanup-20260926-27/plan.json` (SHA-256
`0d0b5f4e806025da61d53d5195a147eb67629d67b1cac4370bb39f74bdd3bf3c`).
It records the 75 exact source and destination paths plus file-level SHA-256
for the first 70 relocated directories. The remaining five were separately
bound by `relocation-plan.json` (SHA-256
`720055c3a4576e14324e8f1fd185780eeeb5c007a6d2aacc3bbfe0bf39edc7d2`).
All 7,357 non-environment files matched after relocation. These operational
records and retained directories are ignored local evidence under
`build/verification/desktop-cleanup-20260926-27/`.

Five old Desktop paths appear directly in prior result or independent-finding
prose. Those references record where a past run or probe occurred; they do not
require that path to remain executable. Their current locations are:

| Historical D: Desktop directory | Current path under `build/verification/desktop-cleanup-20260926-27/` |
| --- | --- |
| `scirel-balmer-independent-20260927` | `retained/D/scirel-balmer-independent-20260927` |
| `scirel-balmer-final-independent-20260927` | `retained/D/scirel-balmer-final-independent-20260927` |
| `scirel-hydrogen-stage1-note-probe-20260927` | `retained/D/scirel-hydrogen-stage1-note-probe-20260927` |
| `scirel-hydrogen-final6-20260927` | `retained/D/scirel-hydrogen-final6-20260927` |
| `scirel-dev39-thermal-regression-20260926` | `retained/D/scirel-dev39-thermal-regression-20260926` |

The other 70 directories follow the same relocation rule, separated into
`retained/D/` and `retained/C/` by original drive. Their names and individual
file digests are in the cleanup plan. After verification, 22 ordinary
rebuildable `venv/.venv` directories were removed. Two `.venv` junctions were
preserved without recursive deletion; they point to a former test environment
and are not a runnable environment in the retained copy. Fresh replay should
create a new environment from the pinned wheel and catalog. The Desktop count
is now zero; the retained non-environment data remains available in the ignored
task directory. The retained directories occupy 124,647,556 bytes, a reduction
of 3,083,766,919 bytes from the original Desktop footprint.
