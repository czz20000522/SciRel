# Language Profiles

D1 implements source-shaped scientific callables in Python or C. Other source languages may be inspected and
executed for comparison; emitting another implementation language needs an explicit project decision.
Formal `operator.md` is not part of the required D1 file set. Scientific meaning belongs in code/docstrings,
comments, YAML or existing anchors, with exact source and evidence locators.

## Select the implementation

Use Python for inspectable reference implementations and installed NumPy/SciPy numerical dependencies. Use C
for a bounded numerical kernel with explicit scalar/array/struct ports and a justified native consumer or source
fidelity need. Do not select C if conversion would invent missing coefficients, closures, units or boundary rules.
For either profile, prove source-language array layout, index base, precision and branch/boundary semantics.

## Python profile

```text
<operator_name>/
  scientific_operator.py
  test_scientific_operator.py
```

Run the actual tests, for example `python -m pytest test_scientific_operator.py -q`. Declare runtime dependencies
and any source/fixture environment variables in existing runtime or test evidence, not a duplicated page.
Candidate execution stays source-free; source comparison may access the declared source runtime separately.

## C profile

```text
<operator_name>/
  scientific_operator.h
  scientific_operator.c
  test_scientific_operator.c
```

Compile and execute the test; compilation alone proves no numerical claim. Use ISO C and `math.h` where
sufficient. Declare BLAS/LAPACK, compiler extensions, OpenMP or platform flags when actually required.
Public declarations stay in the header. Arrays have explicit lengths, dimensions, layout/strides and ownership;
failures use status codes or structured outputs, not silent global mutation. Build products remain outside the
frozen source package or are removed after their last authorized consumer.

## Attributable test evidence

Each scientific claim needs the exact code/source identity, command, relevant runtime versions, explicit input,
oracle/comparison basis, complete observed outputs, numerical metrics, predeclared tolerances and actual result.
These facts may live in test comments or an existing bound execution record. Reference them rather than
requiring a particular Chinese header, label order or comment before every test. Keep local absolute paths in
run evidence and use relocatable source locators for shared contracts.

`direct_source_runnable` means the test actually ran/imported/compiled the source and compared candidate values.
For a runnable subdomain, state its limits; a repaired source-defect domain needs separate independent validation.
An unavailable comparison is a named evidence gap, not a formatting excuse or an invented successful run.
