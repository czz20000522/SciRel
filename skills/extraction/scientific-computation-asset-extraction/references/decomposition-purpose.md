# Why decompose, and what the delivered capability is for

The target library is a self-contained, function-level scientific capability layer. It is not a copy
of any external project and not a runtime wrapper around one.

## Why external projects are decomposed

Mature scientific projects contain validated knowledge: equations, numerical choices,
edge-case handling and failure behavior. They are also complete applications with build
systems, native runtimes, configuration, IO, plotting and orchestration around that
knowledge. The receiver needs the knowledge, not the application.

Decomposition is how the receiver acquires a scientific capability it does not yet have:

1. freeze the source and understand what the implementation actually does;
2. **translate where understanding is incomplete**, so behavior and hidden pitfalls are
   preserved rather than guessed away;
3. **rewrite only what is understood**, using the receiver's own structure;
4. verify the result against source behavior, independent oracles and analytic invariants;
5. deliver a self-contained function/composition with direct tests and a formal contract.

Translation is an understanding tool; rewriting is a capability earned by understanding.
An implementation that looks odd may be handling a singularity, branch cut, overflow,
index order, unit convention, platform difference or convergence guard. Do not "clean up"
behavior that has not been explained.

## What a completed decomposition produces

- one callable the receiver function (operator) or composition (task graph), with explicit ports,
  units/axes, state/order and failure semantics;
- direct tests and source/independent evidence;
- a formal asset contract and the derived documentation;
- a candidate capability record that the receiver can later accept, reject or map onto its
  capability matrix.

It is a reusable scientific building block, not a project mirror.

## How it is used

- users call it like a SciPy function, without installing or running the source project;
- workflows compose functions into analyses (equilibrium, dispersion, transport,
  diagnostics, geometry, numerical kernels);
- agents retrieve the manual/contract, choose functions, supply units and compose calls
  instead of inventing scientific formulas;
- the manual teaches the model, a real example, the meaning of the result and its limits;
- the capability matrix and documentation record what exists and what remains a candidate.

## Where and why it is used

The target is broad coverage of controlled fusion work. The library is used where a
correct, inspectable, composable scientific primitive is more valuable than a complete
application: analysis workflows, simulation post-processing, model coupling, teaching and
agent-assisted coding.

Correctness is the product. If a delivered function is not demonstrably correct, users can
use the mature project directly; the decomposition has no reason to exist. Coverage must
never be traded for correctness.

## Proactive supply and handoff boundary

Decomposition is an independent supply line. the receiver aims to cover most controlled-fusion
work, so the line must run ahead of current demand; it does not wait for a capability-demand
map or capability matrix.

- The decomposition line: identifies valuable source capabilities, understands/translates/
  rewrites them, produces evidence, tests and contracts, and delivers a candidate inventory
  and admission-shaped submission.
- the receiver: decides acceptance, overlap/reception, catalog integration and what enters the
  matrix.
- Once the correct, evidence-backed delivery is handed off, the decomposition line's
  responsibility ends. It does not wait for acceptance or make merge decisions.
- The 10–20% figure is a receiver-side expectation of carried capabilities, not an
  extraction filter or a LOC target.

## Runtime, storage and delivery are independent

Decomposition can run anywhere suitable: a server cluster, a cloud runner, a project
container, or a local machine. Do not assume a fixed E-drive layout, a project registry,
a methodology mirror or a container metadata directory.

The runtime work product (WORK/INBOX, probes, scratch logs, temporary datasets and
runtime containers) is disposable. Only the final candidate delivery **and the evidence
needed to prove correctness** must survive and be handed to the receiver. Delivery may be a
cloud Git repository, an archive, an object store or any other reviewable transfer; E is
an optional local staging/archive location, not the delivery authority.
