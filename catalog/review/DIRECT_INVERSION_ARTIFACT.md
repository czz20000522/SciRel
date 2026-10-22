# Direct-inversion artifact release condition

The only remaining hold is:

```text
scirel.inference.direct-anisotropic-inversion
```

## Why it is held

- Assembly-level source parity with the Pleiades task graph is established.
- Its former axisymmetric dependency is now released.
- The Pleiades FINAL payload lacks the exact admitted graph artifact; only the
  admitted hashes and a later snapshot survive.

## What must be restored

Record, in this file or `HOLD.json`:

- the exact admitted graph artifact id/SHA-256 (the current records cite
  `graph.py 6d1c3b52...`, `task_graph.yaml 997b3335...`, `vcommit_d196...`);
- where the artifact lives (E archive, object store, commit path);
- the comparison target (which snapshot/file it must match);
- the pass condition: exact artifact match, direct composition suite, and
  physical-closure fixture green with the released axisymmetric solver.

Until those are present, do not replace the missing artifact with a plausible
graph or a later snapshot without recording the substitution.
