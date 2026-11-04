# Source Behavior and Controlled Repair

Use this reference when a source snapshot is executable but lacks an external physical oracle,
or when a replay exposes a reproducible shape, index, allocation, or producer/consumer defect.
The method separates what can be recovered from source control flow from what still needs an
independent scientific or numerical basis.

## Split the claim before investigating

Record these as separate fields in the gap or evidence receipt:

| Claim lane | What may establish it | What it cannot establish |
| --- | --- | --- |
| `termination_semantics` | Source control flow, call sites, explicit normal/failure markers, bounded instrumentation, and terminal-state replay | Physical correctness or universal convergence |
| `source_behavior` | Identical explicit inputs and source-free replay of the declared source snapshot | That the source itself implements the intended science |
| `relation_or_numerics` | Independently reassembled equations, units, limits, invariants, manufactured cases, residuals, refinement, or justified external references | Unrecorded source-only branches or hidden state |
| `source_repair` | A reproducible defect, source-intent anchors, minimal patch, differential tests, and a new bundle revision | A general scientific-correctness claim without an independent oracle |

Never collapse `termination_semantics` or `source_behavior` into `relation_or_numerics`.
Source-side numeric parity under pre-registered, scale-aware tolerances can close only the
`source_fidelity_verified` lane with an explicit claim ceiling. It does not establish relation or numerical
correctness. Source extraction records a demonstrated source anomaly without changing its scientific meaning;
an authorized correctness/repair owner decides whether to create a corrected successor. Reserve
`validation_oracle_gap` for the specific claim whose required basis is unavailable; do not block unrelated
source-behavior evidence merely because an external physical reference is absent.

## Source-derived termination semantics

Treat termination as a semantic contract, not a process exit code. Build a source-behavior oracle
only for the declared source scope:

1. Map normal return, `STOP`/abort paths, explicit failure markers, iteration limits, threshold
   comparisons, and whether the check occurs before or after the state update.
2. Trace the call sites that interpret each marker and list the complete terminal output/state
   schema, including discrete status, selected branch, iteration count, and failure fields.
3. Instrument a disposable source workcopy when static inspection does not expose the marker. Capture
   process status and semantic status separately, with a normal case plus applicable threshold,
   boundary, nonconvergent, and invalid-input cases.
4. Replay identical explicit inputs in the source-free bundle and compare the semantic marker,
   complete terminal schema, shapes, selectors, and discrete state exactly. Use pre-registered,
   scale-aware tolerances only for declared floating fields.

The resulting evidence may earn `source_behavior_verified` or a bounded local
`functional_reassembly_passed` claim. Source-side parity on canonical and holdout cases may earn
`source_fidelity_verified`; it does not close `relation_or_numerics` or earn independent physical-correctness
evidence. Retain `validation_oracle_gap` only for the claim whose required basis is unavailable.

## Controlled source repair protocol

This protocol may restore evidenced source intent for shape/interface/state defects only under an authorized
correctness/repair scope. For a wrong scientific relation use
[scientific correction](../../scientific-relation-implementation/references/scientific-correction.md).
Preserve original behavior as evidence; only an explicit compatibility request justifies a separately isolated
defective legacy callable.

An observed defect is a repair candidate, not an automatic terminal gap and not permission to
rewrite the algorithm. Preserve the immutable source snapshot and raw failure receipt, then use this
sequence:

1. **Reproduce.** Freeze the exact input, source digest, runtime, branch selectors, first divergent
   state, and the failing shape/index/allocation/consumer access. Separate a source defect from
   undefined or uninitialized behavior.
2. **Recover intent.** Cite the declaration/allocation, producer loop, consumer access, active
   extent, index base, neighboring assignments, call-site contract, and any equation/unit anchor.
   A shape fix needs both the producer's emitted extent and the consumer's required extent; a
   plausible reshape from the failing array alone is insufficient.
3. **Propose the smallest patch.** Preserve axis order, loop meaning, index base, units, branch
   guards, and terminal semantics. Do not arbitrarily reshape, truncate, pad, clamp, zero-fill,
   or widen a domain. Boundary padding or a default is allowed only when the source contract or
   independently stated relation explicitly requires it. Keep the original and repaired revisions
   addressable; never overwrite legacy evidence.
4. **Differentiate.** Re-run an unaffected-domain parity set, the defect boundary (including empty,
   singleton, and maximum active extents where applicable), downstream terminal-state checks, and a
   sealed holdout that was not used to choose the patch or tolerances. Add an independent scientific
   or numerical check whenever the repair changes a relation rather than merely restoring an
   explicitly evidenced interface.
5. **Record a new claim.** Bind the repaired source/candidate digest, patch delta, evidence, and
   claim ceiling to a new immutable successor. Keep the labels distinct:

   - `legacy_exact`: original snapshot behavior, including a known defect when compatibility is
     required;
   - `source_repaired`: minimal source-intent repair with source parity on the unaffected domain and
     explicit repaired-domain evidence;
   - `scientifically_corrected`: a corrected relation with independent scientific/numerical evidence;
   - `validation_oracle_gap`: repair intent is plausible but the required independent basis is absent.

`source_repaired` is not a synonym for `scientifically_corrected`. If the repair changes equation,
boundary, normalization, or physical meaning, return it to the correctness owner as a separate corrected
relation with independent validation and read-only findings.

## Minimum repair receipt

Keep the following outside the formal asset package and link it from the ledger/report:

```text
source_snapshot_digest
source_runtime_identity
failure_receipt_and_first_divergent_state
defect_class_and_affected_extent
source_intent_anchors
minimal_patch_delta_and_new_revision_digest
unaffected_domain_parity
repaired_domain_boundary_cases
canonical_and_sealed_holdout_results
termination_semantics_before_after
independent_oracle_or_validation_oracle_gap
claim_ceiling_and_reopen_condition
```

The receipt is evidence of a controlled change, not a stage-completion or approval record.
