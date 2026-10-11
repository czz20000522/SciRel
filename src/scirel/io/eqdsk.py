"""Pleiades legacy extended EQDSK exchange.

This module intentionally names the retained Pleiades dialect rather than
calling it standard GEQDSK.  The source format has a 48-character title,
four integer header fields (``cursign, nnr, nnz, nnv``), five profiles of
length ``nnv``, a C-order ``(nnz, nnr)`` psi grid, and one combined limiter /
vessel coordinate section.  It is not the standard EFIT gEQDSK contract,
which uses three header integers and distinct ``NW``/``NH`` dimensions.

The implementation is derived from Pleiades D0 ``pleiades/io.py`` (commit
``be412aa14b775f2a8170315242b92208bd11fc0e``), with D2-bounded structural
validation.  It does not assign units, COCOS, or physical meaning to values
whose source did not establish them.
"""
from __future__ import annotations

from numbers import Integral
from pathlib import Path
from typing import Any, Mapping

import numpy as np

DIALECT = "pleiades-legacy-extended"
_REQUIRED = (
    "title", "cursign", "nnr", "nnz", "nnv", "rbox", "zbox", "psi_lim",
    "Ip", "tor_flux", "p_flux", "rbphi_flux", "pprime_flux", "psi",
    "q_flux", "nlim_pairs", "nves_pairs", "lim_pairs", "ves_pairs",
)
_PROFILE_KEYS = ("tor_flux", "p_flux", "rbphi_flux", "pprime_flux", "q_flux")


class EQDSKFormatError(ValueError):
    """Raised when a Pleiades extended-dialect file violates its structure."""


def _float_fields(line: str, *, fixed: bool = False) -> list[float]:
    """Parse one line using source whitespace/fixed-width lexical rules."""
    raw = line.rstrip("\r\n")
    if fixed:
        if len(raw) % 16:
            raise EQDSKFormatError("coordinate record must contain 16-character fields")
        fields = [raw[i : i + 16] for i in range(0, len(raw), 16)]
        fields = [field for field in fields if field.strip()]
    else:
        fields = raw.split()
        try:
            values = [float(field) for field in fields]
        except ValueError:
            fields = [raw[i : i + 16] for i in range(0, len(raw), 16)]
            fields = [field for field in fields if field.strip()]
        else:
            if not np.all(np.isfinite(values)):
                raise EQDSKFormatError("EQDSK records must contain finite values")
            return values
    try:
        values = [float(field) for field in fields]
    except ValueError as exc:
        raise EQDSKFormatError(f"non-numeric field in EQDSK record: {raw!r}") from exc
    if not np.all(np.isfinite(values)):
        raise EQDSKFormatError("EQDSK records must contain finite values")
    return values


def _read_values(lines: list[str], start: int, count: int, *, section: str,
                 coordinates: bool = False) -> tuple[np.ndarray, int]:
    """Read exactly ``count`` values from the source-defined record group."""
    if count < 0:
        raise EQDSKFormatError(f"{section} count must be non-negative")
    nlines = (count + 4) // 5
    stop = start + nlines
    if stop > len(lines):
        raise EQDSKFormatError(f"truncated {section}: expected {count} values")
    values: list[float] = []
    for line in lines[start:stop]:
        fields = _float_fields(line, fixed=coordinates)
        values.extend(fields)
    if len(values) != count:
        raise EQDSKFormatError(
            f"{section} has {len(values)} values; expected {count}"
        )
    return np.asarray(values, dtype=float), stop


def _header(lines: list[str]) -> tuple[str, int, int, int, int]:
    if not lines:
        raise EQDSKFormatError("empty EQDSK file")
    line = lines[0].rstrip("\r\n")
    if len(line) != 64:
        raise EQDSKFormatError("header must contain exactly a 48-character title and four 4-character integers")
    title = line[:48]
    tail = line[48:]
    chunks = [tail[i : i + 4] for i in range(0, 16, 4)]
    try:
        values = [int(chunk) for chunk in chunks]
    except ValueError:
        fields = tail.split()
        if len(fields) != 4:
            raise EQDSKFormatError("header must contain exactly four integer fields")
        try:
            values = [int(value) for value in fields[-4:]]
        except ValueError as exc:
            raise EQDSKFormatError("header integer fields are malformed") from exc
    if len(values) != 4:
        raise EQDSKFormatError("header does not contain four integer fields")
    cursign, nnr, nnz, nnv = values
    if nnr <= 0 or nnz <= 0 or nnv <= 0:
        raise EQDSKFormatError("nnr, nnz, and nnv must be positive")
    return title, cursign, nnr, nnz, nnv


def _scalar_records(lines: list[str]) -> tuple[np.ndarray, int]:
    if len(lines) < 5:
        raise EQDSKFormatError("missing five scalar records")
    records = []
    for i in range(1, 5):
        fields = _float_fields(lines[i])
        if len(fields) != 5:
            raise EQDSKFormatError(f"header scalar record {i} has {len(fields)} values; expected 5")
        records.extend(fields)
    return np.asarray(records, dtype=float).reshape(4, 5), 5


def read_pleiades_eqdsk(filename: str | Path, *, strict: bool = True) -> dict[str, Any]:
    """Read the Pleiades legacy extended EQDSK dialect.

    ``strict=True`` rejects records after the declared coordinate section.
    ``strict=False`` permits such trailing records for compatibility; it still
    requires every declared profile, grid, and coordinate value.  Coordinates
    remain fixed-width, as required by the source parser.
    """
    lines = Path(filename).read_text().splitlines()
    title, cursign, nnr, nnz, nnv = _header(lines)
    scalar, offset = _scalar_records(lines)
    data: dict[str, Any] = {
        "title": title, "cursign": cursign, "nnr": nnr, "nnz": nnz,
        "nnv": nnv, "rbox": float(scalar[0, 0]), "zbox": float(scalar[0, 1]),
        "psi_lim": float(scalar[1, 3]), "Ip": float(scalar[2, 0]),
        "header_scalars": scalar,
    }
    for key in _PROFILE_KEYS[:4]:
        values, offset = _read_values(lines, offset, nnv, section=key)
        data[key] = values
    psi_values, offset = _read_values(lines, offset, nnr * nnz, section="psi")
    data["psi"] = psi_values.reshape((nnz, nnr))
    q_values, offset = _read_values(lines, offset, nnv, section="q_flux")
    data["q_flux"] = q_values
    if offset >= len(lines):
        raise EQDSKFormatError("missing limiter/vessel pair counts")
    count_record = lines[offset].rstrip("\r\n")
    if len(count_record) == 10:
        count_fields = (count_record[:5], count_record[5:])
    else:
        count_fields = count_record.split()
    if len(count_fields) != 2:
        raise EQDSKFormatError("limiter/vessel count record must contain two integers")
    try:
        nlim_pairs, nves_pairs = (int(x) for x in count_fields)
    except ValueError as exc:
        raise EQDSKFormatError("limiter/vessel counts are malformed") from exc
    if nlim_pairs < 0 or nves_pairs < 0:
        raise EQDSKFormatError("limiter/vessel counts must be non-negative")
    offset += 1
    pair_values, offset = _read_values(
        lines, offset, 2 * (nlim_pairs + nves_pairs), section="limiter/vessel coordinates",
        coordinates=True,
    )
    if strict and offset != len(lines):
        raise EQDSKFormatError(f"unexpected trailing records after coordinates: {len(lines) - offset}")
    data["nlim_pairs"], data["nves_pairs"] = nlim_pairs, nves_pairs
    pairs = pair_values.reshape((-1, 2))
    data["lim_pairs"] = pairs[:nlim_pairs].copy()
    data["ves_pairs"] = pairs[nlim_pairs:].copy()
    data["R"], data["Z"] = np.meshgrid(
        np.linspace(0, data["rbox"], nnr),
        np.linspace(-data["zbox"] / 2, data["zbox"] / 2, nnz),
    )
    return data


def _integer(value: Any, key: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise EQDSKFormatError(f"{key} must be an integer")
    return int(value)


def _finite_float(value: Any, key: str) -> float:
    if np.iscomplexobj(value):
        raise EQDSKFormatError(f"{key} must be a finite real number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EQDSKFormatError(f"{key} must be a finite number") from exc
    if not np.isfinite(result):
        raise EQDSKFormatError(f"{key} must be a finite number")
    return result


def _fixed_float(value: Any, key: str) -> float:
    result = _finite_float(value, key)
    rendered = f"{result:16.9E}"
    if len(rendered) != 16:
        raise EQDSKFormatError(f"{key} is not representable in a 16-character field")
    return result


def _fixed_integer(value: Any, key: str, width: int) -> int:
    result = _integer(value, key)
    rendered = f"{result:{width}d}"
    if len(rendered) != width:
        raise EQDSKFormatError(
            f"{key} is not representable in a {width}-character integer field"
        )
    return result


def _as_vector(value: Any, key: str, count: int) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim != 1 or arr.size != count:
        raise EQDSKFormatError(f"{key} must have shape ({count},), got {arr.shape}")
    return arr


def _as_pairs(value: Any, key: str, count: int) -> np.ndarray:
    arr = np.asarray(value)
    if arr.shape != (count, 2):
        raise EQDSKFormatError(f"{key} must have shape ({count}, 2), got {arr.shape}")
    return arr


def _validated(data: Mapping[str, Any]) -> dict[str, Any]:
    missing = [key for key in _REQUIRED if key not in data]
    if missing:
        raise KeyError(missing[0])
    nnr, nnz, nnv = (
        _fixed_integer(data[key], key, 4) for key in ("nnr", "nnz", "nnv")
    )
    if nnr <= 0 or nnz <= 0 or nnv <= 0:
        raise EQDSKFormatError("nnr, nnz, and nnv must be positive")
    title_value = data["title"]
    if not isinstance(title_value, str):
        raise EQDSKFormatError("title must be a string")
    if any(separator in title_value for separator in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"):
        raise EQDSKFormatError("title must not contain line separators")
    if len(title_value) > 48:
        raise EQDSKFormatError("title must contain at most 48 characters")
    title = title_value.ljust(48)
    result = dict(data)
    result.update(nnr=nnr, nnz=nnz, nnv=nnv, title=title)
    # The retained Pleiades record stores only radial/span extents (rbox,
    # zbox).  Its reader therefore reconstructs R=linspace(0,rbox,nnr) and
    # Z=linspace(-zbox/2,zbox/2,nnz); an arbitrary radial origin cannot be
    # represented by this dialect.  Reject an attached solver grid that would
    # otherwise be silently shifted on round-trip.  This is an explicit
    # representability check, not an inference of EFIT/COCOS semantics.
    if "R" in data or "Z" in data:
        if "R" not in data or "Z" not in data:
            raise EQDSKFormatError("R and Z must be supplied together")
        rbox = _finite_float(data["rbox"], "rbox")
        zbox = _finite_float(data["zbox"], "zbox")
        R = np.asarray(data["R"])
        Z = np.asarray(data["Z"])
        expected_R, expected_Z = np.meshgrid(
            np.linspace(0.0, rbox, nnr),
            np.linspace(-zbox / 2.0, zbox / 2.0, nnz),
        )
        if (R.shape != (nnz, nnr) or Z.shape != (nnz, nnr) or
                np.iscomplexobj(R) or np.iscomplexobj(Z) or
                not np.all(np.isfinite(R)) or not np.all(np.isfinite(Z)) or
                not np.array_equal(R, expected_R) or not np.array_equal(Z, expected_Z)):
            raise EQDSKFormatError(
                "R/Z grid is not representable: Pleiades dialect fixes R origin at 0 and Z at +/-zbox/2"
            )
    # Also reject explicit origin metadata rather than silently discarding it.
    # These keys are accepted only as a caller-side guard; they are not added
    # to the legacy record because no origin field exists in the dialect.
    if "r_origin" in data and _finite_float(data["r_origin"], "r_origin") != 0.0:
        raise EQDSKFormatError("r_origin is not representable: Pleiades dialect fixes R origin at 0")
    if "z_origin" in data and _finite_float(data["z_origin"], "z_origin") != 0.0:
        raise EQDSKFormatError("z_origin is not representable: Pleiades dialect centers Z at 0")
    for key in _PROFILE_KEYS:
        result[key] = _as_vector(data[key], key, nnv)
        if not np.issubdtype(result[key].dtype, np.number) or not np.all(np.isfinite(result[key])):
            raise EQDSKFormatError(f"{key} must contain finite numeric values")
        result[key] = np.asarray([_fixed_float(v, key) for v in result[key]], dtype=float)
    psi = np.asarray(data["psi"])
    if psi.shape != (nnz, nnr):
        raise EQDSKFormatError(f"psi must have shape ({nnz}, {nnr}), got {psi.shape}")
    if not np.issubdtype(psi.dtype, np.number) or not np.all(np.isfinite(psi)):
        raise EQDSKFormatError("psi must contain finite numeric values")
    result["psi"] = np.asarray([_fixed_float(v, "psi") for v in psi.reshape(-1)], dtype=float).reshape(psi.shape)
    nlim, nves = (
        _fixed_integer(data[key], key, 5) for key in ("nlim_pairs", "nves_pairs")
    )
    if nlim < 0 or nves < 0:
        raise EQDSKFormatError("limiter/vessel counts must be non-negative")
    result["nlim_pairs"], result["nves_pairs"] = nlim, nves
    result["cursign"] = _fixed_integer(data["cursign"], "cursign", 4)
    result["lim_pairs"] = _as_pairs(data["lim_pairs"], "lim_pairs", nlim)
    result["ves_pairs"] = _as_pairs(data["ves_pairs"], "ves_pairs", nves)
    for key in ("lim_pairs", "ves_pairs"):
        if not np.issubdtype(result[key].dtype, np.number) or not np.all(np.isfinite(result[key])):
            raise EQDSKFormatError(f"{key} must contain finite numeric values")
        result[key] = np.asarray([_fixed_float(v, key) for v in result[key].reshape(-1)], dtype=float).reshape(result[key].shape)
    raw_header = data.get("header_scalars", np.zeros((4, 5)))
    if np.iscomplexobj(raw_header):
        raise EQDSKFormatError("header_scalars must contain finite real values")
    header = np.asarray(raw_header, dtype=float)
    if header.shape != (4, 5) or not np.all(np.isfinite(header)):
        raise EQDSKFormatError("header_scalars must be finite and have shape (4, 5)")
    result["header_scalars"] = header.copy()
    result["header_scalars"][0, :2] = [_finite_float(data["rbox"], "rbox"), _finite_float(data["zbox"], "zbox")]
    result["header_scalars"][1, 3] = _finite_float(data["psi_lim"], "psi_lim")
    result["header_scalars"][2, 0] = _finite_float(data["Ip"], "Ip")
    for value in result["header_scalars"].reshape(-1):
        _fixed_float(value, "header_scalars")
    return result


def _format_float(value: Any, key: str) -> str:
    result = _fixed_float(value, key)
    return f"{result:16.9E}"


def _format_values(values: Any, key: str = "values") -> str:
    flat = np.asarray(values).reshape(-1)
    rows = []
    for start in range(0, flat.size, 5):
        row = flat[start : start + 5]
        rows.append("".join(_format_float(value, key) for value in row))
    return "\n".join(rows)


def write_pleiades_eqdsk(data: Mapping[str, Any], filename: str | Path) -> None:
    """Write a structurally validated Pleiades extended-dialect dictionary."""
    d = _validated(data)  # validate before opening/truncating the destination
    header = d["header_scalars"]
    lines = [d["title"] + "".join(f"{int(d[key]):4d}" for key in ("cursign", "nnr", "nnz", "nnv"))]
    lines.extend(_format_values(row) for row in header)
    for key in _PROFILE_KEYS[:4]:
        lines.append(_format_values(d[key]))
    lines.append(_format_values(d["psi"]))
    lines.append(_format_values(d["q_flux"]))
    lines.append(f"{d['nlim_pairs']:5d}{d['nves_pairs']:5d}")
    if d["nlim_pairs"] + d["nves_pairs"]:
        lines.append(_format_values(np.vstack((d["lim_pairs"], d["ves_pairs"]))))
    Path(filename).write_text("\n".join(lines) + "\n")


def _resample_contour(segment: np.ndarray, count: int, start: tuple[float, float],
                      end: tuple[float, float]) -> np.ndarray:
    """Resample the source-selected arc without assuming single-valued R(Z).

    The source rolls open paths as if they were rings and fits R(Z), creating
    spurious jumps or failing when Z is not monotonic. Here an open path keeps
    its adjacency; a closed path keeps the source clockwise direction. Nearest
    start/end vertices and longest-component selection retain source choices.
    """
    points = np.asarray(segment, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 2 or not np.all(np.isfinite(points)):
        raise EQDSKFormatError("contour segment is empty or nonfinite")
    points = points[np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 0.0]]
    if points.shape[0] < 2:
        raise EQDSKFormatError("contour segment is degenerate")
    closed = np.array_equal(points[0], points[-1])
    if closed:
        points = points[:-1]
        if points.shape[0] < 3:
            raise EQDSKFormatError("closed contour segment is degenerate")
        signed_twice_area = np.sum(points[:, 0]*np.roll(points[:, 1], -1) -
                                   points[:, 1]*np.roll(points[:, 0], -1))
        if signed_twice_area > 0.0:
            points = points[::-1]
        start_idx = int(np.argmin(np.sum((points - np.asarray(start)) ** 2, axis=1)))
        points = np.roll(points, -start_idx, axis=0)
        end_idx = int(np.argmin(np.sum((points - np.asarray(end)) ** 2, axis=1)))
        points = points[:end_idx+1]
    else:
        start_idx = int(np.argmin(np.sum((points - np.asarray(start)) ** 2, axis=1)))
        end_idx = int(np.argmin(np.sum((points - np.asarray(end)) ** 2, axis=1)))
        if start_idx <= end_idx:
            points = points[start_idx:end_idx+1]
        else:
            points = points[end_idx:start_idx+1][::-1]
    if points.shape[0] < 2:
        raise EQDSKFormatError("source contour hints select a degenerate arc")
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    if not np.isfinite(cumulative[-1]) or cumulative[-1] <= 0.0:
        raise EQDSKFormatError("contour has zero arclength")
    sample_s = np.linspace(0.0, cumulative[-1], count)
    return np.column_stack([np.interp(sample_s, cumulative, points[:, axis]) for axis in (0, 1)])


def write_pleiades_eqdsk_legacy_raw(R, Z, psi, plas_currents,
                                    filename: str | Path, title: str) -> None:
    """Write the retained source contour workflow with robust geometry.

    This explicit ``legacy_raw`` entry point recovers the source workflow's
    nearest ``(0.6, 0)`` flux level, 2% vessel offset, longest contour and
    100-point limiter/vessel records.  It uses parametric arclength contour
    points so vertical/open and closed boundaries remain representable.  It
    intentionally preserves the Pleiades grid-origin convention (R starts at
    zero and Z is centred at zero); callers needing another origin must choose
    a dialect that stores that field.
    """
    R, Z, psi, plas_currents = map(np.asarray, (R, Z, psi, plas_currents))
    if (R.ndim != 2 or Z.shape != R.shape or psi.shape != R.shape or
            plas_currents.shape != R.shape or any(np.iscomplexobj(a) for a in (R, Z, psi, plas_currents)) or
            not all(np.all(np.isfinite(a)) for a in (R, Z, psi, plas_currents))):
        raise EQDSKFormatError("raw writer requires finite real arrays with one common 2-D shape")
    if R.shape[0] < 2 or R.shape[1] < 2:
        raise EQDSKFormatError("raw writer requires a rectangular grid with at least 2x2 points")
    raxis, zaxis = R[0], Z[:, 0]
    if (not np.array_equal(R, np.broadcast_to(raxis, R.shape)) or
            not np.array_equal(Z, np.broadcast_to(zaxis[:, None], Z.shape))):
        raise EQDSKFormatError("raw writer requires column-consistent R and row-consistent Z")
    data = {
        "R": R, "Z": Z, "rbox": float(np.ptp(raxis)), "zbox": float(np.ptp(zaxis)),
    }
    expected_R, expected_Z = np.meshgrid(
        np.linspace(0.0, data["rbox"], R.shape[1]),
        np.linspace(-data["zbox"] / 2.0, data["zbox"] / 2.0, R.shape[0]),
    )
    if not np.array_equal(R, expected_R) or not np.array_equal(Z, expected_Z):
        raise EQDSKFormatError("R/Z grid is not representable: raw Pleiades dialect fixes R origin at 0 and Z at +/-zbox/2")
    nearest_r = int(np.argmin(np.abs(raxis - 0.6)))
    nearest_z = int(np.argmin(np.abs(zaxis - 0.0)))
    psi_lim = float(psi[nearest_z, nearest_r])
    if not np.isfinite(psi_lim):
        raise EQDSKFormatError("raw writer could not determine finite limiter flux")
    psi_ves = psi_lim * 1.02
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    try:
        levels = sorted((psi_lim, psi_ves))
        if levels[0] == levels[1]:
            raise EQDSKFormatError("raw writer requires distinct limiter and vessel contour levels")
        contour = ax.contour(R, Z, psi, levels=levels)
        boundaries = []
        for level in (psi_lim, psi_ves):
            index = int(np.argmin(np.abs(np.asarray(contour.levels) - level)))
            segments = contour.allsegs[index]
            if not segments:
                raise EQDSKFormatError("raw writer could not find a contour at the requested level")
            segment = max(segments, key=lambda candidate: candidate.shape[0])
            boundaries.append(_resample_contour(segment, 100, (0.05, 0.5), (0.05, -0.5)))
    except EQDSKFormatError:
        raise
    except Exception as exc:
        raise EQDSKFormatError(f"raw contour construction failed: {exc}") from exc
    finally:
        plt.close(fig)
    raw_title = f"PLEIADES {title}"
    if len(raw_title) >= 26:
        raw_title = raw_title[:26]
    raw_title = raw_title.ljust(26) + "cursign,nnr,nnz,nnv = "
    nnv = 101
    total_current = float(np.sum(plas_currents))
    mapping = {
        "title": raw_title, "cursign": int(np.sign(total_current)),
        "nnr": R.shape[1], "nnz": R.shape[0], "nnv": nnv,
        "rbox": data["rbox"], "zbox": data["zbox"], "psi_lim": psi_lim,
        "Ip": total_current, "psi": psi, "R": R, "Z": Z,
        "nlim_pairs": 100, "nves_pairs": 100,
        "lim_pairs": boundaries[0], "ves_pairs": boundaries[1],
    }
    for key in _PROFILE_KEYS:
        mapping[key] = np.zeros(nnv)
    write_pleiades_eqdsk(mapping, filename)


# Keep the source spelling available only as an explicit legacy alias; the
# corrected name above is preferred in new code and in catalog documents.
write_eqdsk = write_pleiades_eqdsk_legacy_raw


# Explicit aliases preserve the useful source vocabulary while the module and
# docstrings keep the non-standard dialect visible to callers.
read_eqdsk = read_pleiades_eqdsk
write_eqdsk_fromdict = write_pleiades_eqdsk


class EQDSK(dict):
    """Mutable dictionary wrapper for the Pleiades extended EQDSK dialect."""

    dialect = DIALECT

    def __init__(self, fname: str | Path | None = None):
        super().__init__()
        if fname is not None:
            self.read_eqdsk(fname)

    def write_eqdsk(self, fname: str | Path) -> None:
        write_pleiades_eqdsk(self, fname)

    def read_eqdsk(self, fname: str | Path) -> None:
        parsed = read_pleiades_eqdsk(fname)
        self.clear()
        self.update(parsed)
