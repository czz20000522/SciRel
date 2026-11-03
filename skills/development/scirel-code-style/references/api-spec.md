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

- A function returning several quantities returns a `dict` with documented keys, as the catalog does today. Do not mix tuples and dicts within one function.
- Invalid input raises `ValueError`, or `TypeError` for a wrong kind. An unrepresentable result raises `FloatingPointError`.
- A solver reports non-convergence as declared in its contract, and never returns it looking converged.

## Docstrings

Use numpydoc sections: `Parameters`, `Returns`, `Raises`, `Notes` for formulas and sources, and `Examples` where short. State units in the parameter description.

## Migration status

Each batch keeps `scirel-acceptance` green.

| Batch | Change | Status |
| --- | --- | --- |
| 1 | ruff configuration and formatting | see Git history |
| 2 | Private composition helpers, removing duplicate `run_composition` | see Git history |
| 3 | Explicit parameters for compositions | see Git history |
| 4 | Split `kinetic` into `kinetic`, `neutrals`, `mirror` | see Git history |
| 5 | Unified names | see Git history |
