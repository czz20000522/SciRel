# Independent two-table project: useful partial delivery, assisted ownership repair

This synthetic two-turn user project tested whether a local neutral harness could
discover and use two independent SciRel relations, then respond to a new request
that the supplied data could not support. Claude Code `2.1.281` ran one resumed
session with three visibly read SciRel usage skills, the unapproved dev39 wheel
(`be5a2a2b...1eef9b8`) and complete 126/126 development catalog
(`434249fe...86e3fca`). Its CLI model label was `claude-fable-5`, while message
events said `GLM-5.3-Flash`; the underlying model was not independently verified.
There was no call or token cap, and examiner/solver shared a host filesystem.
Claude project auto-memory was enabled and pre-existing SciRel notes were
present; the trace does not show a memory-body read, but this was not a
memory-isolated blind trial. Claude also wrote case notes to that shared
memory, which is outside the frozen project archive and was not deleted.
The [manifest](manifests/2026-09-27-dd-dual.json) binds inputs, method bytes,
five project archives, all raw traces and the independent replay script.

The first autonomous request supplied separate temperature and velocity-pair
CSV tables plus a note explicitly denying that they were measurements of one
plasma. Claude found the Bosch-Hale DT reactivity and D(d,n)3He lab-neutron
energy exact assets without being given asset IDs. It converted m/s to cm/s,
normalized one non-unit detector direction, kept the tables separate, wrote a
reusable Python entrypoint and repaired its own initial test errors. The
[first archive](../../../build/verification/dd-dual-20260927/stage1-autonomous.tgz)
ended with 11 passing project tests. An independent raw-CSV-to-asset-call replay
matched all three reactivities and two neutron energies from the installed
wheel; an extracted ordinary rerun preserved both result CSVs byte-for-byte.
The first project kept those CSVs on bad input but replaced its only successful
`run_record.json` with the failed-attempt record.

The second autonomous user turn supplied only a detector efficiency of 0.12
and asked for count rates. Claude correctly withheld count-rate numbers, reopened
the catalog, and delivered a per-case missing-input ledger while retaining both
first-turn CSVs. Its [second archive](../../../build/verification/dd-dual-20260927/stage2-autonomous.tgz)
passed 16 project tests. A latent code branch nevertheless computed three
numeric rates when an examiner copy supplied five missing numeric fields **but
no emission or detector-geometry model declaration**. Thus the autonomous
project still chose isotropic/far-field physics for a future user. It also
asked a normal user to edit JSON, and its failure path later overwrote the
last successful missing-input ledger. Correctly refusing the current request
did not establish a safe reusable project.

Three symptom-level reviewer messages are preserved in the manifest and traces.
The first made model declarations mandatory before any rate calculation and
separated failed `run_record` from the last successful one. An independent
negative rerun confirmed numeric fields alone produced no `count_rates.csv`,
but exposed the still-overwritten ledger. The second repair wrote failed
attempt ledgers separately and corrected the README: the user gives facts and
material model choices in ordinary language; the Agent maintains files. A
fresh extraction then exposed a third defect that earlier test order had
hidden: the [stage-4 archive](../../../build/verification/dd-dual-20260927/stage4-reviewed.tgz)
kept three CSVs byte-identical on an unchanged rerun but rewrote the success
record solely because it encoded the original absolute workspace path. A
third review changed records to store portable output file names and added a
moved-project regression. The
[final reviewed archive](../../../build/verification/dd-dual-20260927/stage5-reviewed-final.tgz)
is therefore **three-review-assisted**, not an autonomous end-to-end pass.

Independent extraction of the final archive ran the ordinary entrypoint
*before* any tests and kept the three delivered CSVs plus successful run
record byte-identical. Then 27/27 project tests and the separate raw-input
numeric replay passed. A numbers-only counterexample did not
emit a rate. Zeroing one sightline made the entrypoint exit 1 while preserving
those four files exactly, with the failed ledger and record written under
separate names. The SciRel import came from the installed wheel in
`site-packages`; the Python 3.14.3 venv reused host dependencies, so this is
not an offline dependency installation or a strict filesystem blind test.

Only synthetic development arithmetic and software delivery are established.
The user's 0.12 efficiency still cannot determine a count rate; no user-supplied
densities, emitting volume, detector geometry or model choice were provided.
The future declared-model rate path has only manufactured test values, no real
device or angular-distribution validation. The velocity-pair rate remains a
catalog capability gap. The scientific wheel is pending expert review and
public licensing; no CodeFusion product result, trusted release or public v1
is claimed. This is a bounded neutral-harness comparator, not a request for a
SciRel-specific CodeFusion kernel feature.
