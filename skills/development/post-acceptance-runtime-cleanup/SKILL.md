---
name: post-acceptance-runtime-cleanup
description: Route post-acceptance cleanup of SciRel project runtime assets to the repository lifecycle policy when a project is accepted, merged, archived, handed off, or under storage pressure.
---

# Post-acceptance runtime cleanup

This is a personal routing layer. The repository document is the canonical policy; this skill must not become a second copy of the
project's retention, deletion, evidence, or approval rules. It does not grant deletion authority or replace project manifests and receipts.

Read and follow [运行资产清理责任与交接](../../../docs/design/project-and-distribution.md#运行资产清理责任与交接).
For stage ownership and handoff, also read [the development process](../../../docs/development-process.md) and
[the development-skill operating contract](../references/scirel-development-core.md). If the task changes container, WSL,
Docker, mount, or storage placement, route the environment part through the `project-environments` skill.

Use this route after acceptance/receipt, merge, project archive or handoff, and when a bounded storage audit identifies accumulated
runtime assets. My working method is to locate the exact manifest and receiving owner first, then follow the canonical document before
any mutation; unresolved scope is handed back as a documented stop rather than inferred from directory names or age.
