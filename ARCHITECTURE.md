# SciReL architecture: operators, task graphs and static consumption

This document is the canonical project description of the three-line boundary,
task-graph roles and the retrieval path for a growing static SciReL asset set.
The asset contract remains the scientific truth. This document does not create
a second catalog, runtime protocol or acceptance standard.

## Three independent lines

SciReL work is divided into three independent responsibilities:

```text
source line      source behavior -> neutral candidate packet
maintenance line candidate packet -> static SciReL asset
outbound line    user requirement + static SciReL -> user-owned program and result
```

The lines may exchange only the artifacts defined by their public boundary.
The outbound line does not report its private program, task graph or gap list
to the maintenance line in order to use SciReL. A general agent may consume the
same static package; SciReL is not bound to Codex, Claude Code, Cursor, DSH or
any other agent.

### Source line

The source line extracts observable behavior from a frozen source or source
slice. Its candidate packet may contain operators, a source behavior task graph,
inputs, outputs, state transitions, failure paths and correctness evidence. It
does not choose SciRel asset IDs, public taxonomy, final aliases or receiver
roadmap decisions.

### Maintenance line

The maintenance line admits self-contained candidate packets and maintains the
public implementation, tests, contract, discovery projection, dependencies and
documentation. It decides whether a candidate is a leaf operator, a public
composition, a variant or an internal implementation. It does not inspect a
user's private outbound program and does not require outbound feedback to make
the package usable.

### Outbound line

The outbound line receives a user requirement and a public SciRel package. A
general agent searches the published contracts, writes its own program, creates
or updates its own task graph, writes task-specific tests, runs it, and retains
its own inputs, results and diagnostics. Those artifacts remain user-owned.
SciRel's query tools help the agent find contracts; they do not plan or execute
the user's scientific work.

The outbound line has two operating modes under the same skill:

| Mode | Owner and purpose | Public capability gap | Completion path |
| --- | --- | --- | --- |
| Internal SciRel run | SciRel owner tests the current package or prepares a capability addition | Stop the affected task at the missing public relation, record the gap, and route it to the maintenance/intake line | Capability decision, boundary tests, integration and rerun |
| External user run | A distributed package is used to solve a user's requirement | Treat SciRel as optional; implement the missing step with ordinary programming or numerical dependencies when permitted, and disclose it as task glue | User solution tests, diagnostics and deliverable result |

The same discovery and testing method serves both modes. The difference is
ownership and routing. A missing public capability is an internal intake signal;
it is a task-level implementation choice for an external user. An external
solution never becomes evidence that SciRel already owns the missing scientific
relation; an internal gap report never blocks an external user from completing
a solvable programming task.

## Capability boundary and ownership

The package is intentionally split into a reusable scientific core and a
user-owned solution program. The core does not need to solve every complete
question by itself; it must expose stable, composable scientific relations with
typed ports, units, shapes, applicability and failure semantics. The outbound
agent supplies the missing orchestration, data preparation, control flow,
format conversion and presentation as explicit glue.

| Artifact | Owner | Responsibility | Acceptance evidence |
| --- | --- | --- | --- |
| User requirement / benchmark problem contract | User / problem author / coordinator | Complete statement, typed inputs, units, boundaries, outputs, failure paths and test families when the problem is benchmarked | Requirement review and boundary test matrix |
| Public capability | Maintenance line | Reusable scientific relation or composition with public contract | Implementation, direct tests, contract and projections |
| User glue | Outbound agent / user | Task-specific orchestration and ordinary programming around public capabilities | Reproducible source, API trace, agent tests, outputs and disclosed gaps |
| Benchmark reference oracle | Coordinator / designated reviewer | Optional internal expected observations and comparison rules for benchmark regression | Separate oracle custody and post-run comparison; never a user runtime dependency |
| Scientific acceptance | Human owner / designated expert | Physical interpretation, applicability, rights and release decision | Explicit acceptance record |

The boundary is tested in both directions. A capability must survive normal,
lower-bound and upper-bound inputs, plus applicable degenerate, branch, failure
and composition cases. A user solution must be able to use the public core and
ordinary glue to solve the complete problem contract. Passing one fixed example
does not promote task-specific glue into a public capability; repeated
scientific relations across independent problems are the evidence for promotion.

An external-agent benchmark evaluation receives only the benchmark problem
contract and the public SciRel package. It does not receive reference answers,
hidden oracle data, existing glue or historical result files. The coordinator
may compare the result with a separately held benchmark oracle after the
evaluation. In a real user task there is no assumed reference oracle: the agent
must solve the requirement using the public package, ordinary programming,
task-specific tests, constraints and observable diagnostics. This keeps
capability discovery, solution generation, benchmark regression and scientific
acceptance as separate claims while testing whether the public boundary is
actually usable.

## Four graph roles

The word “task graph” is reserved for an operator graph whose ordering or
control semantics affect behavior. The following roles must not be conflated:

| Graph role | Owner | Purpose | Where it belongs |
| --- | --- | --- | --- |
| Source behavior task graph | Source line | Records the source operators, required order, data/control/feedback edges, state ownership and failure semantics | Candidate evidence and parity packet |
| Extraction procedure graph | Source line | Records how a worker inspected source, ran probes and assembled a packet | Internal source records only |
| Public SciReL composition graph | Maintenance line | A reusable, public composition with its own ports, dependencies, tests and contract | `catalog/examples/*.json` `composition` |
| User task graph | Outbound line | The program structure chosen for one user's request, including revisions after observations | User's private workspace |

The source behavior graph is part of the source behavior whenever the source
order is non-commutative or controls state, branches, feedback or failure. A
leaf-only submission is incomplete when omitting that graph would change the
observable result. It is not an extraction procedure graph.

The public `composition` field is not an automatic copy of a source graph. It
is created only when the maintenance line can give the composition a stable
public contract and independent tests. A source graph can therefore remain
evidence without becoming a user-facing SciReL composition.

## Promotion from source graph to public composition

A source composition may be promoted only when all of the following are true:

1. The ordering, state, branch and failure behavior is explicit and bounded.
2. Every public node and dependency has a contract with compatible ports,
   units, shapes and applicability.
3. The composition has direct tests that exercise its wiring and important
   failure or feedback paths.
4. Its public inputs, outputs and limitations do not depend on a source
   checkout, private path, hidden oracle or source-specific name.
5. The contract, discovery projection, examples and documentation can describe
   the composition as a reusable SciReL capability.

If these conditions do not hold, retain the source graph in provenance and
keep only the independently admitted leaf assets. Do not expose an incomplete
composition merely because its individual functions are available.

## Static retrieval as the package grows

The current portable consumer is intentionally static: contracts are the truth,
the discovery index is generated from them, and `describe`, `browse`, `search`
and `get` provide bounded read-only access. Retrieval is recall and selection;
it does not establish scientific applicability or composition correctness.

The scalable path is a set of derived views, not a central agent service or a
second hand-maintained taxonomy:

```text
L0 exact asset identity
L1 domain, phenomenon and capability family
L2 operation, model, geometry, boundary and device scope
L3 ports, units, shapes, state and failure compatibility
L4 public composition signatures and examples
```

All layers are generated from the contracts and bound to the same source
revision. A consumer normally narrows the candidate set from L0/L1/L2, checks
L3 compatibility, and then reads the complete selected contract. L4 helps an
agent find reusable public compositions, but it never replaces inspection of
their node and edge contracts.

The retrieval order is therefore:

```text
bounded recall -> hard metadata filters -> complete contract -> user task graph
```

Lexical search, aliases and future semantic indexes may improve recall, but a
similarity score cannot override units, geometry, boundary, state, failure or
evidence constraints. A zero hit is a retrieval result, not proof that SciReL
lacks a scientific capability. A near hit is not an applicable substitute.

When the asset count becomes large, the index may add measured family and port
signatures while preserving the existing query identity, pagination, pinning and
failure semantics. Any future semantic backend must be a derived projection,
must have a measured retrieval baseline, and must leave the complete contract as
the final selection authority.

## From Python package toward a scientific language

The current public form remains a Python package of ordinary callables and
contracted compositions. This keeps the static asset portable across general
agents and lets users write ordinary programs without a SciReL runtime service.

A later scientific-language layer may consume the same contracts and compile a
user-owned task graph to Python, C++ or another backend. Its verifier can check
ports, units, shapes, order, state transitions and declared failure behavior.
That layer is a downstream compiler/tool, not a new responsibility for the
source line or maintenance line, and it does not turn scientific applicability
into an automatic proof.

## Related canonical documents

- Contract truth and discovery ownership: [`catalog/README.md`](catalog/README.md)
- Project boundaries and information flow: [`RULES.md`](RULES.md)
- Static consumer protocol: [`tools/docs/PURE_CONSUMPTION.md`](tools/docs/PURE_CONSUMPTION.md)
- Admission boundary: [`contracts/admission/README.md`](contracts/admission/README.md)
