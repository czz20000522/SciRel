# SciRel legacy release gate successor r33

Status: development review pending, not expert-approved, trusted, or publicly released. There is no trusted baseline; the first expert review still covers all 68 public assets. r32 is an unapproved development comparison, not a trusted scientific baseline.

## Engineering change and scientific scope

The prior per-item `approved` workflow could still call `SciRelWorkflow.release()`, write a release manifest through `SciRelPlugin.release()` or `complete_release()`, emit `scirel.release.completed`, and invoke `scripts/finalize_release.py` directly. None of those paths proved expert recognition of the whole frozen version and its cumulative scientific change. All now reject that shortcut. The plugin no longer advertises `scirel.release`, the approved-item review UI no longer offers `release`, and workflow snapshot restoration rejects a legacy release record. Candidate preparation, per-item expert review, development wheel construction, and the host's separate `PluginReleaseSnapshot` remain available.

This changes the SciRel workflow/plugin development interface. A CodeFusion caller using the old operation, action, completion event or finalizer must stop calling it; the neutral host artifact, identity and review primitives need no scientific special case. A new version-level expert recognition and independent release binding are still to be implemented. This gate does not itself grant trust.

No `src/scirel` scientific implementation, public callable signature, model condition, default, dependency edge or numerical assertion changed from r32. The implementation version advances from `0.1.0.dev17` to `0.1.0.dev18` to distinguish the new wheel. All 68 exact documents change only that version field; catalog coverage remains 68/68. The previous development snapshots and historical L1 evidence are untouched. The qualified L1 delivery root remains empty; historical withdrawn candidates are not treated as current frozen input.

## Review and limits

Relative to r32, there is no scientific implementation or contract delta. The engineering review should check the blocked entrypoints, existing host consumers, and the eventual version-level approval protocol. Because no trusted version exists, this comparison cannot reduce the first expert review of the 68 scientific assets. The prior source and science evidence can be reused only within its stated conditions; no new source parity or whole-project extraction is claimed here.

The repository affected selector ran 162 tests before the mechanical version change. After it, the selector correctly expanded to the whole suite: 889 passed and 43 retained-source tests skipped. All 68 documents passed source and installed runtime signature/example validation. The internal wheel installed offline into a Python 3.14.3 venv with system site-packages disabled; 627 installed scientific and composition tests passed, 43 retained-source tests skipped, and three user acceptance tasks passed. Exact commands and artifact digests are in the frozen test evidence.

License clearance, expert recognition, trusted promotion and public release remain open. The future public protocol must be normalized to `v1` before launch; the `.dev` schema names are development-only.
