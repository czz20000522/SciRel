---
name: post-acceptance-runtime-cleanup
description: Route post-acceptance cleanup of SciRel project runtime assets to the repository lifecycle policy when a project is accepted, merged, archived, handed off, or under storage pressure.
---

# Post-acceptance runtime cleanup

This is a personal routing layer. The repository document is the canonical policy; this skill must not become a second copy of the
project's retention, deletion, evidence, or approval rules. It does not grant deletion authority or replace project manifests and receipts.

Read and follow the repository policy in
[`catalog/RECORDS.md`](../../../catalog/RECORDS.md). For the executable
classification, disposition, and readback sequence, read
[`artifact-lifecycle-closeout.md`](../references/artifact-lifecycle-closeout.md)
and the [development-skill operating contract](../references/scirel-development-core.md).
If the task changes container, WSL, Docker, mount, or storage placement, route
the environment part through the `project-environments` skill.

Use this route after acceptance/receipt, merge, project archive or handoff, and
when a bounded storage audit identifies accumulated runtime assets. Before any
mutation, locate the exact manifest or receipt, receiving owner, current
consumer, and run state. Classify every owned path as process, result,
temporary, or frozen delivery; create an exact `RETAIN`/`RETIRE`/`HOLD`
disposition; apply only the reviewed temporary set; and read back filesystem,
Git, process, and consumer state. Finish with the minimum closeout record from
the reference, even when cleanup is partial. Unresolved scope remains
`UNKNOWN` or `HOLD`; never infer deletion from a directory name, age, or size.
