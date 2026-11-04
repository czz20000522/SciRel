# Pleiades D1 extraction workflow optimization trial

Status: reopened; the historical `full_freeze` self-reports below are not accepted as current strict freeze evidence. Not exported.

On 2026-09-25, an independent source-first review rejected the run's later rev3 whole-project freeze claim: the
kinetic and Hall public drivers save terminal physical state absent from the declared output denominator and from
canonical/sealed-holdout comparisons. See the run's
`coordination/source-first-independent-veto-20260925.txt`. This also invalidates the earlier two-path freeze claim
as a whole-project conclusion. The original run must close the source-derived denominator and pass a new independent
review before this trial can establish preserved strict quality. The observations below remain historical process
measurements, not a current L1 delivery or a quality-preserving optimization result.

## Question

Does the optimized extraction method reduce repeated navigation, broad source reading, and avoidable coordination
while preserving the current D1 scientific scope and strict `capability-progress` schema 1.0 freeze boundary?

This is one bounded pilot. It selects the best currently supported method; it does not seek an absolute optimum or
establish a universal numerical improvement threshold.

## Frozen trial identity

- Spark run: `Pleiades/stage1-Pleiades-opt-20260921T093633Z`
- source root: `/home/opc/codefusion-decomposition/sources/pleiades_hall_kinetic`
- source tree digest: `7c809a0d6d1fb18568e3b70e1a0fcbee7fff42469881b859df2028a373488c5a`
- SciRel extraction bundle digest:
  `sha256:2fe86e72d44e62f3cd9cd8957a729eb50e4ffbaa40040efb860adb9d36e799be`
- fresh artifact-template digest: `1cb015d42e89144386421c95f96d2594f08d1a65183572cc6e30f373691385fa`
- coordinator/worker budget: two agent threads total
- prior Pleiades bundle and evidence visibility: forbidden to the trial coordinator

The run started from the deployed empty artifact template. It did not copy the historical Pleiades candidate bundle.
The historical output is available only to the outer comparison after the trial stops.

## Invariant quality boundary

The candidate workflow must independently account for the complete source scope, explicit dispositions, material
branches and state lifecycles, dependency closure, source-free execution, and every declared core target path. A
`full_freeze` claim additionally requires canonical and fresh sealed-holdout source/bundle reassembly with identical
explicit inputs, complete declared terminal outputs, exact source and bundle digests, and
`scirel.extraction-reassembly-comparison.v1` receipts under capability-progress schema 1.0.

Efficiency observations cannot offset a scientific gap, reduced scope, weaker oracle, missing output, or deferred
work. Process exit status, package counts, test counts, or model activity are not scientific completion.

## Intervention

The optimized workflow adds four mechanisms:

1. A source-digest-bound structural evidence index performs file, symbol, reference, entry/test/example/document, and
   explicit state-access navigation before broad semantic reading.
2. The model uses the index only to select anchors, then returns to source and runtime probes for scientific meaning,
   boundaries, hidden state, document authority, and coverage decisions.
3. Source fidelity and independent scientific validation are planned as separate evidence axes.
4. TaskGraph `probe_ready` and `freeze_ready` are derived from current dependencies, ports, and gates rather than a
   manually duplicated readiness list.

The method was informed by the `baidubce/skills` FaMou problem-definition, evaluator/adapter, experiment-management,
and diagnosis skills. SciRel adopts the baseline-before-change, bounded experiment, and baseline/previous/current
diagnosis concepts; adapts them to separate scientific quality from workflow cost; and rejects the FaMou cloud/SDK
binding, fixed polling behavior, directory conventions, automatic dependency installation, and a single optimization
score. No FaMou code or runtime dependency is copied into SciRel.

## Comparison evidence

The historical Pleiades ledger records a long method-development period from August through 9 September 2026. Its
final reported snapshot contained 41 operators, 11 TaskGraphs, 226 package tests, and eight M1-M4
canonical/holdout comparisons covering 5,945 numeric values with maximum absolute error zero. That history included
method discovery, later source additions, scientific corrections, and changing freeze standards, so elapsed calendar
time and iteration count are context, not a controlled baseline.

The trial will record only observable, comparable evidence:

- wall-clock milestones from prepared run through structural index, first staged candidate, closed target paths, and
  terminal state;
- structural-index coverage, parse failures, uncertainties, and queries that still required direct source/probes;
- candidate reopenings, failed/retried operations, and manual handoffs;
- final census, dispositions, target paths, candidate identities, test/reassembly evidence, claim ceilings, and gaps;
- environment, provider/model, dependency, concurrency, cache, and prior-artifact differences that confound comparison.

Token or tool-call totals will be reported only if the runtime exposes them reliably; they will not be estimated from
prose or terminal length.

## Current observations

- The generic Spark `launch-project.sh Pleiades 2` failed before coordinator start because `prepare-run.py` checked
  `sources/Pleiades` before reusing the already prepared run whose explicit source is `pleiades_hall_kinetic`.
- The failure was retained in `coordination/optimization-trial.json`. A run-local launcher started the unchanged
  coordinator supervisor against the same prepared run; no duplicate run was created.
- The digest-bound structural index completed at `2026-09-21T09:42:13Z`, about 5 minutes 39 seconds after run
  preparation. It inventoried 110 files, parsed 35 Python files, indexed 389 symbols, and reported zero parse failures.
  The coordinator then used it to select and directly inspect the governing equilibrium, kinetic, Hall, field, test,
  and scientific-document anchors.
- The index file itself was complete by `2026-09-21T09:40:29Z`, about 3 minutes 55 seconds after preparation. The
  later timestamp records when the coordinator bound it into the experiment ledger. The index remained navigation
  evidence only; direct source reading and wrapper probes supplied the scientific judgments.
- The coordinator initially made two raw `docker run` calls while selecting a runtime image. This violated the run
  wrapper contract. The observations were quarantined and excluded from all scientific, dependency, runtime, and
  freeze evidence. Wrapper-produced receipts subsequently established the runtime identity. The violation is retained
  as `RCV-RAW-DOCKER-RUNTIME-INSPECTION` in `coordination/optimization-trial.json`.

## Result

The coordinator reported schema 1.0 `full_freeze` at `2026-09-21T12:41:00Z`, 3 hours 4 minutes 26 seconds after
the run envelope was prepared. It was then stopped. This was a two-path historical checkpoint, not an accepted
whole-project freeze. The experiment bundle was not exported and did not replace the local Pleiades L1.

Final evidence:

- frozen candidate bundle digest:
  `6b6bdd788d1d5da8a961c02fb4f41f7314bfe2ee2e44531f18a7a0b5ba948c2d`;
- 17 operator packages and two TaskGraphs, with 19 packages tested on both evidence axes: 38/38 runs passed on the
  frozen bytes;
- two declared whole-path targets: kinetic mirror equilibrium and Hall CGL-Vlasov equilibrium;
- canonical and independently sealed holdout comparisons used identical explicit inputs and compared every declared
  terminal output: kinetic 8/8 outputs had `max_abs=0`; Hall 11/11 had `max_abs<=1.74e-18`; the degenerate
  Hall/inertia-off branch compared 4/4 outputs with `max_abs<=4.34e-19`;
- intake, source-free bundle, asset-entry, library API, package tests, dependency closure, and capability-progress
  schema 1.0 gates passed against the same frozen digest;
- the 110-file structural inventory was dispositioned in that checkpoint, but the later source-first review found
  missing terminal physical outputs in the kinetic and Hall denominator. Inventory completeness did not prove
  scientific-output completeness.

### Observed effects

The optimized method produced a two-path checkpoint in a little over three hours with one coordinator and no
worker handoff. It did not demonstrate a strict whole-project freeze. The structural index made the file/symbol/document surface available in under six minutes and
gave the model a bounded navigation layer before scientific reading. The dual evidence axes exposed incorrect Picard
semantics, a magnetic-field/potential port mix-up, an invalid Hall-off invariant, and omitted graph outputs before
freeze. Derived graph readiness and digest rebinding kept the final tests, validators, and reassembly receipts attached
to the same candidate bytes.

The run still required three substantive candidate reopenings and several fresh attempts. The index reduced search
cost; it did not remove the need to understand source semantics or execute scientific probes. This supports retaining
the optimized workflow, not replacing scientific analysis with automated summaries.

### Comparison limits

The historical 41-operator/11-TaskGraph Pleiades result and this 17-operator/two-TaskGraph result use different
decomposition granularity and were produced under different freeze standards. The historical calendar span also
contains method development, source additions, and repeated gate changes. Therefore this experiment does not support a
numerical claim such as a fixed percentage speedup, nor does the lower asset count by itself imply lower or higher
quality. Runtime token and tool-call totals were not exposed reliably and are not estimated.

The supported conclusion is narrower: the structural index provided rapid source navigation and the dual-axis checks
found several defects, but the source-first independent review found that the candidate-defined output denominator
missed public terminal physics. This trial therefore does not establish preserved strict quality or an end-to-end
speedup. Continue the already reopened original Pleiades run to a source-derived whole-project freeze; compare with
the historical artifact only after the new candidate stops and passes independent review. Do not begin another
optimization loop or promote a general speed claim from this incomplete comparison.
