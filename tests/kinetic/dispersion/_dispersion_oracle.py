"""Independent SI velocity-integral oracles; no source assembly imports.

Time/space convention follows supplied PDF K=I-sigma/(i*omega*epsilon0).
Gauss-Hermite uses x=(v_parallel-vd)/vtz; Laguerre uses u=v_perp**2/vtp**2.
Both weights integrate normalized Maxwellians, so cylindrical 2*pi*vperp measure
is already included. Loss-cone components have their own vtp and signed weights.
"""

import numpy as np
from scipy.special import roots_hermite, roots_laguerre, jv, wofz

C = 2.9979e8
EPS0 = 8.8542e-12
QE = 1.6022e-19
MP = 1.6726e-27
KB = 1.3807e-23
MU0 = 1 / (C * C * EPS0)


def physical(deck, B0):
    d = np.asarray(deck, dtype=float)
    if d.ndim != 2 or d.shape[1] != 8 or not np.isfinite(d).all():
        raise ValueError("deck shape/finite")
    q, m, n, tz, tp, alpha, delta, drift = d.T
    if (
        np.any(m <= 0)
        | np.any(n <= 0)
        | np.any(tz <= 0)
        | np.any(tp <= 0)
        | np.any(q == 0)
        | np.any(alpha <= 0)
        | np.any(alpha > 1)
        | np.any(delta < 0)
        | np.any(delta > 1)
        or B0 == 0
    ):
        raise ValueError("contracted physical domain")
    if np.any((alpha == 1) & (delta != 1)):
        raise ValueError("alpha1 Delta!=1 source bypass not qualified losscone limit")
    q = q * QE
    m = m * MP
    vtz = np.sqrt(2 * tz * QE / m)
    vtp = np.sqrt(2 * tp * QE / m)
    weights = np.empty((2, len(m)))
    for s, (a, de) in enumerate(zip(alpha, delta)):
        weights[:, s] = [1, 0] if a == 1 else [(1 - a * de) / (1 - a), a * (de - 1) / (1 - a)]
    return dict(
        q=q,
        m=m,
        n=n,
        tz=tz * QE / KB,
        tp=tp * QE / KB,
        vtz=vtz,
        vtp=vtp,
        alpha=alpha,
        delta=delta,
        vd=drift * C,
        gyro=B0 * q / m,
        wp2=n * q * q / (m * EPS0),
        kd2=n * q * q / (EPS0 * tz * QE),
        weights=weights,
        cwp=C / np.sqrt(n[0] * q[0] ** 2 / (m[0] * EPS0)),
    )


def coordinates(par, pa, pb, ipa, ipb, iloga, ilogb, cwp, row, column):
    p = np.asarray(par, dtype=float).reshape(6).copy()
    p[ipa - 1] = pa[row - 1] if not iloga else 10.0 ** pa[row - 1]
    if ipa != ipb:
        p[ipb - 1] = pb[column - 1] if not ilogb else 10.0 ** pb[column - 1]
    k = abs(p[0]) / cwp
    theta = np.deg2rad(p[1])
    kx, kz = (
        (p[3] / cwp, p[2] / cwp) if ipa > 2 and ipb > 2 else (k * np.sin(theta), k * np.cos(theta))
    )
    return dict(par=p, kx=kx, kz=kz, k=np.hypot(kx, kz), theta=np.degrees(np.arctan2(kx, kz)))


def response(deck, B0, kx, kz, omega, N, order):
    """EM Eq11/12/13/16 and ES Eq43 evaluated by independent integrals.

    EM uses literal ordinary J_n/J'_n, never scaled I_n/BesselGamma, source
    residues or candidate matrix. ES integrates J_n**2 perpendicular and the
    velocity numerator (kz*(v-vd)+lambda*n*Omega)/(omega-kz*v-n*Omega).
    It is the finite-harmonic moment form of Eq42/43, with normalization constants
    retained per harmonic; its infinite-N limit agrees longitudinal kinetic K.
    """
    if (
        not np.isfinite([kx, kz, omega.real, omega.imag]).all()
        or omega.imag <= 0
        or kz == 0
        or kx == 0
    ):
        raise ValueError("oblique real nonzero-k upper-omega-plane oracle domain")
    p = physical(deck, B0)
    x, wh = roots_hermite(order)
    u, wl = roots_laguerre(order)
    weight = wl[:, None] * wh[None, :] / np.sqrt(np.pi)
    chi = np.zeros((3, 3), complex)
    es = 1.0 + 0j
    k2 = kx * kx + kz * kz
    for s in range(len(p["q"])):
        vz = p["vd"][s] + p["vtz"][s] * x
        for branch in range(2):
            r = p["weights"][branch, s]
            if r == 0:
                continue
            vtp = p["vtp"][s] * np.sqrt(1 if branch == 0 else p["alpha"][s])
            vp = vtp * np.sqrt(u)
            lam = p["vtz"][s] ** 2 / vtp**2
            for n in range(-N, N + 1):
                arg = kx * vp / p["gyro"][s]
                jn = jv(n, arg)
                jnp = (jv(n - 1, arg) - jv(n + 1, arg)) / 2
                a = n * p["gyro"][s] / kx * jn
                bb = vp * jnp
                cc = jn[:, None] * vz[None, :]
                den = omega - kz * vz[None, :] - n * p["gyro"][s]
                fac = (
                    -2 * weight * (n * p["gyro"][s] / vtp**2 + kz * x[None, :] / p["vtz"][s]) / den
                )

                def integral(v):
                    return np.sum(fac * v)

                P = np.array(
                    [
                        [
                            integral(a[:, None] ** 2),
                            integral(1j * a[:, None] * bb[:, None]),
                            integral(a[:, None] * cc),
                        ],
                        [
                            integral(-1j * a[:, None] * bb[:, None]),
                            integral(bb[:, None] ** 2),
                            integral(-1j * bb[:, None] * cc),
                        ],
                        [
                            integral(a[:, None] * cc),
                            integral(1j * bb[:, None] * cc),
                            integral(cc * cc),
                        ],
                    ]
                )
                chi += p["wp2"][s] / omega**2 * r * P
                gamma = np.dot(wl, jn * jn)
                moment = np.dot(
                    wh / np.sqrt(np.pi),
                    (kz * p["vtz"][s] * x + lam * n * p["gyro"][s])
                    / (omega - kz * vz - n * p["gyro"][s]),
                )
                es -= p["kd2"][s] / k2 * r * gamma * moment
    K = np.eye(3) * (1 - p["wp2"].sum() / omega**2) + chi
    return K, es


def parallel_es(deck, B0, kz, omega, order):
    """Exact kx=0/n0 ES1D velocity integral; no small-kx substitution."""
    p = physical(deck, B0)
    x, w = roots_hermite(order)
    out = 1.0 + 0j
    for s in range(len(p["q"])):
        vz = p["vd"][s] + p["vtz"][s] * x
        out -= (
            p["kd2"][s]
            / kz**2
            * np.dot(w / np.sqrt(np.pi), kz * p["vtz"][s] * x / (omega - kz * vz))
        )
    return out


def plasma_z(z):
    return 1j * np.sqrt(np.pi) * wofz(z)


def em_schur(M, omega):
    """Read public matrix partition only, not production coefficient assembly.

    Aux state a: omega*a=A*a+C*E. E row: omega*E=G*a+F*B.
    Q=G(omega I-A)^-1 C and K=I-Q/omega. Check diagonal aux structure
    before using diagonal inversion. Maxwell blocks are returned separately.
    """
    from scipy import sparse

    if sparse.issparse(M):
        M = M.toarray()
    M = np.asarray(M)
    na = M.shape[0] - 6
    if M.ndim != 2 or M.shape[0] != M.shape[1] or na <= 0:
        raise ValueError("EM shape")
    A = M[:na, :na]
    diag = np.diag(A)
    if not np.array_equal(A, np.diag(diag)):
        raise ValueError("unexpected coupled aux block")
    if not np.isfinite(M).all() or np.any(omega == diag):
        raise ValueError("nonfinite/singular matrix")
    Q = M[na : na + 3, :na] @ ((M[:na, na : na + 3]) / (omega - diag)[:, None])
    if np.any(M[:na, na + 3 :] != 0) or np.any(M[na : na + 3, na : na + 3] != 0):
        raise ValueError("unexpected field block")
    return (
        np.eye(3) - Q / omega,
        M[na : na + 3, na + 3 :],
        M[na + 3 :, na : na + 3],
        M[na + 3 :, na + 3 :],
    )


def es_schur(M, omega):
    from scipy import sparse

    if sparse.issparse(M):
        M = M.toarray()
    M = np.asarray(M)
    A = M[:-1, :-1]
    diag = np.diag(A)
    if not np.array_equal(A, np.diag(diag)) or not np.isfinite(M).all():
        raise ValueError("ES aux/finite")
    return 1 - (M[-1, :-1] @ (M[:-1, -1] / (omega - diag)) + M[-1, -1]) / omega


def error(a, b):
    """Dimensionless component and Frobenius metrics; natural zero scale one."""
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("shape/nonfinite")
    diff = abs(a - b)
    return dict(
        component=float(np.max(diff / np.maximum(1.0, abs(b)))),
        relative=float(np.linalg.norm(a - b) / max(1.0, np.linalg.norm(b))),
        max_abs=float(np.max(diff)),
    )


def field_oracle(E, B):
    E = np.asarray(E, dtype=complex)
    B = np.asarray(B, dtype=complex)
    if E.shape != (3,) or B.shape != (3,) or not np.isfinite(E).all() or not np.isfinite(B).all():
        raise ValueError("finite3vectors required")
    norm = np.linalg.norm(E)
    if norm == 0:
        raise ValueError("zeroelectricnorm")
    pivot = int(np.argmax(abs(E)))  # first index wins exact ties
    factor = np.exp(-1j * np.angle(E[pivot])) / norm
    en = E * factor
    bn = B * factor
    return en, bn, EPS0 * np.vdot(en, en).real / 2, np.vdot(bn, bn).real / (2 * MU0)
