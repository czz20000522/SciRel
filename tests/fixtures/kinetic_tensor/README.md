# Independent tensor references for sixteen fixed inputs

These data separate two mathematical objects: **A**, the Maxwellian response
with the entire causal Z function, and **B**, Eq.(8) with the exact current
binary64 J=8 table and independently summed R/H. Neither product outputs nor
product kernels generated these references. The Python files here are our
independent mathematical implementations, not copies of an upstream solver.
Pytest reads the saved data; it never imports these research generators.

## Data and preserved history

- `inputs.json`: sixteen inputs, constants, hexadecimal and exact rational
  binary64 identities. All numeric inputs first become binary64, then enter
  each high-precision context exactly; do not parse their decimal spellings as
  infinitely precise physical constants. Constants are
  `KB=1.38064852e-23`, `eps0=8.854187817e-12`, `C=299792458`.
- `reference.json`: full complex K, D, detK and detD, as 160 significant-digit
  decimal string pairs `[real, imaginary]`. Original A retains all sixteen
  selected 160-dps values, including the blocked one. New A observations select
  the separate 280-dps small-kz successor; the other fifteen remain original.
  B selects 160 dps. Nonzero kx uses N128; kx=0 uses analytic endpoints.
- `convergence.json`: original A **15/16, REFERENCE_BLOCK, process exit 2**;
  independently frozen small-kz successor, four evaluations, all converged;
  B **16/16**. The original A small-kz precision differences were about
  `1.52040398038e-58`, exceeding the unchanged `1e-70` criterion. The successor
  maximum comparison was about `3.51851327069e-158`. It did not rerun or relabel
  the original study. Original A/B each used sixty variants: fourteen cases
  at 100/160 dps times N96/128, plus two analytic endpoints at 100/160 dps.
  The successor used only small-kz at 200/280 dps times N96/128.
- `poles.json`: literal rows, exact binary64 identities and exact rational
  moments M0 through M3. No normalization, ideal-moment substitution or repair.
- `zero_kz_responses.json`: selected B R/H and species scales for checking the
  endpoint with the actual moments, including its nonzero cross-z residuals.

Saved precision/cutoff comparisons establish observed convergence at these
points, not complete 160-digit accuracy, a continuous-domain bound or total
arithmetic-error enclosure. `reproduction.json` binds original input artifacts
by digest without requiring their private locations or availability.

## Public scientific definitions

Primary source: H. S. Xie, *Phys. Plasmas* **32**, 082110 (2025),
[arXiv:2502.06550v2](https://arxiv.org/html/2502.06550v2), Eq.(3), its X matrix,
and Eq.(8), (13), (14). The arXiv revision is August 12, 2025. Additional method
sources: K. Rönnmark, *WHAMP*, KGI Report 179 (June 1982), printed pp.10–13,
17; K. Rönnmark, *Plasma Physics* **25**, 699 (1983),
[DOI 10.1088/0032-1028/25/6/007](https://doi.org/10.1088/0032-1028/25/6/007).
The 1983 full text was not obtained; it supplies no extra accuracy guarantee.

The definitions below specify the reference, including the independently
derived signed-kz convention and analytic endpoints. Assume homogeneous,
linear, collisionless, nonrelativistic, isotropic, drift-free Maxwellians,
time dependence `exp(-i omega t)`, real nonzero omega, real kz, and finite
possibly complex kx. For each species define

```text
vt = sqrt(2 KB T/m), Omega = q B/m, wp2 = n q²/(eps0 m)
a = kx sqrt(KB T/m)/Omega, b = a², alpha = wp2/omega²
h = |kz| vt, eta = sign(kz), z0 = omega/h, zn = (omega-n Omega)/h
Gamma_n(b) = exp(-b) I_n(b)
Gamma'_n = (Gamma_(n-1)+Gamma_(n+1))/2 - Gamma_n
Z(z) = i sqrt(pi) exp(-z²) erfc(-i z)
```

T is kelvin; kx/kz are phase wavenumbers in 1/m. Omega and a retain signs.
All squares are ordinary complex squares. For h>0, Eq.(3) is

```text
K_A = I + sum_species alpha [z0 sum_n Z(zn) X_n + 2 z0² ez ez^T]
X_n = [[n² Gamma/b, i n Gamma', eta sqrt(2) zn n Gamma/a],
       [-i n Gamma', n² Gamma/b-2b Gamma', -i eta sqrt(2) zn a Gamma'],
       [eta sqrt(2) zn n Gamma/a, i eta sqrt(2) zn a Gamma', 2 zn² Gamma]]
```

The sum denotes the infinite mathematical response; N96/N128 are its
independently checked approximants. For kz<0 evaluate with h>0 then reflect
xz/yz/zx/zy after assembling all species. This follows the causal parallel
integral under `vz -> eta vz`. Do not feed signed h into the same Z expression.

At kz=0 fix nonresonant omega before taking the limit. Write x=omega/Omega,
P=wp2/(omega Omega). The infinite R/H definitions, Eq.(13)/(14), are

```text
R(x,b) = sum_n n² Gamma_n(b)/(b (x-n))
H(x,b) = d[b R(x,b)]/db = sum_n n² Gamma'_n(b)/(x-n)
       = x² sum_n Gamma'_n(b)/(x-n)
R(x,b) = -x/b + (x²/b) sum_n Gamma_n(b)/(x-n)
```

The last forms require the infinite identities sum Gamma=1 and sum Gamma'=0.
Our direct finite R/H sums preserve the residuals of those identities. For
kz=0, A has species response

```text
chi_A = [[-P R, -i P H/x, 0],
         [i P H/x, -P (R-2b H/x²), 0],
         [0, 0, -P (x+b R)/x²]]
```

At kx=0, kz!=0, use Gamma0=1 and Gamma±1=b/2+O(b²) before dividing:
`chi_xx=chi_yy=alpha z0 [Z(z1)+Z(z-1)]/2`,
`chi_xy=i alpha z0 [Z(z1)-Z(z-1)]/2`, cross-z zero,
`chi_zz=2 alpha z0² [1+z0 Z(z0)]`.
At both zero, `R=H=x/(x²-1)` and A is the cold Lorentz result:
`chi_xx=chi_yy=-wp2/(omega²-Omega²)`,
`chi_xy=-i wp2 Omega/[omega(omega²-Omega²)]`, `chi_zz=-wp2/omega²`.
The independent linear solve uses
`(-i omega I - [[0,Omega,0],[-Omega,0,0],[0,0,0]]) v=(q/m)E`.
This fixes the Hall sign without a pole fit.

For B, let `xj=(omega-h cj)/Omega`, `P=wp2/(omega Omega)`, with the actual
table's beta/c values. Eq.(8) defines the species response

```text
chi_B = P sum_j beta_j *
[[Rj, i Hj/xj, eta sqrt(2) a cj Rj/xj],
 [-i Hj/xj, Rj-2b Hj/xj², -i eta sqrt(2) a cj Hj/xj²],
 [eta sqrt(2) a cj Rj/xj, i eta sqrt(2) a cj Hj/xj²,
  2 cj² (xj+b Rj)/xj²]]
```

At b=0, use `Rj=Hj=xj/(xj²-1)`, including both-zero B. Do not switch B to A's
cold endpoint. At kz=0 use the positive-side convention eta=+1 and the actual
moments `Ml=sum beta_j cj^l`. Their exact binary64 values do not equal ideal
`M0=-1, M1=0, M2=-1/2`. In particular delta0≈−1.56125112838e−15,
M1≈+i 5.08977394236e−16, delta2≈−6.49852243407e−15. Thus B retains
`chi_xz=P sqrt(2) a M1 R/x` and `chi_yz=-i P sqrt(2) a M1 H/x²`.

Inserting ZJ directly into Eq.(3), **B_direct**, is a different object. Exact
polynomial division with the infinite Gamma identities gives

```text
(B_direct-B)_zz = 2 wp2 (1+M0)/h² + 2 wp2 M1/(omega h).
```

This explains why repairing moments or replacing B by B_direct invalidates
the intended diagnostic. The current coefficient texts have an identified
appearance in the author's source linked by the 2025 paper; their original
generation constraints, difference from the published 1982/2016 table and
global approximation accuracy remain UNKNOWN. No upstream code is vendored.

Both references add I once across species. For `n=(c kx/omega,0,c kz/omega)`,
`D=K+nn^T-(nx²+nz²)I`; all K/D entries and general complex determinants are
retained. Transpose relations are `Kyx=-Kxy`, `Kzx=Kxz`, `Kzy=-Kyz`, not
Hermitian relations.

## Reproduction and numerical/physical scope

Manual independent reproduction from the repository root:

```sh
python3 scripts/dev.py run python -B tests/fixtures/kinetic_tensor/reproduce.py --output .runtime/tensor-reference-reproduction
python3 scripts/dev.py run python -B tests/fixtures/kinetic_tensor/reproduce.py --observe --output .runtime/tensor-model-observation
```

Each command requires a new output directory. The first freezes tracked input
digests before evaluation and regenerates the original sixty A and sixty B
variants and four successor variants, with the original precision/N checks
and `1e-70` criterion. It retains raw data, observed comparisons and comparison
against stored values; expected exit **2** preserves A's historical BLOCK.
It is not a default test or product test. The second recomputes per-component
B-A real/imaginary, absolute, and `abs(B-A)/max(1,abs(A))` differences from
saved independent values, with **no acceptable-error threshold**. detK is
auxiliary; product-return comparisons use only eighteen K/D entries and detD.

`test_product_matches_independent_B_16` uses the frozen new diagnostic
`abs(product-B)/max(1,abs(B)) <= 2e-7` at precisely these sixteen inputs. It
does not replace C/source `1e-11/1e-9`, F_N `2e-12`, R80/160 `1e-14`, or
the existing R/H `rtol=1e-7, atol=1e-9`. The latter direct R/H test also checks
that H means d(bR)/db, not dR/db; reuse its budget without broadening it.
The model difference B-A is measurable and is separate from arithmetic error.
There is no global physical-accuracy, weak-imaginary-part sign, mode/root,
damping, device applicability or release guarantee.

The separately reviewed omitted-harmonic inequalities concern **the exact
finite truncated matrix M_N** and an entrywise radius E for the difference
between the exact infinite response and M_N. Their determinant perturbation
bound is the sum over six permutations and seven nonempty subsets of the
three factors, choosing E on the subset and |M_N| elsewhere. A saved numerical
matrix used as a center only evaluates that formula at high precision; it
does not enclose total arithmetic error. Such a certificate would additionally
need a center-error radius and its propagation. At analytic kx=0 the omitted
tail is zero, but arithmetic error is not thereby zero.

Scientific identity and these boundaries received independent static review
(`ACK_STATIC`); this does not confer execution, integration or release approval
on a new candidate. Current-candidate execution belongs to its local test logs.
