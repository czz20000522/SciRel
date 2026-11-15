"""Independent Eq.(8), (13), (14) fixed-table model B; manual only."""

import itertools

import mpmath as mp


def number(v):
    # Convert inside the respective high-precision work context, not at module load.
    return mp.mpf(float(v))


def complex_input(v):
    return mp.mpc(number(v[0]), number(v[1]))


def scalar(v):
    v = mp.mpc(v)
    return {
        "re": mp.nstr(v.real, 160, strip_zeros=False),
        "im": mp.nstr(v.imag, 160, strip_zeros=False),
        "binary64": {
            "re": float(v.real),
            "im": float(v.imag),
            "re_hex": float(v.real).hex(),
            "im_hex": float(v.imag).hex(),
        },
    }


def parse(v):
    return mp.mpc(mp.mpf(v["re"]), mp.mpf(v["im"]))


def matrix_record(m):
    return [[scalar(m[r, c]) for c in range(3)] for r in range(3)]


def determinant_permutations(m):
    terms = []
    for p in itertools.permutations(range(3)):
        inversions = sum(p[i] > p[j] for i in range(3) for j in range(i + 1, 3))
        terms.append((-1) ** inversions * mp.fprod(m[i, p[i]] for i in range(3)))
    return mp.fsum(terms)


def prepare_species(case, species, constants, dps):
    kx, kz = complex_input(case["kx"]), number(case["kz"])
    omega, B = number(case["omega"]), number(case["B"])
    KB, eps = number(constants["KB"]), number(constants["eps0"])
    q, m, density, T = (number(species[k]) for k in ("charge", "mass", "density", "temperature"))
    thermal = mp.sqrt(2 * KB * T / m)
    Omega = q * B / m
    wp2 = density * q * q / (eps * m)
    a = kx * mp.sqrt(KB * T / m) / Omega
    b, P, h = a * a, wp2 / (omega * Omega), abs(kz) * thermal
    if b == 0:
        gamma = [mp.mpc(1)] + [mp.mpc(0)] * 129
    else:
        exponential = mp.exp(-b)
        gamma = [exponential * mp.besseli(n, b) for n in range(130)]
    gp = [(gamma[abs(n - 1)] + gamma[n + 1]) / 2 - gamma[n] for n in range(129)]
    return dict(
        thermal=thermal,
        Omega=Omega,
        wp2=wp2,
        a=a,
        b=b,
        P=P,
        h=h,
        gamma=gamma,
        gp=gp,
        omega=omega,
        computed_dps=dps,
    )


def gamma_identities(state, cutoff):
    N = 2 if cutoff is None else cutoff
    g, gp = state["gamma"], state["gp"]
    ns = range(-N, N + 1)
    actual = [
        mp.fsum(g[abs(n)] for n in ns),
        mp.fsum(n * g[abs(n)] for n in ns),
        mp.fsum(gp[abs(n)] for n in ns),
        mp.fsum(n * n * g[abs(n)] for n in ns),
        mp.fsum(n * n * gp[abs(n)] for n in ns),
    ]
    expected = [1, 0, 0, state["b"], 1]
    return [
        {"name": name, "actual": scalar(v), "expected": scalar(e), "residual": scalar(v - e)}
        for name, v, e in zip(
            ["sum_gamma", "sum_n_gamma", "sum_gp", "sum_n2_gamma", "sum_n2_gp"],
            actual,
            expected,
            strict=True,
        )
    ]


def evaluate_variant(case, constants, states, poles, cutoff, dps):
    K = mp.eye(3)
    raw_species = []
    for state in states:
        a, b, P, h, omega, Omega = (state[k] for k in ("a", "b", "P", "h", "omega", "Omega"))
        contributions, raw_poles = [], []
        for beta, c in poles:
            x = (omega - h * c) / Omega
            if b == 0:
                R = H = x / (x * x - 1)
            else:
                ns = range(-cutoff, cutoff + 1)
                R = mp.fsum(n * n * state["gamma"][abs(n)] / (b * (x - n)) for n in ns)
                H = mp.fsum(n * n * state["gp"][abs(n)] / (x - n) for n in ns)
            ar = mp.sqrt(2) * a * c
            term = mp.matrix(
                [
                    [R, 1j * H / x, ar * R / x],
                    [-1j * H / x, R - 2 * b * H / x**2, -1j * ar * H / x**2],
                    [ar * R / x, 1j * ar * H / x**2, 2 * c * c * (x + b * R) / x**2],
                ]
            )
            contributions.append(P * beta * term)
            raw_poles.append(
                {
                    "beta": scalar(beta),
                    "c": scalar(c),
                    "x": scalar(x),
                    "R": scalar(R),
                    "H": scalar(H),
                }
            )
        chi = mp.matrix(3, 3)
        for r in range(3):
            for c in range(3):
                chi[r, c] = mp.fsum(t[r, c] for t in contributions)
                K[r, c] += chi[r, c]
        raw_species.append(
            {
                "derived": {
                    k: scalar(state[k]) for k in ("thermal", "Omega", "wp2", "a", "b", "P", "h")
                },
                "poles": raw_poles,
                "chi_positive_side": matrix_record(chi),
                "gamma_identities": gamma_identities(state, cutoff),
                "gamma_cache": "once per case/species/dps, shared by all eight poles and both cutoffs",
            }
        )
    if number(case["kz"]) < 0:
        for r, c in ((0, 2), (1, 2), (2, 0), (2, 1)):
            K[r, c] = -K[r, c]
    nx = number(constants["C"]) * complex_input(case["kx"]) / number(case["omega"])
    nz = number(constants["C"]) * number(case["kz"]) / number(case["omega"])
    n = mp.matrix([nx, 0, nz])
    D = K + n * n.T - (nx * nx + nz * nz) * mp.eye(3)
    # All serialization below is inside this variant's respective workdps context.
    return {
        "id": case["id"],
        "computed_dps": dps,
        "harmonic_cutoff": cutoff,
        "harmonic_policy": "N/A analytic b0" if cutoff is None else "symmetric direct Bessel sum",
        "status": "RAW_OK",
        "K": matrix_record(K),
        "D": matrix_record(D),
        "detK": scalar(mp.det(K)),
        "detD": scalar(mp.det(D)),
        "detK_permutations": scalar(determinant_permutations(K)),
        "detD_permutations": scalar(determinant_permutations(D)),
        "nx": scalar(nx),
        "nz": scalar(nz),
        "species": raw_species,
    }
