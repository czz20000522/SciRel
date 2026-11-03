# Direct-inversion artifact release condition

`scirel.inference.direct-anisotropic-inversion` is held because the exact admitted
graph artifact is missing, so the composition is not bound to a reviewed graph.

To release it, record the artifact identity and SHA-256, where it lives, what it
must match, and the pass condition: exact artifact match, direct composition suite
and physical-closure fixture green.

Do not replace the missing artifact with a plausible graph or a later snapshot
without recording the substitution.
