"""High precision two-sided Padé construction for the plasma dispersion function."""

import numpy as np


def _validate_orders(J, I, precision):
    for value, name in ((J, "J"), (I, "I"), (precision, "precision")):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValueError(name + " must be an integer")
    if J < 1 or not 0 <= I <= 2 * J or precision < 32:
        raise ValueError("J>=1, 0<=I<=2J and precision>=32 required")


def _float_array(values):
    return np.asarray([complex(value) for value in values], complex)


def construct_maxwellian_pade(*, J, I, precision):
    """Construct Padé poles and residues at the requested decimal precision."""

    _validate_orders(J, I, precision)
    import mpmath as mp

    with mp.workdps(int(precision)):
        J = int(J)
        I = int(I)
        K = 2 * J - I
        positive_moments = [mp.mpc(0)] * (2 * J + 4)
        negative_moments = positive_moments.copy()
        for n in range(J + 2):
            positive_moments[2 * n] = (-1) ** n * mp.j * mp.sqrt(mp.pi) / mp.gamma(n + 1)
            positive_moments[2 * n + 1] = (
                -((-1) ** n) * mp.gamma(mp.mpf("0.5")) / mp.gamma(n + mp.mpf("1.5"))
            )
            negative_moments[2 * n + 1] = -mp.gamma(n + mp.mpf("0.5")) / mp.gamma(mp.mpf("0.5"))

        matrix = mp.matrix(2 * J)
        right_hand_side = mp.matrix(2 * J, 1)
        for row in range(1, I + 1):
            right_hand_side[row - 1] = positive_moments[row - 1]
            if row <= J:
                matrix[row - 1, row - 1] = 1
            for column in range(1, row):
                if row <= J + column:
                    matrix[row - 1, J + row - column - 1] = -positive_moments[column - 1]
        for row in range(1, K + 1):
            if row <= J:
                matrix[I + row - 1, J - row] = 1
            for column in range(1, row + 1):
                if row < 2 * J + column:
                    matrix[I + row - 1, 2 * J - row + column - 1] = -negative_moments[column]
            if row > J:
                right_hand_side[I + row - 1] = -negative_moments[1]

        coefficients = mp.lu_solve(matrix, right_hand_side)
        numerator = list(reversed([coefficients[index] for index in range(J)]))
        denominator = list(reversed([coefficients[J + index] for index in range(J)]))
        denominator.append(mp.mpf(1))

        seeds = np.roots(_float_array(denominator))
        derivative = [denominator[index] * (J - index) for index in range(J)]
        target = mp.power(10, -int(precision) + 10)
        roots = []
        root_errors = []
        for seed in seeds:
            root = mp.mpc(float(seed.real), float(seed.imag))
            for _ in range(100):
                value = mp.polyval(denominator, root)
                slope = mp.polyval(derivative, root)
                if slope == 0:
                    raise ArithmeticError(
                        "repeated or unresolved polynomial root requires higher-order-pole contract"
                    )
                step = value / slope
                root -= step
                if abs(step) <= target * max(1, abs(root)):
                    break
            else:
                raise ArithmeticError("high-precision Padé root refinement did not converge")

            scale = max(
                1,
                sum(
                    abs(coefficient) * max(1, abs(root)) ** (J - index)
                    for index, coefficient in enumerate(denominator)
                ),
            )
            error = abs(mp.polyval(denominator, root)) / scale
            if error > target:
                raise ArithmeticError("Padé root polynomial residual exceeds declared precision")
            roots.append(root)
            root_errors.append(error)

        for index, root in enumerate(roots):
            if any(
                abs(root - previous) <= mp.sqrt(target) * max(1, abs(root))
                for previous in roots[:index]
            ):
                raise ArithmeticError(
                    "root refinement collapsed distinct seeds; simple-pole "
                    "representation unresolved"
                )

        residues = [mp.polyval(numerator, root) / mp.polyval(derivative, root) for root in roots]
        linear_residual = mp.norm(matrix * coefficients - right_hand_side) / (
            mp.norm(matrix) * mp.norm(coefficients) + mp.norm(right_hand_side)
        )
        if linear_residual > target:
            raise ArithmeticError("high-precision Padé linear residual exceeds declared precision")

        residue_array = _float_array(residues)
        pole_array = _float_array(roots)
        if not np.isfinite(residue_array).all() or not np.isfinite(pole_array).all():
            raise FloatingPointError("Padé poles/residues not representable in binary64")

        return {
            "J": J,
            "I": I,
            "K": K,
            "precision_digits": int(precision),
            "bzj": residue_array,
            "czj": pole_array,
            "p": _float_array(numerator),
            "q": _float_array(denominator),
            "pq": _float_array(coefficients),
            "Mpq": np.asarray(
                [[complex(matrix[i, j]) for j in range(2 * J)] for i in range(2 * J)]
            ),
            "B": _float_array(right_hand_side),
            "moments": np.asarray(
                [
                    sum(residue_array),
                    sum(residue_array * pole_array),
                    sum(residue_array * pole_array * pole_array),
                ]
            ),
            "high_precision_linear_residual": mp.nstr(linear_residual, int(precision)),
            "high_precision_root_residual": [
                mp.nstr(value, int(precision)) for value in root_errors
            ],
            "high_precision_poles": [mp.nstr(value, int(precision)) for value in roots],
            "high_precision_residues": [mp.nstr(value, int(precision)) for value in residues],
            "precision_claim": (
                "coefficient/root construction at declared decimal precision; "
                "output numeric ports binary64; Z applicability separately qualified"
            ),
        }
