---
name: scientific-project-implementation
description: Deliver a user's persistent scientific program and outputs using already selected SciRel capabilities, without adding harness or library-development machinery.
---

# Deliver the user's scientific program

Continue [the user-facing solving flow](../scirel-solving/SKILL.md); reuse confirmed requirements and the existing capability selection. This skill is for files the user actually needs, not a mandatory extra stage for every calculation.

- Use the host-authorized workspace, installed SciRel and declared runtime dependencies. Do not depend on the source checkout or undisclosed developer tools.
- Keep the program small: input handling, calls to selected public APIs, compatible connections and result delivery. Use applicable SciRel science; implement only an established missing capability separately, with independent validation and an explicit limit on its claims.
- Respect the project's file conventions and the user's chosen output format. Document scientific assumptions and units where they affect use. Do not create release manifests, review packets or a new catalog for a one-off application.
- Run the normal entrypoint on confirmed inputs, inspect the saved outputs and perform the [result checks](../scirel-solving/references/result-checks.md). Preserve complete requested coverage and failures. Repeat unchanged inputs when reproducibility is claimed.
- Deliver files, the shortest useful run command, the result and material limitations. The host supplies artifact links, execution history, permissions and recovery; do not implement these as SciRel project features.

A successful application supports its tested scope, not a claim that the entire library is approved. For an explicitly assigned staged library-development handoff, use the separate [development contract](../../references/scirel-development-core.md).
