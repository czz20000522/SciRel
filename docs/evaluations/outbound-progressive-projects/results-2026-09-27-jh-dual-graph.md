# Two-TaskGraph Balmer-alpha project with a later observation table

This fresh Claude Code `2.1.281 --bare` session used the pending-unapproved
SciRel `0.1.0.dev49` wheel and complete 148/148 development catalog. The
[manifest](manifests/2026-09-27-jh-dual-graph.json) binds the inputs, three
methods, raw traces, autonomous archives, three frozen counterexamples,
four reviewer messages, and the final reviewed project. CLI model label was
`claude-fable-5`;
assistant messages reported `GLM-5.3-Flash`. Underlying model identity was not
confirmed. No call/token cap was set. Bare mode disabled automatic memory and
hooks, but the shared filesystem did not strictly isolate examiner and solver.
CodeFusion was not used.

The first user turn supplied a synthetic Johnson-Hinnov coefficient bundle
and four out-of-order profile rows. Claude found and called
`scirel.diagnostics.hydrogen-jh-balmer-alpha-emission`, a TaskGraph composing
the r-coefficient and Saha-population assets. It delivered a reusable command
and a per-`sample_id` photon-rate/emissivity CSV. A source-free external
installation of the bound wheel passed 10 project tests. The preview CSV hash
was `92c94b63...e095e75d0`. An unchanged rerun kept that CSV byte-identical
but unnecessarily appended redundant archive files. This was a first-pass
defect, not a repaired autonomous result.

The second user turn added an observation table in a different row order and
asked for neutral ground-state density and comparison with the original
prediction. Claude reopened catalog discovery, selected
`scirel.diagnostics.hydrogen-jh-balmer-alpha-ground-state-inversion` (a second
TaskGraph), and joined by `sample_id`. The original preview CSV remained
byte-identical; the inference CSV hash was `8797f700...a095e75d0`. In an
external extraction, 20/20 tests passed and the inferred densities agreed
with an independent synthetic reference: H02 `3.5e17`, H04 `9e17`, H01
`2.5e17`, H03 `8e17 m^-3`. This establishes one structure-specific two-graph
composition with project glue, not general multi-graph reliability.

The first independent negative probe changed H01's profile density and made
H02's observed cell invalid. The ordinary command exited 1, but the forward
CSV changed to `cb0cf467...54a2d` while the inference CSV stayed at
`8797f700...a095e75d0`; the current pair represented different input
revisions. The [counterexample](../../../build/verification/jh-dual-graph-20260927/stage2-partial-write-counterexample.tgz)
preserves the mixed state. The same session received symptom-level reviewer
feedback and changed the project to validate both stages before delivery. A
fresh extraction of that first reviewed archive passed 22 tests; an invalid
observation then left both CSVs, both metadata files, the log, and the archive
count untouched. Unchanged reruns stopped adding redundant archives.

The first reviewed version still had a provenance defect. After an ordinary
Windows rerun, the actual preview/inference CSV hashes were `92c94b63...` and
`8797f700...`, but both `.meta.json` files and run-log rows claimed the
in-memory LF-text hashes `92a47e43...` and `2675e46c...`. A separate
equivalent-decimal observation edit kept the inference bytes unchanged while
changing its source digest. The [second counterexample](../../../build/verification/jh-dual-graph-20260927/stage3-digest-counterexample.tgz)
preserves this state. A second symptom-level review made delivery hash and
write the same explicit CRLF bytes, checked an old meta against actual bytes
before citing its revision in an archive, and added focused tests. This is a
second review-assisted repair, not autonomous provenance reliability.

In a new source-free extraction of the second reviewed
[`stage4-reviewed.tgz`](../../../build/verification/jh-dual-graph-20260927/stage4-reviewed.tgz),
25/25 project tests passed. An ordinary unchanged run kept both CSV hashes and
16 archive files unchanged; each current meta's output hash matched the
actual on-disk CSV. The negative probe again exited 1 before changing either
table. An equivalent-decimal H02 input then produced identical output bytes
under a new input revision. Changing H04's observation by `1e6 W m^-3`
subsequently changed only the inference table (H04 inferred density became
about `9.121714e17 m^-3`), archived the old inference CSV, and left the
preview table unchanged. The archived inference bytes and sidecar both had
SHA-256 `8797f700...a095e75d0`; the current inference CSV and meta both had
`d35c606f...dbab40`. The archive cites the immediately preceding source
revision. Earlier revisions that produced identical bytes are traceable in
the run log, but the project does not preserve their full original input
contents. The external venv imported SciRel from installed `site-packages`;
it inherited NumPy/pytest from system site-packages, so the check was
source-free for SciRel, not fully dependency-hermetic.

The next packaging audit found that the documented ordinary
`run_balmer_alpha.bat` failed with `The system cannot find the path specified`
when run from that archive: it excluded the machine-local `venv/` but the
launcher unconditionally called `venv/Scripts/python.exe`. The
[entrypoint counterexample](../../../build/verification/jh-dual-graph-20260927/stage4-bat-entrypoint-counterexample.txt)
records the actual exit. A third reviewer message led Claude to add an
offline, bundled-wheel setup and a first-run launcher. A fresh extraction of
[`stage5-reviewed-entrypoint.tgz`](../../../build/verification/jh-dual-graph-20260927/stage5-reviewed-entrypoint.tgz)
created its own project-local venv and ran `.bat` successfully; 33 project
tests passed. The setup required an installed Python with NumPy/SciPy and
did not fetch dependencies. It was nevertheless unsafe: its documented
optional runtime directory was passed to `shutil.rmtree()` whenever an
existing environment failed version verification. Code review identified a
reachable path to deleting an unrelated directory. This was not exercised
against real user data and was not accepted as the final delivery.

A fourth reviewer message removed recursive deletion. The final
[`stage6-reviewed-safe-setup.tgz`](../../../build/verification/jh-dual-graph-20260927/stage6-reviewed-safe-setup.tgz)
is SHA-256 `a301af55...9f65550c`. In a new extraction, the ordinary `.bat`
created a project-local venv offline from the bundled dev49 wheel, then
delivered both original CSV byte streams. An existing unrelated directory
caused `setup_runtime.py` to exit 1; its sentinel file remained at SHA-256
`f67f8414...7cc70eb0b09`. An invalid owned runtime is moved aside rather
than deleted. The extracted project passed 38/38 tests without the earlier
Python 3.14 docstring warning. Its scientific `run_balmer_alpha.py` SHA-256
`87874147...37cb9c5` is unchanged from the second reviewed version; the
preview/inference CSV hashes remain `92c94b63...e095e75d0` and
`8797f700...a095e75d0`, and the archive still contains 16 prior files.
This is four-review-assisted development evidence, not autonomous delivery
integrity. The local venv uses system-site NumPy/SciPy; the bundled SciRel
wheel is digest-checked before offline installation, but dependencies are
not hermetically vendored. An unknown pre-existing default runtime directory
requires a human to inspect and move it before the `.bat` can initialize.

Scientific and delivery limits remain. The coefficient payload is synthetic,
unvalidated atomic data: its r table is flat, three sample temperatures are
clipped to the roughly 10 eV r-table edge, and source-term magnitudes near
`10^51`-`10^56 m^-3 s^-1` are not physical claims. The result is volumetric,
not observed line-integrated brightness or a device prediction. The project
uses a pending-unapproved development wheel, not an expert-approved or public
v1 release. The scientific project code prevalidates both stages but does not
make a two-file transaction: a process kill can still split a table from its meta,
split the two tables, or omit the final run-log entry. Byte hashes make those
states detectable, not impossible. Source attribution is digest-based; prior
raw input snapshots are not retained by the reusable project. No SciRel
scientific source, exact document, catalog, or CodeFusion kernel code was
modified by this evaluation.

To recheck frozen references, run
`python scripts/verify_outbound_evaluation_manifests.py` and
`python -m pytest tests/test_outbound_evaluation_manifests.py -q`. To replay the
final project, extract `stage6-reviewed-safe-setup.tgz` outside the SciRel
source tree. On Windows with Python 3, NumPy and SciPy already available, run
`run_balmer_alpha.bat` from `solver/`; it creates the local environment
offline from the bundled wheel. Then run
`venv/Scripts/python.exe -m pytest -q` to repeat the 38 project tests.
