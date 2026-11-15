"""Independent Maxwellian Eq.(3) reference; manual reproduction only."""

import mpmath as mp


def string(x):
    return mp.nstr(x, 160, strip_zeros=False)


def complex_strings(x):
    x = mp.mpc(x)
    return [string(x.real), string(x.imag)]


def complex_float(x):
    x = mp.mpc(x)
    return [float(x.real), float(x.imag)]


def from_pair(x):
    # JSON binary64 numbers are deliberately converted directly, not via str.
    return mp.mpc(mp.mpf(x[0]), mp.mpf(x[1]))


def Z(z):
    # Entire Landau continuation for exp(-i omega t); no fitted coefficients.
    return mp.j * mp.sqrt(mp.pi) * mp.exp(-z * z) * mp.erfc(-mp.j * z)


def parameters(case, constants, species):
    kb, eps = mp.mpf(constants["KB"]), mp.mpf(constants["eps0"])
    q, m, n, T = [mp.mpf(species[x]) for x in ["charge", "mass", "density", "temperature"]]
    B, w, kz, kx = (
        mp.mpf(case["B"]),
        mp.mpf(case["omega"]),
        mp.mpf(case["kz"]),
        from_pair(case["kx"]),
    )
    thermal = mp.sqrt(2 * kb * T / m)
    omega_c = q * B / m
    wp2 = n * q * q / (eps * m)
    a = kx * mp.sqrt(kb * T / m) / omega_c
    d = dict(thermal=thermal, Omega=omega_c, wp2=wp2, alpha=wp2 / (w * w), a=a, b=a * a)
    if kz:
        d.update(
            z0=w / (abs(kz) * thermal),
            z_plus1=(w - omega_c) / (abs(kz) * thermal),
            z_minus1=(w + omega_c) / (abs(kz) * thermal),
        )
    return d


def cold_linear_solve(case, constants):
    w, B, eps = mp.mpf(case["omega"]), mp.mpf(case["B"]), mp.mpf(constants["eps0"])
    sigma = mp.zeros(3)
    residuals = []
    for sp in case["species"]:
        q, m, n = [mp.mpf(sp[x]) for x in ["charge", "mass", "density"]]
        oc = q * B / m
        gyro = mp.matrix([[0, oc, 0], [-oc, 0, 0], [0, 0, 0]])
        A = -mp.j * w * mp.eye(3) - gyro
        for col in range(3):
            rhs = mp.matrix([q / m if row == col else 0 for row in range(3)])
            v = mp.lu_solve(A, rhs)
            for row in range(3):
                sigma[row, col] += n * q * v[row]
                residuals.append(abs((A * v - rhs)[row]) / max(mp.mpf(1), abs(rhs[row])))
    return mp.eye(3) + mp.j * sigma / (eps * w), residuals


def matrix_data(K, D, detK, detD, rounded=False):
    encode = complex_float if rounded else complex_strings
    return dict(
        K=[[encode(K[i, j]) for j in range(3)] for i in range(3)],
        D=[[encode(D[i, j]) for j in range(3)] for i in range(3)],
        det_K=encode(detK),
        det_D=encode(detD),
    )


def calculate(case, constants, dps, cutoff):
    with mp.workdps(dps):
        w, kz, kx = mp.mpf(case["omega"]), mp.mpf(case["kz"]), from_pair(case["kx"])
        K = mp.eye(3)
        identities = []
        params = []
        for index, sp in enumerate(case["species"]):
            p = parameters(case, constants, sp)
            params.append({name: complex_strings(value) for name, value in p.items()})
            a, b, oc, alpha = p["a"], p["b"], p["Omega"], p["alpha"]
            if not kx and not kz:
                wp2 = p["wp2"]
                K[0, 0] -= wp2 / (w * w - oc * oc)
                K[1, 1] -= wp2 / (w * w - oc * oc)
                K[0, 1] -= mp.j * wp2 * oc / (w * (w * w - oc * oc))
                K[1, 0] += mp.j * wp2 * oc / (w * (w * w - oc * oc))
                K[2, 2] -= alpha
                continue
            if not kx:
                z0 = p["z0"]
                plus, minus = Z(p["z_plus1"]), Z(p["z_minus1"])
                K[0, 0] += alpha * z0 * (plus + minus) / 2
                K[1, 1] += alpha * z0 * (plus + minus) / 2
                K[0, 1] += mp.j * alpha * z0 * (plus - minus) / 2
                K[1, 0] -= mp.j * alpha * z0 * (plus - minus) / 2
                K[2, 2] += 2 * alpha * z0 * z0 * (1 + z0 * Z(z0))
                continue
            assert cutoff is not None
            gamma = {n: mp.exp(-b) * mp.besseli(n, b) for n in range(cutoff + 2)}

            def G(n):
                return gamma[abs(n)]

            def GP(n):
                return (G(n - 1) + G(n + 1)) / 2 - G(n)

            orders = range(-cutoff, cutoff + 1)
            sums = [
                mp.fsum(G(n) for n in orders),
                mp.fsum(n * G(n) for n in orders),
                mp.fsum(GP(n) for n in orders),
                mp.fsum(n * n * G(n) for n in orders),
                mp.fsum(n * n * GP(n) for n in orders),
            ]
            expected = [mp.mpf(1), mp.mpf(0), mp.mpf(0), b, mp.mpf(1)]
            identities.append(
                dict(
                    species_index=index,
                    observed=[complex_strings(v) for v in sums],
                    expected=[complex_strings(v) for v in expected],
                    absolute_diffs=[string(abs(v - e)) for v, e in zip(sums, expected)],
                    scaled_diffs=[
                        string(abs(v - e) / max(mp.mpf(1), abs(e))) for v, e in zip(sums, expected)
                    ],
                )
            )
            terms = [[[] for _ in range(3)] for _ in range(3)]
            for n in orders:
                g, gp = G(n), GP(n)
                xx = n * n * g / b
                yy = xx - 2 * b * gp
                xy = mp.j * n * gp
                if not kz:
                    factor = -alpha * w / (w - n * oc)
                    X = [[xx, xy, 0], [-xy, yy, 0], [0, 0, g]]
                else:
                    zn = (w - n * oc) / (abs(kz) * p["thermal"])
                    factor = alpha * p["z0"] * Z(zn)
                    xz = mp.sqrt(2) * zn * n * g / a
                    yz = -mp.j * mp.sqrt(2) * zn * a * gp
                    X = [[xx, xy, xz], [-xy, yy, yz], [xz, -yz, 2 * zn * zn * g]]
                for i in range(3):
                    for j in range(3):
                        terms[i][j].append(factor * X[i][j])
            chi = mp.matrix([[mp.fsum(terms[i][j]) for j in range(3)] for i in range(3)])
            if kz:
                chi[2, 2] += 2 * alpha * p["z0"] ** 2
            K += chi
        # Assemble every species first, then reflect the four cross-z entries.
        if kz < 0:
            for i, j in [(0, 2), (1, 2), (2, 0), (2, 1)]:
                K[i, j] = -K[i, j]
        nx = mp.mpf(constants["C"]) * kx / w
        nz = mp.mpf(constants["C"]) * kz / w
        D = K.copy()
        D[0, 0] -= nz * nz
        D[1, 1] -= nx * nx + nz * nz
        D[2, 2] -= nx * nx
        D[0, 2] += nx * nz
        D[2, 0] += nx * nz
        detK, detD = mp.det(K), mp.det(D)
        result = dict(
            case_id=case["id"],
            dps=dps,
            N=cutoff,
            branch=(
                "cold-both-zero"
                if not kx and not kz
                else "analytic-kx-zero"
                if not kx
                else "analytic-kz-zero-harmonics"
                if not kz
                else "Eq3-harmonics"
            ),
            high_precision=matrix_data(K, D, detK, detD),
            rounded_binary64=matrix_data(K, D, detK, detD, True),
            parameters=params,
            nx=complex_strings(nx),
            nz=complex_strings(nz),
            bessel_identity_checks=identities,
        )
        if not kx and not kz:
            solved, residuals = cold_linear_solve(case, constants)
            result["cold_lorentz_check"] = dict(
                time_convention="exp(-i*omega*t)",
                gyro_cross="(q/m)*(v cross B) = (Omega*v_y,-Omega*v_x,0)",
                equation="(-i*omega*I-gyro_cross)*v=(q/m)*E; K=I+i*sigma/(eps0*omega)",
                K_solved=[[complex_strings(solved[i, j]) for j in range(3)] for i in range(3)],
                absolute_diffs=[
                    [string(abs(K[i, j] - solved[i, j])) for j in range(3)] for i in range(3)
                ],
                scaled_diffs=[
                    [
                        string(abs(K[i, j] - solved[i, j]) / max(mp.mpf(1), abs(K[i, j])))
                        for j in range(3)
                    ]
                    for i in range(3)
                ],
                linear_equation_scaled_residuals=[string(x) for x in residuals],
            )
        return result
