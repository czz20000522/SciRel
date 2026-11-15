# Public API rules

These rules follow SciPy where they fit: a small root namespace, domain subpackages with explicit exports, plain functions with explicit parameters, and numpydoc docstrings.

## Layout

| Rule | Detail |
| --- | --- |
| Namespaces | Users import from `scirel.<domain>`. The root only lists domains |
| Exports | Each domain has one `__all__`. Anything else is private |
| Lazy loading | Importing a domain does not load SciPy or implementation modules. The lazy table is the single source for `__all__` |
| Numerics | Physics-agnostic tools live only under `scirel.numerics`, split by mathematical topic; use SciPy where it already provides the function |
| Size | When a domain mixes unrelated physics, split it by physics, not by file count |

## Domains

Domains form one-way layers. A domain may depend only on lower layers; an upward dependency is never allowed, and a same-layer dependency only when the whitelist below names it. No dependency may form a cycle. Imports inside function bodies count exactly like module-level imports. The whitelist governs same-layer dependencies only: downward edges need no entry, so the whitelist must never be read as a complete edge list, and it must not name an edge the code does not have. The downward edges the code has today are recorded in the import inventory tracked by the architecture-check issue; that inventory is current state, not part of this rule, and it changes without changing this section.

| Layer | Domains | Responsibility | Must not contain |
| --- | --- | --- | --- |
| L0 private base | `_result`, `_validation`, `_numerics`, `_optional` | `Result` type, input validation, generic numeric helpers | Any physics term |
| L1 maths and numerics | `numerics`, `fvm`, `io` | Interpolation, bases, differences, fitting, linear algebra, finite volume, file formats | Plasma physics quantities |
| L2 local physics relations | `physics`, `collisions`, `fusion`, `dielectric`, `plasma` | Pointwise quantities: scales, Coulomb logarithms, cross sections, rates, dielectric tensors | Field distributions, transport solves |
| L3 geometry and fields | `geometry`, `electromagnetism`, `field`, `configurations` | Flux surfaces, field lines, grid maps, vacuum fields, coils, device data | Kinetic theory or transport |
| L4 physical subsystems | `kinetic`, `neutrals`, `mirror`, `neoclassical`, `closures`, `source` | One physical phenomenon together with its own models | Cross-subsystem coupled iteration |
| L5 coupling and inversion | `equilibrium`, `diagnostics`, `inference` | Cross-subsystem composition, residuals, parameter estimation | Anything a lower layer references |

Same-layer dependencies are allowed only from this whitelist:

| Layer | Allowed same-layer dependency |
| --- | --- |
| L3 | `field → electromagnetism`, `configurations → electromagnetism`, `electromagnetism → geometry` |
| L4 | `mirror → closures` |
| L5 | `equilibrium → diagnostics`, `inference → diagnostics` |

Root-level private modules are not domains and carry no domain API. The current inventory, with what actually uses it:

| Module | Used by | Role |
| --- | --- | --- |
| `_result` | all domains | `Result` mapping type |
| `_numerics` | `closures`, `mirror`, `equilibrium`, `field`, `diagnostics`, `inference` | generic numeric kernels |
| `_validation` | three domains | input validation |
| `_anisotropic_numerics` | `closures`, `equilibrium` | shared anisotropic discretisation kernels |
| `_composition` | `equilibrium`, `mirror` — inside function bodies only | private composition helper |
| `_hold` | nothing | placeholder, not an in-use base |
| `_optional` | nothing | placeholder, not an in-use base |

A domain may import only from that list, and a module that nothing imports is not thereby a base to build on. The architecture check states the rule that makes this auditable: the set of root private modules imported by domains is a subset of this table, holding both for module-level imports and for imports inside function bodies. Private code that belongs to a domain lives in `<domain>/_*.py`. Cross-domain use refers only to public names from the other domain's `__all__`, never to its private modules.

The one upward root dependency is the composition layer, `_framework_compositions/`: a package that wires public `equilibrium` and `mirror` names (currently the kinetic mirror-Hall equilibrium) with module-level imports. It is allowed to depend on L4/L5 because it only assembles public functions, and no domain may import it back. It is scheduled for dissolution into the highest domain it composes, after which this row disappears.

Architecture tests enforce dependency direction, the same-layer whitelist, cycles and the allowed root-private module list, including imports inside functions. Those checks do not by themselves establish physical ownership or every public/private symbol boundary; reviewers still check those requirements. Derive actual edges from code rather than restoring already-removed cycles or never-existing edges to match an old plan.

## Model families

A model family is one physical relation computed by several models or fits — for example several charge-exchange cross-section fits, or cold, thermal and generalized dispersion relations for one wave class. It is the SciRel form of OpenFOAM's runtime-selectable models.

| Rule | Detail |
| --- | --- |
| One entry per family | Select the model with a closed `method=` keyword, as in `scipy.optimize.minimize`. The default is stated in the contract with its reason; prefer the newer, better supported fit |
| Same physical inputs | Members use the same physical parameter names, units and axis order. A model-specific *numeric* control (truncation order, tolerance, iteration cap) may exist, but passing it to a model that does not use it raises `TypeError` naming the parameter, the violated condition, the legal values and the contract ID |
| Same Result keys | Members return the same common scientific keys, including inside nested results. Only method-specific algorithm records explicitly enumerated in the contract may differ or be absent; no `None`/`nan` placeholders stand in for an unavailable scientific quantity. Raw partial diagnostics require a separate diagnostic callable and contract. A single returned quantity is returned directly, without method or order metadata |
| Range per model | Each `method` declares its own applicability, and out-of-range behaviour follows "Returns and errors" |
| Ownership | Approved membership is recorded once in the callable's contract `family` field. One public callable has one contract; its named `methods` retain each fit's range, failures and evidence. The family index is generated from contracts and never committed |

The `family` object contains `name`, `default`, `default_reason` and a nonempty
`methods` list. Each method has `name`, `model`, `numerical_controls`,
`applicability`, `failure_semantics` and `verification`. Common physical ports
remain at the contract top level; methods do not define a second signature or
silently substitute a different physical quantity. The explicit keyword-only
`method` input, declared signature and live callable have the same default.

Numerical controls name existing optional parameters; their method-specific
settings carry a `default` and `constraints`. Passing a value to a method that
does not implement that control is rejected, rather than ignored. Each method's
tests must be covered by the existing top-level test scope, and the executable
contract example explicitly calls every declared method. A whole-file test scope
already covers its node selectors; do not add the file and the same nodes twice
to the pytest command. Runtime test identities still establish what ran, not
mere file registration.

The Chinese reader preserves method names, order and defaults and translates
their descriptions, ranges, failures and evidence limits. Discovery and pages
derive that information from the one contract. Do not create one contract per
method that all bind to the same default call. An approved migration may reduce
contract count while retaining every original method; record each original
contract's destination in its migration issue.

Do not merge functions that answer different questions. When the physical inputs differ — one takes a temperature, the other a full distribution function — keep two functions and cross-reference them in See Also. Never introduce a physical parameter that only some models use just to fit a family. The frozen family table for the current migration is the one recorded in issue #154.

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
- Invalid input raises `ValueError`, or `TypeError` for a wrong kind, and an unrepresentable result raises `FloatingPointError`.
- Every rejection message states five things: the parameter name; the condition violated (finite, positive, shape `(n_r, n_z)`, unit eV); what was actually received (shape, dtype, range, or the number of offending elements — never the whole array); what is legal (all closed options, or the numeric bounds); and the contract asset ID to read next.
- When a result would be wrong with no visible sign, raise. When it stays meaningful but less accurate, warn with `scirel.ApplicabilityWarning`, a `UserWarning` subclass, so callers can promote it with `warnings.filterwarnings("error", category=...)`. The warning states the quantity, the legal range, the value received, the effect on the result, and the contract asset ID. Silent clipping and silent extrapolation are never allowed.
- If a value can be supplied two ways, require exactly one.
- A solver's non-convergence result carries `success`, `status` and `message` on the `OptimizeResult` pattern, and never looks converged. Whether it raises or returns that state is fixed by the contract's `failure_semantics.nonconvergence`.
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

`check_contract_sync.py` enforces the derived columns for every public asset in
`catalog/examples/`; asset-specific stale-phrase rules do not select the checked set.

A contract ID `scirel.<domain>.<name>` must name the domain whose module defines the function: the `<domain>` segment equals the canonical module's domain. Apply this requirement to every migration and update its callers and derived records together. Candidate-package checks do not establish that all existing catalog IDs have already migrated; whole-catalog alignment remains part of the foundation closeout.

## Deprecation

Nothing is published to PyPI yet; SciRel is used internally or delivered as a built-in capability, so the pre-release rule applies.

Before the first public release, rename directly and update every caller, with no alias. After it, keep an old name for at least two minor releases, emit `DeprecationWarning` naming the replacement, and record it in the release notes. Do not change the meaning of an existing name or parameter in place.

## Migration status

Open work is tracked in GitHub issues with the `agent-task` label. Each change keeps `scirel-acceptance` green.
