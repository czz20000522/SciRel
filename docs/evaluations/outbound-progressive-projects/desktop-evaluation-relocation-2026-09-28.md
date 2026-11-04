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
for `scirel*` was zero after this phase; the retained non-environment data
remains available in the ignored task directory. Those 75 retained directories
occupy 124,647,556 bytes, a reduction of 3,083,766,919 bytes from their
original Desktop footprint.

## Non-prefixed supplement

A full directory inventory by creation date found nine more September 26-27
outbound evaluation copies on D: (none on C:), occupying 10,205,562 bytes.
They belong to the frozen STIX per-shot and spectral-pair cases, whose stage
archives, raw traces and manifests remain unchanged. No active process command
line referenced them. The exact-source dry run is
`build/verification/desktop-cleanup-20260926-27/supplement-plan.json`, SHA-256
`bfe94b045539bbd9ce17dbe1e73a5cd944548494d430d32afe871e4be13f0bc1`.
It binds 725 file paths, lengths and SHA-256 values; all matched after the
move. There were no virtual environments or reparse points in this group.

Each old `D:/Users/26569/Desktop/<name>` now maps to
`build/verification/desktop-cleanup-20260926-27/retained/unprefixed/<name>`:

| STIX per-shot | Spectral pair |
| --- | --- |
| `stix-per-shot-independent-20260926` | `spectral-pair-stage1-independent-20260927` |
| `stix-per-shot-failure-independent-20260926` | `spectral-pair-stage2-independent-20260927` |
| `stix-per-shot-final-independent-20260926` | `spectral-pair-stage3-independent-20260927` |
| `stix-per-shot-final-failure-20260926` | `spectral-pair-holdout-independent-20260927` |
| | `spectral-pair-holdout-reviewed-independent-20260927` |

After this supplement, all 84 project directories and 8,082 files remain in
the ignored task directory (134,853,118 bytes). A `-Force` inventory of *all*
directories created since September 25 under both Desktop roots found zero
remaining; the check did not rely on a project-name prefix. Overall the two
phases removed 3,083,766,919 bytes of rebuildable environments from the
original 3,218,620,037-byte Desktop footprint.
