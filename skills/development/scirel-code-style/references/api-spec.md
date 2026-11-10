# Public API rules

These rules follow SciPy where they fit: a small root namespace, domain subpackages with explicit exports, plain functions with explicit parameters, and numpydoc docstrings.

## Layout

| Rule | Detail |
| --- | --- |
| Namespaces | Users import from `scirel.<domain>`. The root only lists domains |
| Exports | Each domain has one `__all__`. Anything else is private |
| Lazy loading | Importing a domain does not load SciPy or implementation modules. The lazy table is the single source for `__all__` |
| Dependencies | Domains may depend on lower layers. Two domains must not depend on each other |
| Size | When a domain mixes unrelated physics, split it by physics, not by file count |

## Domains

| Domain | Physics |
| --- | --- |
| `field`, `electromagnetism`, `configurations` | Vacuum magnetic fields, coils, devices |
| `geometry` | Meshes, flux surfaces, field lines, chords, splines |
| `equilibrium`, `closures` | Force balance, Picard iteration, pressure closures |
| `kinetic` | Waves and kinetic theory: dispersion, plasma functions, Vlasov–Poisson, fluid spectra |
| `neutrals` | Neutral transport: velocity meshes, generations, collision sources and moments |
| `mirror` | Mirror confinement: invariant distributions, end loss, Frank–Egedal closure |
| `collisions`, `physics`, `fusion`, `plasma`, `neoclassical`, `source`, `dielectric` | Rates, scales and local models |
| `diagnostics`, `inference`, `fvm`, `numerics`, `io` | Residuals, parameter estimation, numerics, file formats |

## Names

- Functions are `verb_object` in `snake_case`.
- Use these verbs:

| Verb | Meaning |
| --- | --- |
| `compute` | Direct formula |
| `evaluate` | Function or kernel at given points |
| `solve` | Equation or eigenproblem, including iteration |
| `assemble` | Build a matrix or a source |
| `reduce` | Moments or integrals of a distribution |
| `build`, `make` | Build a mesh, grid or object |
| `scan` | Repeat over a parameter |
| `update` | One iteration step |
| `sample`, `interpolate`, `project`, `normalize`, `transform` | Their usual meaning |

- Avoid opaque abbreviations and source-project prefixes in public names.
- Classes are `CapWords` nouns.
- Exactly one public function has each name across the package. Helpers such as a composition's wiring function are private.

## Parameters

- Name every parameter in the signature. Do not take an `inputs` mapping or `**kwargs`.
- Required physical inputs come first and may be positional. Options and solver controls are keyword-only with stated defaults.
- Array axes and units go in the docstring and contract.
- Dependencies such as solvers are not public parameters unless swapping them is a documented capability.

## Returns and errors

- A function returning several quantities returns `scirel._result.Result`, a `dict` subclass with attribute access on the pattern of `scipy.optimize.OptimizeResult`. Existing mapping use keeps working. Plain `dict` returns migrate as they are touched.
- One function returns one shape on every branch. Do not mix tuples and mappings.
- Invalid input raises `ValueError`, or `TypeError` for a wrong kind, and the message names the parameter. An unrepresentable result raises `FloatingPointError`.
- If a value can be supplied two ways, require exactly one.
- A solver reports non-convergence as declared in its contract, and never returns it looking converged.
- A status field must not hide a programming error: catch the numerical exceptions you expect, not `Exception`.

## Docstrings

Use the full numpydoc layout:

| Section | Requirement |
| --- | --- |
| Parameters | Every parameter, with `[unit]` for a dimensional value, and shape, meaning and default behaviour |
| Returns | Every returned item with the same detail |
| Raises | Each exception and what triggers it |
| See Also | Related functions |
| Notes | Formula, conventions and limits |
| References | Sources for formulas |
| Examples | Runs as a doctest, and is the same code as the contract example |

Bring existing functions up to this as they are touched. New functions meet it from the start.

## One truth

| Fact | Owner | Derived copy |
| --- | --- | --- |
| Names, order, defaults | Signature | Contract `public_api`, `inputs` |
| Units, shapes, meaning, returned items | Docstring | Contract `inputs`, `outputs` |
| Exceptions | Docstring `Raises` | Contract `failure_semantics` |
| Example | Docstring `Examples` | Contract `example` |
| Public names | `__all__` | Contract `public_api`, documentation |
| Model, applicability, evidence, limitations | Contract | None |

`check_contract_sync.py` enforces the derived columns for the assets in its scope list.

## Deprecation

Nothing is published to PyPI yet; SciRel is used internally or delivered as a built-in capability, so the pre-release rule applies.

Before the first public release, rename directly and update every caller, with no alias. After it, keep an old name for at least two minor releases, emit `DeprecationWarning` naming the replacement, and record it in the release notes. Do not change the meaning of an existing name or parameter in place.

## Migration status

Open work is tracked in GitHub issues with the `agent-task` label. Each change keeps `scirel-acceptance` green.
