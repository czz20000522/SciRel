"""把本机验收 receipt 渲染成可直接粘贴到 PR 的固定模板。

只读：只读 `.git/scirel-acceptance/receipts/` 和 `git rev-parse`，不写 receipt、不改 Git 状态、
不跑容器。模板原文、字段来源和失效条件见
`skills/development/scirel-acceptance/references/pr-evidence.md`。

判据复用 `scripts/dev_container.py`（`check_receipt_path`、`_read_check_receipt`、
`_check_receipt_is_fresh`、`candidate_tree`），不另写一套匹配和过期逻辑。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import platform
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DEV_CONTAINER = ROOT / "scripts" / "dev_container.py"
MODULE_NAME = "dev_container"
RECEIPT_RETENTION_DAYS = 30

DIRTY_WORKTREE = """\
工作区不干净：有未提交或未跟踪文件，当前 tree 不能代表将要推送的内容。

`candidate_tree()`（`scripts/dev_container.py:646-658`）在这种情况下返回 None，也就是说此刻跑检查
也写不出 receipt。主 checkout 里未跟踪的 `.worktrees/` 目录会稳定落在这一状态，见 #120。

先提交、stash 或清掉这些文件，再重新运行本脚本。"""

RECOVERY = """\
处理方式：在最终提交上重新跑 `python3 scripts/dev_container.py check`，等它通过后再运行本脚本。"""


class EvidenceError(RuntimeError):
    """没有可用 receipt 时抛出，避免产出无法复核的验收结论。"""


def load_dev_container():
    """按路径加载开发容器脚本，复用它的 receipt 判据。"""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, DEV_CONTAINER)
    if spec is None or spec.loader is None:
        raise EvidenceError(f"无法加载 {DEV_CONTAINER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(MODULE_NAME, module)
    spec.loader.exec_module(module)
    return module


DEV = load_dev_container()


@dataclass(frozen=True)
class Evidence:
    """一份可用于 PR 的验收证据。"""

    tree: str
    architecture: str
    checked_at_unix: float
    receipt_name: str
    commit_short: str
    commit_subject: str
    actor: str


def git(*arguments: str) -> str:
    try:
        return DEV.git_output(*arguments)
    except RuntimeError as error:
        raise EvidenceError(f"git {' '.join(arguments)} 失败：{error}") from error


def resolve_actor(explicit: str | None) -> str:
    """返回填表人：命令行显式给出优先，否则取本机 Git 身份。不是 receipt 字段。"""
    if explicit:
        return explicit.strip()
    name = _optional_git("config", "user.name")
    email = _optional_git("config", "user.email")
    if name and email:
        return f"{name} <{email}>"
    return name or email or "未记录（本机未配置 Git 身份，可用 --actor 指定）"


def _optional_git(*arguments: str) -> str:
    try:
        return DEV.git_output(*arguments)
    except RuntimeError:
        return ""


def head_commit() -> tuple[str, str]:
    """返回 HEAD 的短 sha 和标题：匹配用的 tree 就是 HEAD 的 tree，所以提交一定是 HEAD。"""
    return git("rev-parse", "--short", "HEAD"), git("log", "-1", "--format=%s")


def _cached_receipts():
    """返回缓存里可读的 receipt 列表，用于给失败的匹配说明原因。"""
    try:
        directory = DEV.validated_receipt_directory()
    except (OSError, RuntimeError, ValueError):
        return ()
    receipts = []
    try:
        paths = sorted(directory.glob("*.json"))
    except OSError:
        return ()
    for path in paths:
        try:
            receipt, _ = DEV._read_check_receipt(path)
        except (OSError, RuntimeError, ValueError):
            continue
        if receipt is not None:
            receipts.append(receipt)
    return tuple(receipts)


def _missing_reason(tree: str, architecture: str) -> str:
    """说明为什么没有匹配的 receipt：tree 变了，还是架构不同。"""
    receipts = _cached_receipts()
    other_architectures = sorted(
        {
            str(receipt["architecture"])
            for receipt in receipts
            if receipt["tree"] == tree and receipt["architecture"] != architecture
        }
    )
    other_trees = sorted(
        {
            str(receipt["tree"])[:12]
            for receipt in receipts
            if receipt["architecture"] == architecture and receipt["tree"] != tree
        }
    )
    if other_architectures:
        return (
            f"tree 能对上，但 receipt 是在 {', '.join(other_architectures)} 上写的，本机是 "
            f"{architecture}：receipt 按 tree + architecture 分开存放，换机器或换架构要重跑。"
        )
    if other_trees:
        return (
            f"本机 {architecture} 上没有 tree {tree[:12]} 的 receipt，"
            f"缓存里只有其他 tree 的 receipt（{', '.join(other_trees)}）。"
            "tree 不匹配通常意味着 HEAD 被 rebase、amend 或新提交改写过，旧 receipt 只证明改写前的版本。"
        )
    return f"缓存里没有任何匹配 tree {tree[:12]} + {architecture} 的 receipt。"


def collect(actor: str | None = None, *, now: float | None = None) -> Evidence:
    """读取并校验收据；任何一项不满足都抛 EvidenceError，不降级成"大概通过"。"""
    moment = time.time() if now is None else now
    if DEV.candidate_tree() is None:
        raise EvidenceError(DIRTY_WORKTREE)

    tree = git("rev-parse", "HEAD^{tree}")
    architecture = platform.machine()
    path = DEV.check_receipt_path(tree, architecture)
    try:
        # 写入方用临时文件加 os.replace 原子落盘，读出的一定是完整文件，因此不加锁也不写任何东西。
        receipt, _ = DEV._read_check_receipt(
            path,
            expected_tree=tree,
            expected_architecture=architecture,
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise EvidenceError(f"读不到本地验收 receipt：{error}\n\n{RECOVERY}") from error

    if receipt is None:
        raise EvidenceError(
            f"没有可用的验收 receipt。\n{_missing_reason(tree, architecture)}\n\n{RECOVERY}"
        )

    checked_at = float(receipt["checked_at_unix"])
    if not DEV._check_receipt_is_fresh(receipt, moment):
        age = max(0.0, moment - checked_at) / 86400
        raise EvidenceError(
            f"receipt 已过期：{age:.1f} 天前写入，超过 {RECEIPT_RETENTION_DAYS} 天保留期"
            f"（`scripts/dev_container.py:32`、`_check_receipt_is_fresh`）。\n\n{RECOVERY}"
        )

    commit_short, commit_subject = head_commit()

    return Evidence(
        tree=tree,
        architecture=str(receipt["architecture"]),
        checked_at_unix=checked_at,
        receipt_name=path.name,
        commit_short=commit_short,
        commit_subject=commit_subject,
        actor=resolve_actor(actor),
    )


def local_time(checked_at_unix: float) -> str:
    return datetime.fromtimestamp(checked_at_unix).astimezone().isoformat(timespec="seconds")


def utc_time(checked_at_unix: float) -> str:
    return (
        datetime.fromtimestamp(checked_at_unix, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def render(evidence: Evidence) -> str:
    """按固定模板渲染；改这里等于改模板，必须同时更新 references/pr-evidence.md。"""
    return "\n".join(
        [
            "### 本地容器验收证据",
            "",
            "- 结论：本 clone 上某个 checkout 在该 tree 上跑过完整检查，`check_all.py` 以 "
            "`ALL GREEN` 结束，退出码 0",
            "- 依据：`scripts/dev_container.py:867-873`，`run_check()` 只在检查退出码为 0 时"
            "调用 `record_check_receipt()`；因此存在匹配的 receipt 即等价于退出码 0",
            f"- 最终 tree：`{evidence.tree}`（HEAD 提交 `{evidence.commit_short}` "
            f"{evidence.commit_subject}）",
            f"- 架构（architecture）：`{evidence.architecture}`",
            f"- 检查完成时间：`{local_time(evidence.checked_at_unix)}`"
            f"（UTC `{utc_time(evidence.checked_at_unix)}`）",
            f"- receipt：`.git/scirel-acceptance/receipts/{evidence.receipt_name}`，schema 2，"
            "字段只有 tree、architecture、checked_at_unix",
            "- 匹配范围：receipt 存在本 clone 的共享 Git 元数据里，只按 tree + architecture 匹配，"
            "不记录执行者、Docker context、机器名，也不记录由哪个 checkout 写入",
            f"- 填表人：{evidence.actor}（填表人自行声明；receipt 不记录执行者，"
            "真正跑检查的人未知）",
            "- 复核：`git rev-parse HEAD^{tree}` 应得到同一个 tree；"
            "`python3 scripts/dev_container.py check` 可复跑",
            "",
            f"> 该证据只覆盖本机 `{evidence.architecture}` 引擎。跨设备抽查另行手动触发 "
            "`Cross-device check`；receipt 不记录 context，无法据此判断用的是哪个 Docker 引擎。",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acceptance_evidence.py",
        description="把本机验收 receipt 渲染成可直接粘贴到 PR 的固定模板（只读）。",
    )
    parser.add_argument("--actor", metavar="NAME", help="填表人，默认取本机 Git 用户名和邮箱")
    args = parser.parse_args(argv)
    try:
        evidence = collect(args.actor)
    except EvidenceError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    sys.stdout.write(render(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
