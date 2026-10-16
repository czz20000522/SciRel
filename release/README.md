# SciRel release boundaries

The source checkout follows a Git single-source release model. `pyproject.toml`,
scientific source, exact documents, API documentation, release notes, and the
platform receipt for a candidate are bound to one commit. A wheel or rendered
document is a generated artifact of that commit, not a second versioned source
copy. Git history and signed tags carry version history; new candidates must
not add parallel per-version copies of the same source or documentation.


SciRel has one canonical current *candidate receipt* in [`CURRENT.json`](CURRENT.json).
It is derived coordination metadata for the checkout; it is not a second version
source. `pyproject.toml` and the Git commit/tag remain authoritative for package
identity and history.
The wheel and documentation subdirectories retain compatibility pointers for
older consumers, but they must not introduce another version identity. The
repository has one handbook source at `tools/docs/handbook.json`; selected
release views are generated outside the checkout. Git history and tags carry
the version history; generated wheels and rendered documents remain external
artifacts.

The tuple binds:

- the exact source revision and package version;
- the current wheel artifact manifest reference, digest and dependency closure;
- the current document selection and handbook digest; and
- each platform receipt used by the bounded compatibility claim.

`CURRENT.json` may continue to point at an earlier exact commit while the checkout
contains later development commits. Those commits are post-candidate work; they do
not change the bound wheel or documentation. Before moving the candidate forward,
commit the complete follow-up change, rebuild the wheel and documentation from that
new ref, and update the tuple and receipts together. Never rebuild an older version
number from a newer checkout and overwrite its external artifacts.

`release/CURRENT.json` stores only logical `manifest_ref` keys for generated
wheel and documentation artifacts. They are resolved against an external
artifact root during release validation; no `build/releases/` path or generated
wheel is part of the Git checkout. Run
`scripts/validate_release_alignment.py --artifact-root <root>` for byte-level
verification. Without that option, the validator reports the external bytes as
unchecked while still validating the reference shape and inline digests.

Historical candidate identities are preserved by Git commits, tags, and the
short release notes under `docs/release/`. Do not add a per-version wheel JSON,
a parallel documentation tree, or a complete generated catalog snapshot to this
source tree merely to record a candidate.

The project still has three *evidence lines*:

1. External project FINAL artifacts live on the Home E drive under
   `/e/SciRel-lab/projects/<project>/decomposition/FINAL/`. Source snapshots and
   D0-D3 work remain outside this repository.
2. The wheel line records the current cumulative SciRel runtime and exact wheel
   digest. A wheel record names the selected capabilities and the external
   project FINAL manifests consumed by that integration; Git history carries
   prior wheel versions instead of retaining every wheel in the working tree.
3. The documentation line records the current handbook/catalog selection. A
   documentation record may advance without rebuilding the wheel, but the
   current selection must remain exactly bound to the current wheel closure.

The current maintainer reconciliation of delivered scope, integrated code,
packaged runtime and documentation is in [project intake reconciliation](projects/README.md).

Only the final project manifest is an intake surface. Intermediate candidates,
source checkouts, run directories, and local build scratch are not release
inputs.

External project descriptors and directory indexes contain identity and paths,
not progress or SciRel merge/release flags. FINAL describes the external
decomposition result; SciRel records its own integration and release decisions.
Completed workers retain one current FINAL and the source. Delete obsolete
progress copies and redundant work after checking that the required scientific
evidence and license material are included in FINAL. A frozen receipt is evidence
for its original candidate, not a current task or a reason to repeat an integration.

Necessary documents and scientific evidence from superseded catalogs and workspaces
belong in the corresponding project's FINAL. Delete obsolete catalog copies,
build scratch and temporary migration archives after verifying that coverage;
they are not a separate permanent asset line.

Local `.runtime/` is a development workspace that may hold evidence for current
work. It is not a wheel intake or a permanent substitute for external FINAL.
