# Delivery package format

This is a receiver-agnostic delivery format. The receiver may supply a concrete admission
contract and public tools at runtime; bind their exact revision or bundle identity with the
source and method. Use that single supplied interface without embedding receiver identity
in the package or inspecting receiver-private implementation to guess its format.

## Required content

- candidate inventory: capability id, scientific purpose, type (operator/function or
  task graph/composition), source anchor, duplicate family, uncertainty/coverage;
- selected candidate payload: implementation and direct tests;
- contracts: ports, units/axes, state/order, failure semantics, applicability and limits;
- correctness evidence: source parity, independent oracle, invariants, boundary probes, or
  explicit NOT_RUN with the missing evidence named; retain the frozen inputs, expected
  observations and decoding/comparison rules needed by the next evidence consumer;
- license/attribution and a claim ceiling;
- a manifest binding every delivered byte (path, bytes, sha256), with the control files
  bound to each other.

## Delivery rules

- The package must be self-contained and reviewable without the source project.
- Do not encode receiver-specific catalog IDs, paths, acceptance expectations or project
  identity.
- Source probes and internal staging may remain as evidence, but must not become a required
  runtime dependency or implicit input channel.
- Keep necessary capability-level replay evidence outside the callable ImportIntake bundle
  and bind it as delivered evidence. A PASS summary, digest or aggregate error alone cannot
  replace an oracle that the receiver still needs to replay. Follow the
  [evidence lifecycle](evidence_persistence_boundary.md) for neutralization and retirement.
- The receiver decides acceptance, overlap and integration; the decomposition line ends at
  delivery and evidence.

## Public admission tools

Bind the applicable source-side package tools as well as the outer admission tools:
[`validate_import_intake_package.py`](../scripts/validate_import_intake_package.py),
and, when the stage/profile claims the existing discovery entry contract,
[`validate_asset_entry.py`](../scripts/validate_asset_entry.py). Supply their actual
interface and dependencies to the source executor. Check a small structural/discovery
payload early in the authorized isolated environment; a custom discovery probe or
outer manifest PASS does not establish these existing interfaces. Read the entry
validator rather than inventing another list/describe/find protocol.

Source anchors may be supplied through the package tool's existing private
`--evidence-matrix` input; retain that mapping with the source custodian when making a
neutral transfer. Package entry changes must preserve scientific initialization,
shared state and failure order. Do not infer an asset count from callable count,
split shared state to fit directories, or add a meaningless entry alias to pass a gate.

At environment setup, bind the supplied live contract and executable producer/validator,
including their revision or bundle identity. The runtime provider can export the public
surface with `python scripts/export_admission_tools.py --output <NEW-DIR>`; the export
retains `scripts/` and `contracts/admission/` paths and needs no receiver `src`, catalog or
private implementation. Read the supplied contract and tool help rather than asking a chat
to invent the format. This methodology does not duplicate schema fields or the ROOT algorithm.

The author supplies semantic metadata such as scientific scope, limitations, claim ceiling
and licence obligations using the provided tool's documented metadata input. The canonical
producer generates all four controls (`FINAL.json`, `FILES.json`, `PATH_MAP.json`,
`ROOT.sha256`), including membership, sizes and bindings; do not hand-roll or patch them.

```text
python <admission-tools>/scripts/prepare_admission.py --payload <payload-dir> --metadata <metadata.json> --output <NEW-FINAL> [--path-map aliases.json]
python <admission-tools>/scripts/validate_admission.py <FINAL> [--output <OUTSIDE>/report.json]
```

Exercise this format path early with a small structural smoke payload in a new owned output,
before expensive packaging work. Validate the real successor after producing it. An existing
frozen submission is read-only: validate it without regenerating its controls or writing a
report inside it. If tools, contract or packaging disagree, preserve the machine-readable
failure as HOLD for that handoff and continue independently executable authorized work;
repair packaging without repeating valid scientific computation. Unknown scientific meaning
remains an explicit owner question, never a guessed metadata value.
