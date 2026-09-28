# Field-to-margin interrupted delivery recovery (2026-09-28)

An Agent resumed the existing field-to-margin dev58 project to close a D3
user-delivery gap. The source freeze `field-margin-dev58-rebound.tgz` remains
unchanged at SHA-256
`e77513a4d73a2a4d46d8190bdadf43a010738a57bb4cee64d2a04896d78542f7`.
This is a repair of that reviewed project, not a new autonomous solution or
a recheck of the D1/D2 scientific derivation. The exact runtime is the
pending-unapproved dev58 wheel, SHA-256
`60ce811067e2c808b7ed0176bdb4572bf8bea322badc40b7eca3e8f42bc7090a`.

An interruption between the two canonical CSV replacements had left the
first file's new bytes without a delivery record. A retry recovered the
numeric pair but failed to record those bytes. A byte-identical row from a
different result file could also suppress recovery or misattribute preserved
history. The corrected project binds manifest lookups to each result file,
records an interrupted delivery on the same-input retry, and distinguishes
compute/check errors from possible partial delivery writes in its error text.
The [frozen project record](../../../build/verification/field-margin-crash-recovery-20260928/recovery-evidence.md)
retains the observed failing assertion, correction and focused commands.

The affected history and entrypoint suites passed **14/14**. The ordinary
`run_preview.py` entrypoint exited 0. Independent CSV reading found four
vacuum-field and four pointwise-margin rows, including Q1 margin
`+5.001294e+03 Pa`. An unchanged-input rerun kept both canonical CSVs and
`results/history/MANIFEST.csv` byte-identical. The new archive has 375
verified members, with no `venv` member. The [manifest](manifests/2026-09-28-field-margin-crash-recovery.json)
binds its SHA-256, file manifest, JUnit receipt and record.

The project still cannot guarantee an atomic two-file replacement during a
crash. A write failure requires inspection and a same-input retry. The
pointwise margin is a synthetic sampled arithmetic value, not a plasma
stability or design conclusion. This case does not approve the development
wheel or establish general outbound reliability.
