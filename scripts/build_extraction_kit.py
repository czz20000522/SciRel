"""Build the extraction kit: a frozen SciReL checkout that an extraction container works in.

The kit is a directory with two entries:

``scirel/``
    A depth-1 git clone of one SciReL commit. Its ``HEAD`` is the real commit id, so a patch
    series made with ``git format-patch <commit>`` inside it applies unchanged on the merge line,
    and ``scripts/validate_extraction_package.py --repo scirel`` runs the same checks there.
``KIT.md``
    The frozen commit and the commands an extractor needs.

The clone carries no remote, no ``FETCH_HEAD`` and no path of the machine that built it, because
the kit leaves this repository together with the extraction skill.

Usage::

    python scripts/build_extraction_kit.py --output <new directory> [--commit <rev>]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "extraction"
UPLOAD_PACK = "git -c uploadpack.allowReachableSHA1InWant=true upload-pack"

KIT_TEMPLATE = """\
# 拆解工具包

- 冻结 SciReL commit：`{commit}`
- 冻结版 SciReL 的 git 目录：`scirel/`（只含这一个提交）

## 用法

1. 在 `scirel/` 里检索合同、修改 `src/`、`tests/`、`catalog/`，并在分支 `{branch}` 上提交。
2. `PACKAGE.md` 的"冻结 SciReL commit"写上面这个 commit。
3. 生成补丁：

   ```sh
   git -C scirel format-patch {commit} -o <拆解包目录>/patch
   ```

4. 自检，合并线运行的也是同一条命令：

   ```sh
   cd scirel && python scripts/validate_extraction_package.py <拆解包目录> --repo .
   ```

   退出码为 0 才能把 `PACKAGE.md` 的状态写成 `done`。`--fast` 的退出码永远是 2，不算通过。

方法见 `scirel/skills/extraction/scientific-computation-asset-extraction/SKILL.md`。
"""


class KitError(RuntimeError):
    pass


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise KitError(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")
    return result.stdout.strip()


def resolve_commit(repo: Path, revision: str) -> str:
    """Return the full commit id that ``revision`` names in ``repo``."""
    try:
        return _git(["rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"], repo)
    except KitError:
        raise KitError(
            f"--commit {revision!r} does not name a commit in {repo}; "
            "pass a commit id, tag or branch that exists there"
        ) from None


def build_kit(repo: Path, revision: str, output: Path) -> str:
    """Create the kit for ``revision`` of ``repo`` in the new directory ``output``.

    Returns the frozen commit id. ``output`` must not exist yet, so a kit is never mixed with
    an earlier one.
    """
    repo = Path(repo).resolve()
    output = Path(output)
    if output.exists():
        raise KitError(f"--output {output} already exists; choose a new directory")
    commit = resolve_commit(repo, revision)
    clone = output / "scirel"
    clone.mkdir(parents=True)
    _git(["init", "--quiet", "--initial-branch", BRANCH], clone)
    _git(
        ["fetch", "--quiet", "--depth", "1", "--upload-pack", UPLOAD_PACK, repo.as_uri(), commit],
        clone,
    )
    _git(["reset", "--quiet", "--hard", commit], clone)
    (clone / ".git" / "FETCH_HEAD").unlink(missing_ok=True)
    head = _git(["rev-parse", "HEAD"], clone)
    if head != commit:
        raise KitError(f"kit HEAD is {head}, expected the frozen commit {commit}")
    (output / "KIT.md").write_text(
        KIT_TEMPLATE.format(commit=commit, branch=BRANCH), encoding="utf-8"
    )
    return commit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True, help="new directory for the kit")
    parser.add_argument("--commit", default="HEAD", help="SciReL revision to freeze (default HEAD)")
    parser.add_argument("--repo", type=Path, default=ROOT, help="SciReL git repository")
    args = parser.parse_args(argv)
    try:
        commit = build_kit(args.repo, args.commit, args.output)
    except KitError as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    print(f"PASS  extraction kit for {commit} in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
