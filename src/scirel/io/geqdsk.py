"""Read the standard EFIT G-EQDSK equilibrium file.

The record layout follows L. L. Lao, "G EQDSK FORMAT" (EFIT documentation,
7 February 1997).  Each Fortran ``read`` starts a new record; real numbers use
``5e16.9`` and may run together when a field begins with a minus sign.

Units are those the format specification states: lengths in m, poloidal flux
in Wb/rad, ``fpol = R B_T`` in m T, pressure in N/m^2, plasma current in A and
``bcentr`` in T.  The reader does not infer a COCOS sign convention; it returns
the values as written.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from scirel.io.eqdsk import EQDSKFormatError

__all__ = ["read_geqdsk"]

# One Fortran real: optional sign, mantissa, optional E/D exponent.  Matching
# numbers, not splitting on spaces, separates fields such as "1.0E+00-2.0E+00".
_NUMBER = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][+-]?\d+)?")
# Positions in the four scalar records (5e16.9 each).  Records three and four
# repeat simag, rmaxis, zmaxis and sibry and pad with dummies.
_SCALARS = {
    "rdim": 0,
    "zdim": 1,
    "rcentr": 2,
    "rleft": 3,
    "zmid": 4,
    "rmaxis": 5,
    "zmaxis": 6,
    "simag": 7,
    "sibry": 8,
    "bcentr": 9,
    "current": 10,
}
_PROFILES = ("fpol", "pres", "ffprim", "pprime")


def _numbers(text: str) -> list[str]:
    return _NUMBER.findall(text)


def _header(line: str) -> tuple[str, int, int]:
    """Split the ``(6a8, 3i4)`` first record into the title and grid sizes."""
    fields = line[48:].split() if len(line) > 48 else []
    if len(fields) < 2:
        fields = line.split()
    try:
        nw, nh = int(fields[-2]), int(fields[-1])
    except (IndexError, ValueError) as exc:
        raise EQDSKFormatError("first record must end with the integers NW and NH") from exc
    if nw < 2 or nh < 2:
        raise EQDSKFormatError("NW and NH must both be at least 2")
    return line[:48].rstrip(), nw, nh


class _Stream:
    """Numbers after the first record, consumed in specification order."""

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.position = 0

    def take(self, count: int, section: str) -> np.ndarray:
        stop = self.position + count
        if stop > len(self.tokens):
            raise EQDSKFormatError(f"truncated {section}: expected {count} values")
        chunk = self.tokens[self.position : stop]
        self.position = stop
        try:
            values = np.array([float(token.replace("D", "E").replace("d", "e")) for token in chunk])
        except ValueError as exc:
            raise EQDSKFormatError(f"non-numeric value in {section}") from exc
        if not np.all(np.isfinite(values)):
            raise EQDSKFormatError(f"{section} must contain finite values")
        return values

    def take_count(self, section: str) -> int:
        token = self.take(1, section)[0]
        if token != int(token) or token < 0:
            raise EQDSKFormatError(f"{section} must be a non-negative integer")
        return int(token)


def read_geqdsk(filename: str | Path, *, strict: bool = True) -> dict[str, Any]:
    r"""Read a standard EFIT G-EQDSK file.

    Parameters
    ----------
    filename : str or Path
        Path of the G-EQDSK text file.
    strict : bool, optional
        If True (default), reject numbers after the limiter section.  Some codes
        append extra records; ``strict=False`` ignores them, but every record of
        the standard layout must still be present.

    Returns
    -------
    dict
        Keys use the specification names.

        ``description`` (str), ``nw``, ``nh`` (int);
        ``rdim``, ``zdim``, ``rcentr``, ``rleft``, ``zmid``, ``rmaxis``,
        ``zmaxis`` (m); ``simag``, ``sibry`` (Wb/rad, flux at the magnetic
        axis and boundary); ``bcentr`` (T, vacuum toroidal field at
        ``rcentr``); ``current`` (A);
        ``fpol`` (m T), ``pres`` (N/m^2), ``ffprim`` ((m T)^2/(Wb/rad)),
        ``pprime`` (N/m^2/(Wb/rad)), ``qpsi``: shape ``(nw,)`` on the uniform
        flux grid ``psi`` from ``simag`` to ``sibry``;
        ``psirz`` (Wb/rad), shape ``(nh, nw)``, with ``psirz[j, i]`` the flux
        at ``(r[i], z[j])``;
        ``r`` shape ``(nw,)`` from ``rleft`` to ``rleft + rdim`` and ``z``
        shape ``(nh,)`` from ``zmid - zdim/2`` to ``zmid + zdim/2`` (m);
        ``rbbbs``, ``zbbbs`` (m), the plasma boundary; ``rlim``, ``zlim``
        (m), the limiter; ``nbbbs``, ``limitr`` (int), their lengths.
    mapping : dict[str,Any], shape dict
        Specification-named scalars, profiles fpol/pres/ffprim/pprime/qpsi,
        psirz (nh, nw), r, z, psi, boundary rbbbs/zbbbs and limiter rlim/zlim
        [m, Wb/rad, m T, N/m^2, A, T as in the specification]. Finite values;
        positive RDIM, ZDIM; SIMAG differs from SIBRY.

    Raises
    ------
    EQDSKFormatError
        If a record is missing, non-numeric or non-finite, a count is not a
        non-negative integer, a grid extent is not positive, the axis and
        boundary flux coincide, or ``strict`` is True and extra numbers follow.

    See Also
    --------
    scirel.field.poloidal_field_from_flux : Poloidal field from the per-radian flux psi(R, Z).

    Notes
    -----
    The specification repeats ``simag``, ``sibry``, ``rmaxis`` and ``zmaxis``
    in the third and fourth scalar records.  The values from the second record
    are returned; the repeats are not compared because several writers store
    zeros there.  Sign conventions (COCOS) are not inferred.

    Examples
    --------
    >>> from pathlib import Path
    >>> from tempfile import TemporaryDirectory
    >>> import numpy as np
    >>> from scirel.io import read_geqdsk
    >>> rec = lambda v: [''.join('%16.9E' % x for x in v[i:i+5]) for i in range(0, len(v), 5)]
    >>> lines = ['EXAMPLE'.ljust(48) + '   0   3   2']
    >>> for values in ([2., 3., 1.5, .25, 0.], [1.2, 0., -.75, .5, -2.5], [1e6, -.75, 0., 1.2, 0.], [0., 0., .5, 0., 0.]):
    ...     lines += rec(values)
    >>> for _ in range(4):
    ...     lines += rec([1., 2., 3.])
    >>> lines += rec([11., 21., 31., 12., 22., 32.]) + rec([1., 2., 3.]) + ['    0    0']
    >>> with TemporaryDirectory() as directory:
    ...     path = Path(directory) / 'g.eqdsk'
    ...     _ = path.write_text('\n'.join(lines) + '\n')
    ...     g = read_geqdsk(path)
    ...     assert g['psirz'].shape == (2, 3) and g['psirz'][1, 2] == 32.0
    ...     assert np.allclose(g['r'], [.25, 1.25, 2.25]) and np.allclose(g['z'], [-1.5, 1.5])
    """
    text = Path(filename).read_text()
    first, _, rest = text.partition("\n")
    description, nw, nh = _header(first.rstrip("\r"))
    stream = _Stream(_numbers(rest))
    data: dict[str, Any] = {"description": description, "nw": nw, "nh": nh}
    scalars = stream.take(20, "scalar records")
    data.update({name: float(scalars[index]) for name, index in _SCALARS.items()})
    if data["rdim"] <= 0.0 or data["zdim"] <= 0.0:
        raise EQDSKFormatError("RDIM and ZDIM must be positive")
    if data["simag"] == data["sibry"]:
        raise EQDSKFormatError("SIMAG and SIBRY must differ")
    for name in _PROFILES:
        data[name] = stream.take(nw, name)
    data["psirz"] = stream.take(nw * nh, "psirz").reshape(nh, nw)
    data["qpsi"] = stream.take(nw, "qpsi")
    data["nbbbs"] = stream.take_count("NBBBS")
    data["limitr"] = stream.take_count("LIMITR")
    boundary = stream.take(2 * data["nbbbs"], "boundary").reshape(-1, 2)
    limiter = stream.take(2 * data["limitr"], "limiter").reshape(-1, 2)
    if strict and stream.position != len(stream.tokens):
        extra = len(stream.tokens) - stream.position
        raise EQDSKFormatError(
            f"{extra} numbers follow the limiter section; use strict=False to ignore them"
        )
    data["rbbbs"], data["zbbbs"] = boundary[:, 0].copy(), boundary[:, 1].copy()
    data["rlim"], data["zlim"] = limiter[:, 0].copy(), limiter[:, 1].copy()
    data["r"] = np.linspace(data["rleft"], data["rleft"] + data["rdim"], nw)
    data["z"] = np.linspace(data["zmid"] - data["zdim"] / 2, data["zmid"] + data["zdim"] / 2, nh)
    data["psi"] = np.linspace(data["simag"], data["sibry"], nw)
    return data
