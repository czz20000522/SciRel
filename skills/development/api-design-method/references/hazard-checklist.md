# Hazard checklist

A hazard is an interface that lets a careful caller get a wrong answer without being told. For each one, ask: **what would someone reasonably assume, and what happens if they are wrong?**

The checks are grouped by how the mistake happens. "Scan" marks what `scan_hazards.py` or `api_inventory.py` can point at. The rest needs reading.

## Hidden assumptions

- A function assumes a coordinate origin, grid order, axis order or sign convention that the signature does not show.
- A preset or constructor default stands in for a value the caller should choose, such as a current, a density or a size. A default of one that "works" is the classic case: the result is finite, plausible and wrong.
- A function requires sorted, uniform or positive input and does not check.
- Part of an input is ignored. A header field or option is read, or accepted, and has no effect.
- A file reader accepts only one dialect of a format while its name suggests the standard one.

## Silent behaviour (scan)

- Values are clipped, floored or zeroed. Non-finite values are replaced. Warnings or floating-point errors are turned off.
- A special case returns zero or an empty result, based on position in an array instead of on the actual value.
- Inputs are truncated or broadcast to fit. Extra arguments are dropped.
- A broad `except` turns any failure, including a programming error, into a status or a default.
- A solver that did not converge returns a result that looks like a converged one.
- A fallback method runs without saying so.

## Units and conventions

- The units of a parameter or result are not stated, or are stated only in prose elsewhere.
- Two functions measure the same quantity differently: per radian or total, keV or eV, a thermal speed with or without a factor of two, a normalised or physical value.
- A quantity is named for one convention and computed in another.
- A function's definition depends on a variant, and the docstring describes a different variant from the code.
- A formula's family has more than one common form, and the documentation does not give the exact one used.

A useful test: **write down the conversion a caller would need between this function and the most common alternative convention.** If that conversion cannot be read off from the docstring, the documentation is incomplete.

## Misleading names

- A name promises more than the code does: "solve" that takes one step, "read" that reads only a dialect, "average" whose weighting is unstated.
- A name describes the source it came from, not what it does.
- Similar names do different things, or different names do the same thing (scan).
- A public name is an implementation detail, or a private helper is imported from outside.

## Duplicate capability (scan)

- Two public functions compute the same thing, possibly with different conventions.
- One function's name appears in several modules with different meanings.
- A family has several entry points, and nothing says which to use.

## Unclear parameters (scan)

- A single mapping or `**kwargs` holds the real parameters, so the signature says nothing.
- A flag, or an integer selector, chooses between behaviours, and the values are not documented.
- A parameter may be `None`, and its meaning in that case is not stated.
- Several positional parameters of the same type are easily swapped.
- A parameter has a mutable default.
- A required physical input has a default.

## Return values

- The return type varies with the input or the branch.
- A function returns a bare tuple whose order must be remembered, or a mapping whose keys are undocumented.
- A result carries no units, or a diagnostic is mixed with data.

## Documentation

- The example does not run, or runs but no longer shows what the text says.
- Failure behaviour is not listed, so callers cannot tell a bad input from a bug.
- Nothing points to the related functions, so a caller cannot find the right one.
- The documentation contradicts itself between a summary, a parameter entry and a separate record.

## How to record a finding

One line each: the name, what a caller would assume, what really happens, the input that shows it, and the proposed fix. If you cannot name the input, mark it unconfirmed.
