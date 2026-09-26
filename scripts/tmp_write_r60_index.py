"""One-off: write the r60 index section into the candidate materials index
with real SHA-256 digests. Run once from the repository root, then delete."""
import hashlib
from pathlib import Path

BASE = Path("review_candidates/2026-09-26-neutral-moments")
INDEX = Path("docs/evaluations/candidate-review-materials-index-2026-09-25.md")

files = ["review.md"] + sorted(
    f"proposal/{p.name}" for p in (BASE / "proposal").iterdir() if p.is_file()
)
lines = [
    "",
    "## Batch r60: KN1DPy neutral-moment diagnostics family (eleven operators)",
    "",
    f"Directory: `{BASE.as_posix()}/`",
    "Successor of batch r59: the r59 candidate files below keep their frozen "
    "r59 bytes and digests; this batch binds the new bytes.",
]
for rel in files:
    digest = hashlib.sha256((BASE / rel).read_bytes()).hexdigest()
    lines.append(f"- `{rel}` -- sha256 `{digest}`")

text = INDEX.read_text(encoding="utf-8")
marker = "## Batch r59:"
pos = text.index(marker)
text = text[:pos] + "\n".join(lines) + "\n\n" + text[pos:]
INDEX.write_text(text, encoding="utf-8", newline="\n")
print(f"index updated with {len(files)} entries")
