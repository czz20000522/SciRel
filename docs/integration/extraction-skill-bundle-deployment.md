# Extraction skill bundle deployment

`skills/extraction/` is the authority for the standalone D0-D3 decomposition
skills. A harness may load a deployed copy, but the copy is never an editing
source and does not belong in the CodeFusion repository. The separate
`skills/development/` package owns merge, correction, project delivery and
review work; the two packages have no direct skill references.

Build a new immutable artifact from the current SciRel checkout:

```powershell
python scripts/build_extraction_skill_bundle.py --output build/skill-bundles/scirel-extraction-<new-id>.zip
```

The builder fails unless all seven D0-D3 decomposition entrypoints exist. It
excludes interpreter caches, sorts UTF-8 paths, fixes zip metadata, records
every file size and SHA-256 digest, and binds the exact decomposition set under
`scirel.decomposition-skill-bundle`. The output path must not exist; a new
bundle replaces the active bundle at the same target path after verification.

Transfer the zip and `scripts/install_extraction_skill_bundle.py` to the runtime host. Inspect the exact plan first,
then install into that host's Codex skill root, not a CodeFusion checkout:

```sh
python3 install_extraction_skill_bundle.py \
  --bundle scirel-extraction-<new-id>.zip \
  --target-skill-root "$CODEX_HOME/skills" \
  --dry-run
python3 install_extraction_skill_bundle.py \
  --bundle scirel-extraction-<new-id>.zip \
  --target-skill-root "$CODEX_HOME/skills"
```

The installer verifies the manifest and every payload digest before writing. It stores one content-addressed bundle,
switches the seven stable decomposition entrypoints through
`.scirel-extraction-active`, writes an install receipt, and removes the
previous SciRel-owned bundle after the switch. It does not create a backup. Existing non-symlink skill directories
fail closed instead of being overwritten. Installed bundle directories and files are read-only so interpreter caches
or task-local output cannot mutate the content-addressed runtime copy; run Python checks with
`PYTHONDONTWRITEBYTECODE=1` and keep all run artifacts outside the skill root.

For a pinned session that may still read its deployed files, install a new release into a new run-owned skill
root instead of switching that shared root: the installer removes previous owned bundle directories. Keep the old
root available for its live/frozen consumers. Native Claude can use the same verified D0-D3 payload through
its own project skill root; its runtime adapter supplies Agent definitions, explicit skill preloading, MCP config
and the material entry. Check effective tool visibility and actual calls after deployment. A bundle digest alone
proves installed bytes, not method adoption or delegation. See the extraction skill's
[material access and preprocessing](../../skills/extraction/scientific-computation-asset-extraction/references/material_access_and_preprocessing.md).

Running sessions keep their pinned context. Restart or explicitly resume a run only after recording the installed
bundle digest, then use the deployed validator and fresh attempt identities. A deployment does not relabel or mutate
old run receipts; `.dev` evidence remains superseded history.

## Private model configuration

The control checkout keeps model credentials in the Git-ignored
`.runtime/spark-model.local.json`, with string fields `url`, `model`, and `key`.
This file is a local secret, not part of a skill bundle, wheel, review packet, or
scientific contract. Never print its contents or stage it with `git add -f`.

Use the maintained transfer entrypoint from the control checkout:

```powershell
python scripts/spark_codex.py sync --host <ssh-host>
```

It sends the JSON through SSH stdin, installs a private mode-0600 copy at
`~/.config/scirel/spark-model.local.json`, and installs
`~/.local/bin/scirel-codex`. The launcher reads that copy on every invocation and
supplies the key through `SCIREL_MODEL_API_KEY`, never command arguments. It uses
the Responses API and leaves shared Codex configuration and authentication files
unchanged. Re-run `sync` after changing the control JSON.

For runs explicitly configured to use Codex, use `scirel-codex` in place of the direct `codex` executable.
This adapter does not select the execution harness: caller-selected native Claude runs retain their private
Claude provider/model route and use their native Agent tools. Remove competing model/provider/profile
arguments; the launcher rejects them so stale script flags cannot select another
model. Other Codex arguments, working directories, permissions and session IDs
remain the launcher's caller's responsibility.

A worker's isolated runtime must admit the installed launcher, Python script and
private JSON at their actual paths, read-only where applicable, without granting
access to unrelated credentials or candidate answers. Switch existing runs at an
owner-controlled safe boundary, preserving original sessions and long-running
scientific processes. Verify a real tool call through each affected launcher;
an HTTP probe alone does not prove the coordinator/worker integration works.
