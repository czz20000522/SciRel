# One truth for each fact

Parameter names, units, defaults, failure behaviour and examples tend to live in several places: signature, docstring, manual, a schema or a separate record. Each extra copy will drift. Editing whichever copy you noticed makes it worse.

## The rule

Every fact has exactly one owner. Every other appearance is derived from it, by generation or by a check that fails the build. "We will keep them in step" is not a mechanism.

## Choosing the owner

Use the place that changes together with the behaviour, and the one the code cannot run without:

| Fact | Usual owner |
| --- | --- |
| Parameter names, order, defaults | The signature |
| Types, units, shapes, meaning of parameters and returns | The docstring |
| Exceptions | The docstring's Raises section, checked by tests that trigger them |
| Examples | The docstring, run as doctests |
| The list of public names | `__all__` |
| Knowledge that does not fit a docstring: model scope, evidence, known limits | A separate record, which should not restate the above |

A separate record is worthwhile only for facts with no natural home in the code. Do not repeat the signature there unless it is generated or checked.

## Generate, or check

Prefer generating when the copy has no human content. Otherwise write a sync check, which should:

- Compare the live signature with the docstring and with any record, by value.
- Run every example.
- Report each disagreement with both values and the file to fix.
- Fail the project's normal check command, so that nobody can forget it.

`scripts/check_docs_sync.py` covers the code side and is a starting point for adding your project's record format.

## Adopting a check on an existing library

A check that fails everywhere gets switched off. So adopt it as a ratchet:

1. Keep a list of what the check covers, starting with the functions that matter most.
2. Make the check strict inside that list.
3. Grow the list and never shrink it. Removing an entry needs a stated reason.
4. For pattern scans, record a baseline of current hits, and fail only on new ones.

## Fixing a disagreement

When two copies disagree, do not assume the newer one is right. Find out what the code does, and what it should do. If the code is wrong, that is a behaviour change and needs its own decision. If the document is wrong, fix the owner and regenerate the rest. Fix every copy in one commit.
