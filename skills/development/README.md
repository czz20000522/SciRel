# SciRel development skills

This directory is the independent development package for D2 integration, D3
project delivery, correction, normalization, review preparation and
development-only claim validation. Its inputs are exact decomposition packets;
it does not load or link to the decomposition package. Repeated guidance may
be duplicated here deliberately so each package can be shipped and pinned
without a cross-package dependency.

These skills produce candidates, project artifacts and review packets. They do
not grant human endorsement, redistribution rights or release authority.

Daily work runs in `development` mode by default. Capability counts, documents
and the development catalog may change with the current Git tree. Candidate
and public release work is an explicit `release_freeze` mode; it derives a new
manifest and exact closure once, instead of making every development change
advance a wheel version or run the full platform matrix.

The repository documents are the public, handoff-friendly source for project
and development methods. Skills are personal routing and method overlays; they
may point to the canonical documents or add a narrowly scoped working habit,
but must not hide or duplicate the general policy.

Lifecycle route: [post-acceptance-runtime-cleanup](post-acceptance-runtime-cleanup/SKILL.md)
routes acceptance-owned cleanup to the repository's runtime-asset policy.

For the mode boundary and transition triggers, read [the development lifecycle](references/development-lifecycle.md).
