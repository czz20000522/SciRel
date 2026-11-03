# Executable result delivery

Use the [delivery helper](../scripts/delivery.py) from this skill. It reads saved CSV data, computes statements, and renders the answer/report and optional plots. It has no scientific solver or agent runtime. It does not evaluate arbitrary prose or certify a model, a declared unit, or the origin of a conversation file.

Write a UTF-8 JSON specification beside the output CSVs. Paths are relative to that specification; absolute paths also work. Only the documented fields are accepted. No expected result values, PASS flags or free-form conclusions can be supplied.

```json
{
  "schema": "scirel.result-delivery",
  "tables": {
    "measurements": {
      "path": "measurements.csv",
      "units": {"time_s": "s", "temperature_K": "K"},
      "coordinates": ["time_s"],
      "expected_rows": 3
    }
  },
  "claims": [
    {"op": "range", "table": "measurements", "column": "temperature_K"},
    {"op": "threshold", "table": "measurements", "column": "temperature_K", "relation": ">", "value": 350}
  ],
  "plots": [{"table": "measurements", "x": "time_s", "y": "temperature_K"}]
}
```

The illustration is an input shape, not a default model or criterion. Choose columns, units and criteria from the confirmed request and selected scientific contract. CSV column names must be identifiers; units are short ASCII scientific expressions (`1` means dimensionless). No value conversion is implicit. Extra CSV columns may remain undeclared, but every column used by a claim, coordinate or plot needs units. All declared values must be finite and rows well formed.

## Coverage and conditions

- Set `expected_rows` from the requested output coverage, not from whatever the solver happened to return.
- When particular coordinate groups are required, add `expected_groups` to the table: `{"columns":["coordinate_a","coordinate_b"],"values":[[0,0],[0,1]],"rows_each":3}`. The actual set and multiplicity must match exactly. This detects a terminal-point diagnostic offered as a scan. Do not attach a full-scan scope to a one-row diagnostic table.
- Optional top-level `premises` is a list of `{"path":"request.txt","quote":"exact text from that file"}`. Save the supplied request/clarification faithfully, then quote it without inferred wiring, causes or conditions. The tool checks exact inclusion and binds bytes; the host remains responsible for conversation identity. These are quoted inputs, not verified physics.

## Statements

Each operation consumes the whole declared table, without a hidden row filter:

- `range`: `op, table, column`; returns min, max, maximum absolute value and actual row scope.
- `threshold`: adds `relation` (`>`, `>=`, `<`, `<=`) and finite `value`; counts matching rows. A zero count establishes only that no saved values meet this condition. Derive the scientific criterion from clarified intent.
- `relative_deviation`: adds `at`, a coordinate-to-value mapping identifying exactly one saved reference row. Optional nonnegative `coordinate_atol` allows explicit coordinate rounding tolerance (default zero). Reports reference value and maximum absolute relative deviation; a zero reference is rejected. It does not assert engineering suitability or a scaling law.
- `compare`: adds `reference` (another table), `keys` (coordinate columns), nonnegative `atol`, `rtol`. Requires unique, identical full key sets and identical declared units, then computes `abs(actual-reference) <= atol + rtol*abs(reference)`. Failed comparison remains failed. Same bytes are disclosed; a successful comparison is never called independent physics validation. Degenerate spectra needing multiset matching require their own scientific check; do not silently drop modes to fit unique keys.

Diagnostics may be saved as a separate table with their actual coordinates. Its statement retains that table's scope. This tool does not reinterpret residuals, convert backward error to forward accuracy, or establish independence from field names. An unsupported scientific inference stays outside the checked report; establish a suitable domain method before delivering it as a conclusion.

## Build, replay and deliver

```sh
python3 <skill>/scripts/delivery.py build result-spec.json --out checked
python3 <skill>/scripts/delivery.py verify result-spec.json --out checked --answer checked/ANSWER.md
cat checked/ANSWER.md
```

Outputs: `ANSWER.md`, `REPORT.md`, `checks.json`, and optional `figure-1.png` etc. Plots read the saved coordinates without rescaling, and labels use those same declared columns/units. Matplotlib is required only for plots; use its installed environment. Plotting uses ASCII labels and avoids missing Chinese-font warning loops.

Verification re-reads current CSVs/conditions, recomputes statements and plots, and compares them with delivered artifacts. A changed CSV, condition, spec, report, answer or plot fails replay. The local hashes are consistency bindings, not signed receipts, authority or proof against an agent that rewrites inputs and rebuilds them.

Exit `0`: bounded statements consistent. Exit `3`: valid report with a failed numerical comparison; disclose it, do not claim completion. Exit `2`: invalid/incomplete input or altered output. Fix the real cause and rebuild; never edit a generated PASS flag, change a tolerance to pass, or reuse a stale report after failure.

Verification returns `answer_text`, bounded numerical statements including generated data/figure links. Preserve those statements unchanged (or deliver the report file directly). Additional scientific interpretation needs separate evidence and explicit limits. If the host exposes a draft answer file, pass that actual draft to `--answer`; the verifier does not intercept future chat text or control the host's final message. No host-specific integration is required to run this component.

For a host that supports final-message checks, expose this same `verify --answer <actual-draft-file>` operation. The host passes the draft and handles retry/delivery; all numerical and statement checks remain in this plugin. A consistency result for ANSWER.md alone says nothing about a different message emitted later. This optional consumer contract is not a SciRel session, scheduler or interception service.
