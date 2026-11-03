# FINAL root binding

`FILES.json` and `ROOT.sha256` are excluded from the `FILES.json` membership
list. `FINAL.json` and `PATH_MAP.json` are included. The outer root binding
covers the three control files without introducing a manifest self-hash.

## Format

One line per bound file, in the fixed order below, exactly:

```text
<sha256>  <path>
```

Two ASCII spaces separate digest and path. Use lowercase hexadecimal digests,
the exact case-sensitive names below, UTF-8 without a byte-order mark, and LF
line endings, including one final LF. The bound order is exactly:

```text
FINAL.json
FILES.json
PATH_MAP.json
```

This order is not alphabetical sorting. Payload entries in `FILES.json` have
their own case-sensitive POSIX-string sort order.

## Derivation

```text
members = ("FINAL.json", "FILES.json", "PATH_MAP.json")
lines = concat(sha256(actual_bytes(name)) + "  " + name + "\n" for name in members)
root_digest = sha256(UTF8(lines))
```

Write `root_digest  ROOT.sha256\n` first, followed by those three lines. A receiver
recomputes the member digests and the concatenation digest, then compares the
whole file byte for byte. The producer command in [README.md](README.md)
generates all controls together. `validate_admission.py --emit-root` is an
explicit authoring action for a new, unsealed directory; read-only validation
never repairs an existing submission.

It binds bytes, not truth: it does not prove the members exist (that is
`FILES.json` plus the byte check), scientific validity, or scope.
