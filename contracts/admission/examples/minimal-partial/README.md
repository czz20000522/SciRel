# Minimal partial submission input

This is a wire-format example. The identity callable and status record do not
claim a physical capability, source fidelity or scientific approval.

From the repository or exported tools directory, use:

```text
python scripts/prepare_admission.py --payload contracts/admission/examples/minimal-partial/payload --metadata contracts/admission/examples/minimal-partial/metadata.json --output <new-FINAL-directory>
python scripts/validate_admission.py <new-FINAL-directory> --output <outside-FINAL-report.json>
```

The metadata intentionally omits all generated control fields and counts.
The payload has three members; the generated `FILES.json` must list five:
`FINAL.json`, `LICENSE.txt`, `PATH_MAP.json`, `candidate.py`, and
`evidence/status.json`. The generated `PATH_MAP.json` is exactly `{}\n`.
`payload_bytes` includes the stabilized serialized `FINAL.json` size.

For a direct stored-member alias, add
`--path-map contracts/admission/examples/minimal-partial/aliases.json` to the
producer command and choose another new output. The alias resolves to the
same stored `candidate.py`; it does not add a duplicate payload member.

Run from an unrelated working directory by using absolute paths to the script,
payload, metadata and a new output. No receiver checkout, scientific runtime,
private method, network access or manual control-file edit is needed.

Use a new output for each changed input; the producer refuses overwrite. Never
use the producer or `--emit-root` to update an existing frozen submission.
