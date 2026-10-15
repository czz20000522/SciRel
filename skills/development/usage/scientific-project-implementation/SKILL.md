---
name: scientific-project-implementation
description: Turn a normalized scientific request into working files in the current project, using an authorized capability and exact runtime evidence.
---

# Scientific project implementation

Read [the shared operating contract](../../references/scirel-development-core.md).
Deliver actual project files and an executable result. The project owner supplies request/workspace truth; this skill
does not extract, publish, approve or mutate plugin lifecycle/catalog/release state.

## D3 route

1. Bind the normalized request, exact development or trusted wheel/catalog, supported platform, entrypoint,
   inputs/outputs and task-specific assumptions. Keep D1/D2 deliveries read-only and label development evidence.
2. Use [asset navigation](../scientific-asset-navigation/SKILL.md) for discovery and exact applicability; return
   library gaps to D2. Use the selected packaged Python/native entrypoints without the original source checkout or
   implicit development dependencies.
3. Implement in the persistent user workspace following its conventions. Put assumptions/source references in
   code comments/docstrings or the run record; do not duplicate a formal asset document for a one-off application.
4. Run the narrow affected entrypoint/tests, read files through a consumer path independent of serialization and
   rerun unchanged inputs to check ordinary repeatability. Preserve missing/failed rows and original grids.
5. Return files, command/runtime identity, inputs and output hashes, checks/observations, untested scope, capability
   gaps and exact next owner. A successful user case supports only its declared scope; it does not endorse the wheel
   or establish release readiness.

For evaluator-owned disposable copies, use the declared private result area and pinned wheel/catalog. Do not place
trial outputs in the user's persistent project or overwrite a prior deliverable without an explicit replacement.
