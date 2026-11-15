# Exact zero-b response and ordinary-result failures (#302)

This corrects a removable numerical endpoint and migrates the explicit error
channel. It does not change the nonzero-b Taylor/asymptotic/quadrature formulas,
their coefficients, branch tests or stopping thresholds, nor the J8 pole table,
tensor arithmetic or solver trajectory. The old internal IEEE continuation was
deliberate source parity; it was not evidence that a NaN was a physical answer.

## Independent mathematical definition

Use the harmonic definitions in Xie (2025), arXiv:2502.06550v2,
Eq.(13)/(14), also recorded in [README.md](README.md). With
Gamma_n(b)=exp(-b) I_n(b), Gamma_1=Gamma_-1=b/2+O(b²), and
Gamma_n=O(b^|n|), taking the exact b=0 limit gives

```text
R = H = 1/2 [1/(x-1) + 1/(x+1)] = x/(x²-1)
H = d(b R)/db, not dR/db
RC = [[R,H], [x*dR/dx,x*dH/dx]]
x*dR/dx = x*dH/dx = -x*(x²+1)/(x²-1)²
```

The poles x=+/-1 are genuine. Every other finite real or complex x has a
finite exact rational value. At x=0 the complete matrix is zero; at x=+/-2
the value is finite, but the old Taylor recurrence evaluated a *subsequent
zero coefficient* through b/(x²-4)=0/0. That operation is unnecessary in
the exact constant term. A very close complex pole can have representable R
and an overflowing scaled derivative: the contract requires **all** of RC,
so returning just R is insufficient.

## Production arithmetic and independent oracle

Only exact b=0 uses standard-library rational real and imaginary components.
For u=1/(x-1), v=1/(x+1), compute R=(u+v)/2 and the second row
as -(u+u²+v-v²)/2, rounding components to binary64 only on output. This
avoids both overflowing x² for very large finite x and cancellation of weak
components next to a complex pole. The existing Taylor branch label is kept.
Nonzero b does not take this path.

The direct test in `tests/kinetic/test_ronnmark_zero_endpoint.py` uses a
different algebraic expression: mpmath at 800 decimal digits evaluates
x/(x²-1) and -x*(x²+1)/(x²-1)² after exact rational conversion of each
binary64 input component. The expression is evaluated independently of the
product helper. Precision retains the O(delta²) contribution for
x=1+i*1e-154; rounding x² in binary64 alone would lose it.

The comparison was frozen **before repair outputs**: for each real and
imaginary component separately,

```text
abs(output-reference) <= 16*binary64_epsilon*abs(reference)
                         + 8*minimum_positive_binary64_subnormal
```

This is an endpoint arithmetic budget, not a global response error bound.
It does not replace the original twelve-point R/H budgets or the sixteen
tensor sample budgets. Cases include signed/complex zero, removable +/-2,
adjacent binary64 values next to +/-1, extreme real/complex magnitudes,
subnormals and weak components near a complex pole.

## First red, repair and downstream controls

The original frozen eight-call probe retains its **3 PASS / 5 FAIL** and
exit 1. The added 122 direct tests on the unchanged product first reported
**64 failed / 58 passed**, exit 1. These are retained historical results,
not relabeled as passing because of a later repair. Their run identities and
logs are in the issue/PR receipt, not a private-path runtime dependency.

Additional tests check genuine poles and unrepresentable RC companions,
nonzero-b nonfinite results, complete J8 tensor failure, derived-scale
overflow/underflow, frequency-conversion overflow, and unchanged caller-input
ValueError. The manufactured SI case q=m=B=n=T=1 and omega=2,
kx=kz=0 **must compute a finite tensor**; it must not be rejected to hide
the removable endpoint. Omega=1 is the genuinely singular control. These
manufactured inputs isolate an algebraic relation, not a device-use claim.

The original finite root regression remains unchanged, including its
negative real/imaginary root, original 1e-9 budget, exit flag 0 and
converged=False. Before the repair, a read-only callback trace found all
101 K/D/determinant evaluations finite. The ordinary solver path therefore
does not need to accept NaN trials to retain that finite, unconverged result.

Invalid inputs remain caller errors. Required scales, complete R/H/RC,
K/D and the determinant must be finite; derived positive/nonzero scales
that underflow to zero fail explicitly. Numerical failures raise
FloatingPointError and propagate through roots and scans without a partial
result, fallback model or fabricated successful state. This is still not a
global J8 physics certificate or an accuracy claim about roots or damping.
