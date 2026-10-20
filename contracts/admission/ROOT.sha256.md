# FINAL root binding

`ROOT.sha256` is the only file in a FINAL directory that is not a member of
`FILES.json`. A payload manifest cannot bind itself, so the three control files
are bound by an outer file.

## Format

One line per bound file, sorted by lowercase path, exactly:

```text
<sha256>  <path>
```

Two spaces between digest and path; lowercase hex; relative POSIX path; one
trailing newline. The bound set is exactly:

```text
FINAL.json
FILES.json
PATH_MAP.json
```

## Derivation

```text
root_digest = sha256(concat("<sha256>  <path>\n" for each bound file))
```

Write on the first line `root_digest  ROOT.sha256`, followed by the three member
lines. A receiver recomputes the three member digests and the concatenation
digest, then compares the whole file byte-for-byte. `validate_admission.py`
verifies this; it can emit the file for a producer with `--emit-root`.

It binds bytes, not truth: it does not prove the members exist (that is
`FILES.json` plus the byte check), scientific validity, or scope.
