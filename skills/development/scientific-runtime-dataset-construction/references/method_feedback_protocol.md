# Method Feedback Protocol

## Goal

Turn repeated extraction discoveries into reusable process rules without mixing project evidence,
scientific formulas, or transient workarounds into a general skill.

## Feedback record

For each candidate method, record:

```text
observation
-> generalized rule
-> known counterexample or applicability limit
-> evidence cases
-> owning skill/reference
-> executable guard or review question
```

Keep this record in the active project's external extraction ledger/evidence until the rule is
ready to promote.

## Applicability before promotion

An observation supports a method only within its demonstrated conditions. Identify the causal
mechanism, intended consumer and scope, and a valid case that would defeat an overbroad rule.
Independent branches and material boundary cases are useful probes; their count does not establish
universality. A method learned from a source defect must retain that defect class and its limits.

Prefer a task-specific correction, regression test, or revision of existing conditional guidance.
A blocking gate additionally needs an accepted, necessary and machine-checkable contract with clear
applicability; repeated incidents alone do not supply one. Narrow or retire guidance when its premise
changes. The cases below are scoped evidence patterns, not a checklist every extraction must satisfy.

## Ownership routing

- Dataset qualification, probe placement, case partitions, capture provenance, split isolation,
  and dataset integrity belong here.
- Candidate identity, framework ownership, operator/task-graph boundary, and bundle shape belong
  to `scientific-computation-asset-extraction`.
- Scientific/numerical implementation belongs to `scientific-relation-implementation`.
- Independent oracle choice, tolerances, residuals, refinement, and earned claims belong to
  `scientific-computation-validation`.
- Acceptance decisions belong to `scientific-operator-review`.

If a finding affects two skills, put the authoritative rule in the owner and add only a short
cross-reference in the other. Do not copy the same workflow into multiple `SKILL.md` files.

## Generalization rules

- Replace project names and paths with semantic roles such as source runtime, target-call pre-state,
  row family, event history, or table identity.
- Replace observed constants and array sizes with explicit axes, active extents, selectors, or
  configuration fields.
- Preserve counterexamples: undefined state, missing predecessor initialization, nonunique parallel
  order, serialization loss, and synthetic-data fidelity limits.
- Separate source-derived termination/source behavior from physical or numerical correctness; a
  source control-flow oracle may close a bounded parity claim while an independent physics oracle
  remains `validation_oracle_gap`.
- Treat a reproducible shape/index/allocation mismatch as a controlled-repair candidate. Preserve
  the raw failure, recover intent from both producer and consumer, require a minimal patch and
  fresh boundary/holdout evidence, and keep `legacy_exact`, `source_repaired`, and
  `scientifically_corrected` as separate claims.
- Keep the main `SKILL.md` concise. Put schemas and variant-specific coverage in references.
- Add or extend one deterministic validator only when a machine-checkable invariant recurs; do not
  create a script for a judgment that requires scientific interpretation.

## Update sequence

1. Patch the project-owned skill/reference first.
2. Run the affected skill validator and any deterministic script self-test.
3. Compare adjacent skills for duplicated ownership or conflicting language.
4. Forward-test on a minimally described real gap when practical; do not leak expected answers or
   holdout outputs.
5. Synchronize an installed copy only when it exists and is maintained for this workflow; do not
   create a global runtime-skill copy merely because the project-owned method changed.
6. If synchronized, verify the intended files match, excluding transient caches.

Do not update counts, project ledgers, or formal bundle contents merely because the general method
changed. Apply the method to a concrete extraction slice before claiming a project capability gain.

## Stateful control ownership and stream evolution

Use this rule when a source routine consumes numerical coefficients only under a caller-selected
mode, event, harmonic, phase, or feature-owner condition.

```text
observation: a captured coefficient was present/nonzero but replay was wrong until the real
             consumer/owner selector was captured separately;
generalized rule: record the selector and whether the target call consumed each optional channel
                  as explicit state, then expose it as a caller-owned branch contract;
limit: a selector alone does not identify an omitted scientific producer, and an inactive channel
       must not be synthesized from its stored coefficient;
evidence: source-backed mode/branch capture plus at least one inactive-or-nonowner boundary replay;
guard: reject a replay contract that infers consumption solely from coefficient presence, sign,
       finiteness, or magnitude.
```

When a capture format changes while resolving such a contract, give the stream a new declared
version and describe every field's scalar type, axes, index base, and active extent. Its parser
must reject unsupported versions, incomplete fields, and unread trailing bytes. This is a capture
integrity rule, not permission to demand byte-identical scratch storage when the scientific
consumer declares a smaller active extent.

Do not use the sparse record footprint of one target relation as the active extent of an adjacent
optional channel. A damping, loss, source, boundary, or correction producer can legitimately
consume every active segment even where the target relation skipped its local computation. Capture
that channel's complete producer field at its own consumer boundary; never zero-fill unrecorded
segments and call the result source fidelity.

## Selector qualification before promotion

Use this rule when a source selector can reach a routine but may leave required predecessor state,
tables, or branch initialization invalid.

```text
observation: one reachable selector entered the target with zero/invalid predecessor state or
             non-semantic termination, while a documented supported selector reached the same
             mapping with finite state and normal semantic completion;
generalized rule: promote a selector-specific observation only when its documented configuration,
                  required external-data identity, finite target pre-state, process status, and
                  semantic marker all agree; routine entry or container exit alone is not coverage;
limit: a supported alternative closes only its declared branch and never licenses an invented
       table, clamp, default state, or repair for an unsupported selector;
evidence: one normal source-backed branch plus one material failed/invalid selector boundary;
guard: register the failed record as a boundary/configuration need, not as a covered dataset case.
```

## Target-call parameter authority

Use this rule when a nearby configuration field appears to describe a target routine's branch
bound, extent, mode, or physical region, but the routine consumes a distinct call argument or
runtime-derived value.

```text
observation: replay was falsely accepted after a configuration field was substituted for the
             target call's own bound; an observed boundary record showed that the target still
             consumed state which the substituted value classified as inactive;
generalized rule: record every target-call parameter that controls branch selection or input
                  consumption at the call boundary. Do not infer it from a similarly named,
                  nearby, or apparently related configuration field. When both values matter,
                  serialize them as separately owned fields and make the target value the replay
                  control;
limit: one observed target value proves only that declared input domain. It does not reconstruct
       the target-value producer for arbitrary configurations or license a hard-coded default;
evidence: a normal source-backed branch plus a boundary/continuation replay that crosses the
          mistaken extent and demonstrates real target-state consumption;
guard: reject a dataset derivation if a branch or consumption control lacks target-call provenance,
       or if it is supplied solely by an upstream configuration field without an explicit
       source-defined equality contract.
```

## Controlled caller-state injection at a target boundary

Use this rule when a target mapping consumes a source-declared caller-owned state, but the
available runnable configuration cannot produce one material state transition needed to verify the
mapping.

```text
observation: ordinary source records preserved a caller-owned state, while the target's material
             transition required another legal state value that the available input format did not
             expose on that runtime path;
generalized rule: a disposable source workcopy may inject the already-declared caller-owned state
                  immediately before the literal target call, after genuine predecessor
                  initialization. Capture the injected pre-state and source post-state as a
                  separately labelled boundary case, then replay the same explicit state
                  source-free;
limit: the injection proves only the target's response to that declared state. It does not prove
       the original input configuration produced it, recover the upstream state producer, or
       permit injection of hidden scientific fields, uninitialized storage, or guessed values;
evidence: a normal source-backed preservation case plus a material injected transition whose
          source-free replay would fail if ownership, call position, or branch semantics were
          wrong;
guard: require the manifest to name the injected field, value, target-call position, source-workcopy
       status, and boundary split. Reject an injected record if it is labelled extraction or
       holdout, replaces source input provenance, or is used to claim full-input trajectory parity.
```

## Solver-call pre-state finalization

Use this rule when a source solver mutates or repacks its initial vector, tolerance, iteration cap,
or other consumed numerical control after matrix/preconditioner preparation but before the literal
solver invocation.

```text
observation: an early matrix or factorization capture was structurally correct, but source-free
             replay diverged because a later source step repacked the initial solution or replaced
             an active solver control immediately before the solver call;
generalized rule: capture the target pre-state at the literal solver invocation after the final
                  source-side mutation of every consumed vector and control. Keep earlier matrix,
                  factorization, or workspace captures as separately named preparation evidence;
                  never combine them into a pre-state unless a source-defined equality contract
                  proves they are unchanged;
limit: a literal call-boundary capture closes only the declared solve mapping. It neither recovers
       the upstream matrix/RHS producer nor licenses a guessed packing, unpacking, control default,
       or inactive workspace byte as a scientific input;
evidence: a normal source-backed replay plus an unseen holdout or a material stale-prestate
          counterexample, with an independent residual or iteration-trace comparison;
guard: reject a solver replay when its initial vector, stopping controls, or active extent come
       from an earlier capture without source-defined equality, or when the manifest fails to
       distinguish preparation state from literal-call pre-state.
```

## Terminal-preemption event order

Use this rule when a source event can terminate after one state update but before a later
classification, random draw, accumulation, or side effect.

```text
observation: a source event reached a terminal condition after its step duration was selected;
             the source then bypassed a later random draw and all downstream event handling;
generalized rule: capture the terminal predicate's genuine predecessor fields and position in
                  the source order. In source-free replay, make the caller-owned terminal event
                  and its comparison value explicit, test it before later consumers, and prove
                  that every bypassed draw/state update was not consumed;
limit: the terminal-event contract does not reconstruct the upstream geometry, threshold,
       scheduler, or other producer that decided the event for new inputs;
evidence: one normal source-backed terminal event plus a boundary replay that would diverge if
          the later draw or consumer were executed;
guard: reject a terminal replay record that lacks the pre-terminal comparison value, declares a
       terminal condition after a recorded bypassed draw, or infers terminal status from final
       output alone.
```

## Non-finite source observations at controlled boundaries

Use this rule when a runnable source program reaches a configured coordinate limit, but a subset
of target calls or their downstream aggregate becomes non-finite.

```text
observation: a controlled source run reached the requested boundary; some direct target-call
             outputs were finite while other calls or a later aggregate were NaN/Inf;
generalized rule: retain the complete raw trace and classify finite direct-call records and
                  non-finite records separately. A source-free replay may claim parity only for
                  the explicitly selected finite atomic relation, never for the full profile or
                  aggregate that contained non-finite source behavior;
limit: do not silently drop non-finite rows, repair the source output, or infer that the emitted
       asset is scientifically superior or source-equivalent outside the selected domain;
evidence: the normal source completion marker, complete raw trace, selection predicate, excluded
          non-finite count, and a source-free replay of every selected finite record;
guard: a dataset manifest must name the selected relation and report non-finite exclusions. Reject
       a claimed full-run or aggregate parity result whenever any matched source record is
       non-finite.
```

## Probe-only link isolation

## Target-local completion before outer failure

Use this rule when a real source program completes the declared target call and records its full
post-state, but a later independent stage terminates abnormally.

```text
observation: the target receipt has genuine predecessor state, target input, and post-state;
             source order proves the target returned before a later outer-program failure;
generalized rule: record semantic_status=target_completed_outer_failure and the named later
                  failure. Count coverage only for the exact local target mapping, then replay it
                  source-free from its declared pre-state;
limit: this is not a normal source run, full program parity, or proof that the later failure is
       irrelevant to another mapping. Do not use it if target post-state was not captured;
evidence: target receipt after return, raw outer-failure log, and source-free local replay;
guard: reject the status unless target input/output are both present and the manifest explicitly
       names the later failure and limits the claim to the target call.
```

Use this rule when a legacy source build cannot link its whole program, but the declared probe has
already reached a target handoff before the unresolved routine could execute.

```text
observation: an unrelated unresolved legacy dependency prevented a controlled probe build, while
             target-call capture was reachable through a shorter, known dynamic slice;
generalized rule: a disposable no-op link stub is permitted only when source control flow proves
                  the stub is outside the predecessor-to-target slice, the probe stops immediately
                  after capture, and the manifest hashes both the stub and build log;
limit: never stub a target, predecessor, numerical producer, table reader, or any routine needed
       before the captured handoff. A stubbed probe cannot establish full-program termination or
       parity;
evidence: a failed whole-program link boundary plus a source-backed target capture whose declared
          inputs and outputs replay source-free without the source tree;
guard: reject promotion if reachability is assumed rather than evidenced, if the stub has side
       effects, or if an unresolved dependency lies on the captured target's call path.
```

## Source-expression numeric semantics

Use this rule when a source-free reconstruction has the right declared inputs, formula terms, and
branches but has a small, systematic source-replay difference.

```text
observation: a legacy source expression used default-kind numeric literals; a host-language rewrite
             used wider literals, changing a normalization or a threshold despite matching the
             visible mathematical formula;
generalized rule: capture and declare source-language literal kind promotion, arithmetic precision,
                  association, and comparison precision whenever they materially affect the declared
                  discrete mapping. Diagnose a systematic differential against raw target output
                  before changing a tolerance; preserve the source numerical convention only for a
                  source-faithful mapping;
limit: do not import a source-language rounding accident into a separately declared corrected or
       continuous scientific relation. If the numerical convention is not observable over the
       claimed contract, state the precision policy rather than adding compatibility constants;
evidence: an ordinary source-backed branch plus a conditional threshold/boundary branch where the
          wider-literal reconstruction diverges and the declared source convention restores replay;
guard: before accepting source fidelity, review every source literal and comparison participating in
       a replay mismatch; reject a resolution that only loosens tolerance or that leaves the
       effective precision/threshold undocumented.
```

## Probe field storage authority

Use this rule when a probe helper observes a field with the same name as a target routine variable,
but the captured value is nonsensical or inconsistent with the routine's visible branch behavior.

```text
observation: a helper that included a shared-state header emitted invalid counters because the
             target routine actually owned same-named saved locals outside that shared state;
generalized rule: before adding every captured field, trace its source declaration and storage
                  authority. Capture a routine-local or saved variable inline at the call site, or
                  pass it explicitly as a probe argument. Use a shared-state helper only for a
                  field proven to inhabit that same shared-state declaration;
limit: passing a local value proves only the declared capture point. Capture separate pre/post
       records when nested calls may mutate the local, and never read an uninitialized local merely
       to make a record appear complete;
evidence: one scope-mismatched capture rejected by field-level review, followed by a normal
          source run whose inline/parameterized record agrees with branch and post-state behavior;
guard: reject a dataset record unless every field has a declaration/ownership anchor. A matching
       identifier in a header is not proof that it is the target routine's storage.
```

For unformatted stream captures, declare the parser in the exact temporal write sequence,
including loop nesting and interleaving of distinct field families. Do not regroup records by
field name merely because their logical shapes match: a parser that consumes all instances of one
field before the next can silently bind valid bytes to the wrong scientific ports. Treat write
order and repetition scope as schema fields, then reject trailing bytes and declared-shape
mismatches as usual.

## Probe expression domain and auxiliary ABI

Use this rule when a probe inserts a helper call around a legacy branch whose source expression
is intentionally not evaluated for every row, endpoint, or mode.

```text
observation: a capture evaluated an outer-boundary expression that the source placeholder branch
             never consumes and crossed its unavailable neighbor; a later probe also serialized a
             new helper argument with the wrong implicit Fortran type;
generalized rule: for every probe-only expression, capture only on the same source branch where
                  the target consumes it, and write an explicit zero/not-applicable field for the
                  remaining records. Explicitly declare the scalar type of every added helper
                  dummy argument and on-stream field; do not inherit a legacy implicit-type rule;
limit: a safe probe branch condition does not redefine the source's scientific boundary rule, and
       a captured zero/not-applicable field is not a physical coefficient or a missing producer;
evidence: one normal source-backed replay plus a material endpoint failure caused by eager probe
          evaluation or implicit-type mismatch, followed by a corrected capture with exact replay;
guard: review every inserted call against the source branch predicate and reject a stream schema
       unless each added field declares type, byte width, axes, index base, active extent, and
       not-applicable representation.
```

## Coverage census before heavyweight capture

Use this rule when one real source run reaches many accepted instances of the same target mapping,
but each full call-boundary record is expensive to retain or inspect.

```text
observation: a lightweight record made after genuine predecessor initialization and target-branch
             acceptance distinguished threshold sides and active-extent endpoints that a single
             convenient full trace would not cover;
generalized rule: first capture a bounded branch census containing only selectors, branch controls,
                  active extents, and endpoint indices. Choose a minimal set of full traces whose
                  declared partitions cover behaviorally distinct threshold and endpoint cases;
limit: the census is only a coverage index. It cannot replace the full target input/pre-state and
       output oracle, and it must not be used to infer an unrecorded producer or scientific result;
evidence: one normal full replay plus a material threshold-side or active-extent boundary replay
          selected from the census;
guard: a partition is covered only when its selected full trace has normal semantic completion and
       source-free replay. Reject a claim based only on census rows or convenient sample count.
```

## Target-local coverage ownership

Use this rule when a control or boundary appears in a broader source pipeline, but source order
may force it inactive at the declared target call or defer its consumption to a later mapping.

```text
observation: a related downstream branch was listed as an uncovered partition for an inner
             target, although that target's initializer forced the branch inactive;
generalized rule: require a coverage partition only when the declared target mapping can consume
                  it at the captured lifecycle point. Assign a later-consumed branch to the later
                  producer/consumer dataset, and state the source-order reason for the boundary;
limit: a shared configuration field can still be required target input, but it does not create a
       target-local branch unless source control flow makes the target consume it;
evidence: a normal target-call capture that records the effective selector plus a material
          downstream boundary capture that proves where the condition is actually consumed;
guard: every required partition must name its target-call consumption branch or selector. Reject
       a coverage matrix that retains an unrelated downstream condition merely to increase its
       branch count or labels it as an inner-target gap.
```

## Holdout target-call distinguishability

Use this rule when a declared holdout changes an external configuration value, but the target call
may still consume the same predecessor state and therefore produce the same observation as the
primary case.

```text
observation: a frozen holdout changed a legal time-control input, yet the target was still at its
             initialization lifecycle point; its active predecessor and target output were bytewise
             identical to the primary record;
generalized rule: before evaluating a holdout, compare the declared target-call input/pre-state on
                  its active extent with the primary case. If they are identical, do not count the
                  case as independent behavioral evidence; preserve it as an inert configuration
                  observation and select a later lifecycle state, material boundary, or other legal
                  case whose consumed state actually differs while the claimed mapping remains the
                  same;
limit: different pre-state values are not by themselves an independent scientific oracle, and a
       relation may legitimately be invariant under some input changes; this rule only prevents a
       non-distinguishing holdout from being overstated as new replay coverage;
evidence: a frozen inert holdout detected by active-input comparison, followed without changing
          the formal relation or tolerance by a source-backed later-state holdout and source-free
          replay;
guard: record target-call input identity or a declared active-extent metric for every holdout.
       Mark an identical active pre-state as `inert_holdout`, exclude it from promotion coverage,
       and require a distinguishable replacement unless the holdout's separate purpose is explicitly
       configuration reachability rather than behavioral validation.
```

## Canonical control after initializer projection

Use this rule when a source accepts more than one configuration representation for a control, and
an initializer, adapter, or parser projects one representation over another before the target call.

```text
observation: changing a visible low-dimensional control in an input file produced an inert capture
             because an initialization routine overwrote it from the canonical higher-dimensional
             control; changing the canonical control produced a distinct target pre-state;
generalized rule: treat a raw configuration literal as a candidate input, not proof of the value
                  consumed by a target. Trace every initializer/projection between parse and call,
                  record the canonical control and its source representation in target pre-state,
                  and choose holdouts by a material difference on that consumed state;
limit: an inert alias perturbation proves neither relation invariance nor source failure. It can
       remain a configuration-reachability record, but cannot count as a behavioral holdout or a
       covered branch;
evidence: one inert source capture caused by an overwritten alias plus a second normal capture in
          which the canonical control changes the declared target pre-state and source-free replay;
guard: reject coverage or holdout promotion based only on a raw control-file diff when the target
       pre-state does not differ on its declared active extent. Record the overwriting initializer,
       source-order position, canonical axis/selector, and retained caller ownership.
```

## Target-call receipt over lifecycle label

Use this rule when a probe is scoped by a nominal time step or iteration, but the producer may run
during initialization or another lifecycle phase.

```text
observation: a time-labelled capture missed the producer, while the same normal source run showed
             the target call during a different lifecycle phase and a later labelled record was inert;
generalized rule: anchor capture to a declared target-call or producer-event receipt, and record the
                  lifecycle phase as metadata. Treat a global time or iteration label as a selector
                  only when the source explicitly makes it part of the target-call contract;
limit: one receipt proves execution only for its observed configuration. It neither reconstructs an
       upstream producer nor proves a later lifecycle state is behaviorally distinct;
evidence: one normal source-backed target-call capture plus a material missed/inert lifecycle
          boundary, followed by source-free replay from the captured explicit pre-state;
guard: reject a producer-coverage claim that is supported only by a time/iteration label, or that
       treats an identical later record as an independent holdout.
```

## Scale-aware holdout acceptance

Use this routing rule when a source-free differential includes floating fields whose magnitude
changes materially across lifecycle, configuration, or component.

```text
observation: a frozen later-lifecycle holdout had roundoff-level relative agreement, but failed a
             globally pre-registered absolute threshold because its valid source field magnitude
             was much larger than the primary case;
generalized rule: the dataset owner freezes split identity and captured state, while the validation
                  owner pre-registers a unit-aware differential gate: finite mask/shape plus a
                  scale-relative norm or declared component reference scale. Raw max_abs remains a
                  diagnostic unless its units and ULP/reference-scale budget are explicit;
limit: this does not relax exact discrete contracts or allow a tolerance to be changed after a
       holdout output is revealed. The rejected record is calibration evidence, not promotion
       evidence; generate a new unseen holdout after the corrected gate is frozen;
evidence: an ordinary primary replay plus a later-lifecycle material boundary that exposes the
          scale mismatch while retaining roundoff-level relative agreement;
guard: reject a holdout promotion if a global absolute floating threshold lacks a declared scale,
       or if a post-reveal threshold change reuses the same output as validation evidence.
```

The authoritative acceptance rule belongs to `scientific-computation-validation`'s validation
catalog. This entry only routes split custody and rejected-record handling; do not duplicate the
metric policy into dataset manifests as a second source of truth.

## External producer payload receipt

Use this rule when a producer can terminate normally in a mode that does not emit the file, stream,
or array declared by a downstream consumer.

```text
observation: a producer reached its normal semantic terminal but emitted no declared handoff
             payload under one legal output-mode boundary;
generalized rule: verify process/semantic terminal and payload emission independently. Record the
                  expected consumer contract, emitted artifact identity/schema/active extent, or a
                  hashed absence receipt and consumer inadmissibility;
limit: a payload receipt proves only the observed producer configuration. It neither extracts the
       upstream producer nor establishes arbitrary-input compatibility or consumer invalid-input
       behavior;
evidence: one normal payload-emitting source case and one material normal-but-non-emitting boundary;
guard: reject consumer-handoff coverage that relies only on producer exit/terminal status, and never
       substitute an empty, fallback, or unrelated output for the missing payload.
```

## Source-native writer isolation

Use this rule when a wrapper instruments a legacy script that resets its workspace or writes a
relative terminal file.

```text
observation: a numerical source loop reached its declared terminal iteration, but a probe that
             redirected the source writer through wrapper-owned state failed after the source reset
             that state; the disposable work directory vanished on container exit;
generalized rule: retain the source-native writer and, only after it returns, reacquire the
                  declared work/evidence locations, verify the raw source output exists, and copy
                  it to a new versioned external attachment before the disposable runtime ends;
limit: a copied file proves neither semantic completion nor scientific parity. If the native writer
       did not complete, keep the run failed even when an earlier numerical trace reached a limit;
evidence: a material wrapper-state or teardown failure plus a normal rerun whose raw output,
          source/runtime identity and hash are recorded separately from derived terminal metadata;
guard: reject a dataset when source code depends on a wrapper variable, a prior evidence artifact
       is overwritten, or the raw writer output is absent/unhashed.
```

## Bounded deterministic routine microprobe

Use this rule when a source routine owns a small deterministic state transition, but the full
program trajectory obscures one or more control branches.

```text
observation: a self-contained source routine could be compiled with its genuine declarations and
             explicitly initialized inputs; a threshold-side, equality, or disabled-guard case
             exposed a branch that an extracted directed mapping had not emitted;
generalized rule: compile a disposable microprobe against the read-only source routine and its
                  required declarations, initialize only the routine's documented consumed state,
                  and record source outputs for a minimal branch matrix. Preserve the probe source,
                  build log, and output receipt; then replay the same explicit inputs through the
                  public source-free bundle entry point;
limit: this proves only the routine-level mapping and the declared initialized state. It neither
       proves the full caller trajectory nor licenses a guessed predecessor, common-block field,
       scheduler, or physical correction;
evidence: one ordinary branch plus a material guard/threshold boundary whose expected output would
          differ if the branch were absent;
guard: keep the source mount read-only; emit the temporary executable only to a disposable
       executable work/evidence location, remove it after the run, and reject the record if a
       required predecessor cannot be initialized from declared source semantics. Merge a missing
       branch into the existing operator that owns the complete directed mapping; do not create a
       standalone helper for a private numerical factor.
```

## Legacy whole-file compile isolation

Use this rule when a declared routine is reachable and self-contained for a bounded probe, but a
modern compiler rejects the legacy source file because other, uncalled routines contain obsolete
argument associations or interface inconsistencies.

```text
observation: the target routine and its genuine predecessor are present in the read-only source
             file, yet compiling that whole file fails before execution because unrelated legacy
             routines violate current compiler interface checks;
generalized rule: first compile the unmodified source file with the smallest documented
                  source-compatibility option required by the compiler. When the linker supports
                  section garbage collection, compile functions/data as separate sections and link
                  only the target-call slice, so uncalled legacy dependencies do not become probe
                  implementations. Record the exact flags, compiler, build log, source digest,
                  target symbol, and linked objects. Only if this cannot yield the target routine
                  may a minimal textual source slice be used; preserve its source file digest,
                  original line range, extraction script, and byte-for-byte slice check;
limit: compatibility flags and link isolation may make a bounded target call executable; they do
       not validate the whole source program, permit stubbing a reachable predecessor, or justify
       changing the target's numeric semantics. A copied/retyped routine without provenance is a
       new implementation, not a source observation;
evidence: a failed strict whole-file compile boundary followed by one successful original-routine
          target capture and a material continuation, branch, or boundary replay;
guard: reject a dataset if its build log cannot identify the original target object, if a stub or
       slice replaces any reachable predecessor/target code, or if the manifest omits compiler
       flags and source/slice provenance.
```
