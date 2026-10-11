# Stored-energy accumulation correction

The declared discrete relation is W = (3/2) sum(p vpr drho_norm), independently for the three pressure inputs. Signed finite pressures are accepted algebraically; physical stored energy requires nonnegative thermal pressures.

The initial implementation accumulated longdouble products. For unit weights, [1e30, 1, -1e30] returned zero instead of 1.5 joules, while changing the order could return 1.5. This violates the same signed finite contract even though ordinary positive-profile tests passed.

The successor keeps input conversion, units, shapes, independent total-pressure semantics and failure conditions. It represents converted binary64 values as exact dyadic rationals, multiplies and sums exactly, and rounds only each final energy. An exact magnitude above float64 maximum or a nonzero result rounded to zero still raises FloatingPointError. This also avoids losing products before later cancellation. It is a numerical accumulation correction; no physical formula changes.

Regressions cover all six orders of the counterexample, intermediate products beyond the float64 range, subnormal products whose sum is representable, and original final overflow/underflow failures. Original profile tests and tolerances are retained. Independent evidence and exact package identity are kept in the versioned reception record. Other TORAX scientific families and physical calibration remain outside this narrow result.
