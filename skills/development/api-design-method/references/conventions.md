# Conventions

Choose a mature library in your field as the reference, and follow it unless you have a written reason not to. For scientific Python that library is SciPy, and the points below follow its practice. They apply to most Python libraries.

## Namespaces and privacy

- Users import from documented subpackages. The root stays small.
- Each public namespace declares `__all__`, and that list is the public API. Implementation lives in modules with a leading underscore or is simply absent from `__all__`.
- Exactly one public name per capability. Move helpers out of sight rather than documenting them as internal.
- Heavy imports stay lazy if import time matters, but the public list stays explicit and statically readable.

## Signatures

- Every parameter is named in the signature. Avoid a parameter mapping and avoid `**kwargs`.
- Required inputs come first and may be positional. Options, tolerances and method choices are keyword-only with stated defaults.
- Inputs with no safe default have no default. Make the caller choose a physical or business value.
- Choose among behaviours with a descriptive string, not an integer code or a boolean pair.
- Use one name for one concept across the library, and the same parameter order for similar functions.

## Failing loudly at the entrance

- Validate at the public boundary, and name the parameter and the requirement in the message.
- Raise `ValueError` for a bad value, `TypeError` for a wrong kind, and a specific subclass when callers may want to catch it.
- Reject what you cannot honour. If a file field or an option would be ignored, raise an error rather than ignoring it.
- Report numerical failure as failure. Use a warning only if the result is still meaningful, and say what it means.
- If two ways to supply a value exist, require exactly one and raise on both or neither.

## Units and conventions in the documentation

- State the unit in each parameter and return entry, in one fixed notation that a script can check, such as `[m]`. Mark dimensionless values too.
- State the sign, normalisation, axis order and coordinate origin wherever they could differ.
- Where a quantity has several common conventions, name the one used and how to convert from the others.
- Give the exact formula, or cite the equation, for anything with variants.

## Docstrings

Use the full numpydoc layout:

| Section | Requirement |
| --- | --- |
| Summary | One line saying what it does |
| Parameters | Every parameter: type, unit, shape, meaning, default behaviour |
| Returns | Every returned item, with the same detail |
| Raises | Each exception and what triggers it |
| See Also | Related functions, and when to use each |
| Notes | Formula, assumptions and limits |
| References | Sources for formulas |
| Examples | Short and runnable as a doctest; show typical use and the result |

Bring existing code up to this standard as you touch it. New code meets it from the start.

## Return values

- One function returns one shape, on every branch.
- Several results come back as a named result object rather than a bare tuple or plain dictionary. SciPy's `OptimizeResult` is a good pattern: a dictionary subclass with attribute access, a useful `repr`, and documented fields. It keeps existing dictionary callers working.
- Report status in documented fields, such as `success` and `message`, never by altering the data.

## Deprecation

- Before a first public release there is nothing to protect: rename directly and update every caller, leaving no alias.
- After release, follow a fixed policy: keep the old name working for at least two minor releases, emit `DeprecationWarning` with the replacement named, record it in the release notes, then remove it.
- Never change the meaning of an existing name or parameter in place. Add a new name or a required keyword instead, so that old calls fail or warn rather than silently change.

## Code style

- Use a formatter and a linter with a shared configuration, and accept their output.
- One statement per line. Name intermediate quantities after what they are.
- Keep formatting commits separate from behaviour commits.
