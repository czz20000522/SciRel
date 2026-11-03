---
name: scirel-code-style
description: Code style and public API rules for SciRel. Use when writing or reviewing code under src/scirel, adding a capability, or changing a public name or signature. Maintainer skill; not delivered to users.
---

# Write SciRel code

SciRel is pre-release, so public names can still change without compatibility aliases. A rename updates the implementation, contract, tests and documents together.

## Style

`pyproject.toml` configures ruff, and `scirel-acceptance` enforces it.

- Run `ruff format` and `ruff check`. Do not hand-format against the formatter.
- Keep one statement per line.
- Keep formatting changes in their own commit, separate from behaviour changes.
- Keep physics readable: name intermediate quantities after what they are, and put the formula or source in a comment or the docstring.
- A broad `except Exception` needs a comment explaining why a narrower type cannot work. It must not turn a programming error into a physics status.

## Public API

Follow [the API rules](references/api-spec.md). In short:

- Public callables live in `scirel.<domain>` and are listed in that domain's `__all__`. Implementation modules are private details.
- Names say what the function does, using the shared verb list. Classes use `CapWords`.
- Parameters are explicit. No `inputs` mapping, and no `**kwargs`.
- Docstrings follow numpydoc, with units in the parameter descriptions.
- Every public callable has a contract in `catalog/examples/`.

## When you change a public name or signature

1. Change the implementation and the domain's `__all__` and lazy exports.
2. Update the contract's `public_api` and any examples.
3. Update the tests and documents.
4. Rebind the Chinese reader digest (`source_sha256`) for each changed contract, and any chapter execution binding that names it.
5. Run the `scirel-acceptance` checks.

Do not leave an alias behind, and do not change physics in the same commit.
