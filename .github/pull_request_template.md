<!-- Closes #N, or Part of #N when items remain. -->

## What changed and why

<!-- A short summary. The full explanation belongs in the commit messages; do not add change-log files. -->

## Results

<!-- Pick one and delete the other. -->

- No numerical result changes.
- These results change, for this reason, with this reference:

## Checks

Paste the final lines of this command, run in the foreground on the final commit:

```sh
python3 scripts/dev_container.py check
```

Windows uses `py -3 scripts/dev_container.py check`. Local acceptance is the merge gate. GitHub Actions does not run automatically; maintainers may dispatch the optional Linux/amd64 cross-device check manually.

```text

```

## Before asking for review

- [ ] I read the issue's `Read first` list.
- [ ] I went through `skills/development/scirel-code-style/references/review-checklist.md`.
- [ ] All changed paths are inside the issue's declared write scope.
- [ ] I rebased on the latest `origin/main` and ran the check on the final commit.
- [ ] Formatting changes are in their own commit.
- [ ] Commit messages say what changed and why, in the imperative, one change per commit.
