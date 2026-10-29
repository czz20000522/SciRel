"""Finite-grid magnetic-axis and limited-boundary geometry operators.

The routines in this module intentionally operate on caller supplied typed
arrays.  They implement finite differences, polygon refinement, bilinear
boundary values and a bounded tensor-product cubic-spline ray trace; no device
constants or source-project task graph is embedded here.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "find_critical_points",
    "refine_limiter_polygon",
    "bilinear_interpolate",
    "trace_flux_boundary",
    "solve_limited_boundary",
    "solve_finite_limited_boundary",
]


def _axis(value, name):
    a = np.asarray(value, dtype=float)
    if a.ndim != 1 or a.size < 3 or not np.all(np.isfinite(a)) or not np.all(np.diff(a) > 0):
        raise ValueError(f"{name} must be a finite strictly increasing 1-D array with at least 3 entries")
    return a


def _polygon(value):
    p = np.asarray(value, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 4 or not np.all(np.isfinite(p)):
        raise ValueError("limiter must be a finite array of shape (n, 2) with at least four vertices")
    if not np.array_equal(p[0], p[-1]):
        p = np.vstack((p, p[0]))
    area = np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]) / 2.0
    if area == 0.0:
        raise ValueError("limiter polygon must have nonzero area")
    return p


def _inside(points, polygon):
    """Strict point-in-polygon test (boundary points are excluded)."""
    q = np.asarray(points, dtype=float)
    scalar = q.ndim == 1
    q = np.atleast_2d(q)
    p = polygon
    result = np.zeros(q.shape[0], dtype=bool)
    for k, point in enumerate(q):
        x, y = point
        inside = False
        for a, b in zip(p[:-1], p[1:]):
            cross = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
            on = cross == 0.0 and min(a[0], b[0]) <= x <= max(a[0], b[0]) and min(a[1], b[1]) <= y <= max(a[1], b[1])
            if on:
                inside = False
                break
            if (a[1] > y) != (b[1] > y):
                xcross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
                if x < xcross:
                    inside = not inside
        result[k] = inside
    return bool(result[0]) if scalar else result


def find_critical_points(R, Z, psi, limiter=None):
    """Return finite-difference O/X candidates as ``(R,Z,psi)`` arrays."""
    r, z = _axis(R, "R"), _axis(Z, "Z")
    f = np.asarray(psi, dtype=float)
    if f.shape != (r.size, z.size) or not np.all(np.isfinite(f)):
        raise ValueError("psi must be a finite array with shape (len(R), len(Z))")
    dr, dz = r[1] - r[0], z[1] - z[0]
    gr = (f[2:, 1:-1] - f[:-2, 1:-1]) / (2 * dr)
    gz = (f[1:-1, 2:] - f[1:-1, :-2]) / (2 * dz)
    c = gr * gr + gz * gz
    candidates = []
    for i in range(1, r.size - 1):
        for j in range(1, z.size - 1):
            ci = c[i - 1, j - 1]
            neighbors = [c[ii, jj] for ii in range(max(0, i - 2), min(c.shape[0], i + 1))
                         for jj in range(max(0, j - 2), min(c.shape[1], j + 1))
                         if (ii, jj) != (i - 1, j - 1)]
            if not np.all(ci < np.asarray(neighbors)):
                continue
            gR, gZ = gr[i - 1, j - 1], gz[i - 1, j - 1]
            hrr = (f[i + 1, j] - 2 * f[i, j] + f[i - 1, j]) / dr**2
            hzz = (f[i, j + 1] - 2 * f[i, j] + f[i, j - 1]) / dz**2
            h2rz = (f[i + 1, j + 1] + f[i - 1, j - 1] - f[i - 1, j + 1] - f[i + 1, j - 1]) / (2 * dr * dz)
            det = hrr * hzz - h2rz * h2rz / 4.0
            if det == 0.0:
                continue
            dR = -(gR * hzz - h2rz * gZ / 2.0) / det
            dZ = -(gZ * hrr - h2rz * gR / 2.0) / det
            if not (np.isfinite(dR) and np.isfinite(dZ) and abs(dR) < 1.5 * dr and abs(dZ) < 1.5 * dz):
                continue
            row = (r[i] + dR, z[j] + dZ, f[i, j] + (gR * dR + gZ * dZ) / 2.0)
            candidates.append((row, det > 0.0, i, j))
    if not candidates:
        raise ValueError("no finite critical-point candidate")
    op = [x[0] for x in candidates if x[1]]
    xp = [x[0] for x in candidates if not x[1]]
    if limiter is not None:
        poly = _polygon(limiter)
        op = [row for row in op if _inside((r[np.argmin(abs(r-row[0]))], z[np.argmin(abs(z-row[1]))]), poly)]
    if not op:
        raise ValueError("no O-point remains inside limiter")
    center = np.array([(r[0] + r[-1]) / 2, (z[0] + z[-1]) / 2])
    op.sort(key=lambda row: float(np.sum((np.asarray(row[:2]) - center) ** 2)))
    main = np.asarray(op[0])
    sign = 1.0
    xp = [row for row in xp if (row[2] - main[2]) * sign < 0.0]
    xp.sort(key=lambda row: float((row[2] - main[2]) ** 2))
    return {"opoints_RZpsi": np.asarray(op, dtype=float).reshape(-1, 3), "xpoints_RZpsi": np.asarray(xp, dtype=float).reshape(-1, 3)}


def refine_limiter_polygon(R, Z, limiter):
    """Insert axis-grid intersections into a closed limiter polygon."""
    r, z, p = _axis(R, "R"), _axis(Z, "Z"), _polygon(limiter)
    points = []
    for k, (a, b) in enumerate(zip(p[:-1], p[1:])):
        if k == 0:
            points.append(a.copy())
        d = b - a
        ts = [0.0, 1.0]
        if d[0] != 0.0:
            ts.extend((r[(r > min(a[0], b[0])) & (r < max(a[0], b[0]))] - a[0]) / d[0])
        if d[1] != 0.0:
            ts.extend((z[(z > min(a[1], b[1])) & (z < max(a[1], b[1]))] - a[1]) / d[1])
        ts = sorted(t for t in ts if 0.0 < t < 1.0)
        for t in ts:
            points.append(a + t * d)
        points.append(b.copy())
    return np.asarray(points, dtype=float)


def bilinear_interpolate(R, Z, values, points):
    """Evaluate a finite ``[R,Z]`` node field at in-domain points."""
    r, z = _axis(R, "R"), _axis(Z, "Z")
    f = np.asarray(values, dtype=float)
    if f.shape != (r.size, z.size) or not np.all(np.isfinite(f)):
        raise ValueError("values must be finite with shape (len(R), len(Z))")
    q = np.asarray(points, dtype=float)
    if q.ndim != 2 or q.shape[1] != 2 or not np.all(np.isfinite(q)):
        raise ValueError("points must be a finite array of shape (n, 2)")
    if np.any((q[:, 0] < r[0]) | (q[:, 0] > r[-1]) | (q[:, 1] < z[0]) | (q[:, 1] > z[-1])):
        raise ValueError("points must lie within the grid domain")
    i = np.clip(np.searchsorted(r, q[:, 0], side="right") - 1, 0, r.size - 2)
    j = np.clip(np.searchsorted(z, q[:, 1], side="right") - 1, 0, z.size - 2)
    a = (q[:, 0] - r[i]) / (r[i + 1] - r[i]); b = (q[:, 1] - z[j]) / (z[j + 1] - z[j])
    return (1-a)*(1-b)*f[i,j] + a*(1-b)*f[i+1,j] + (1-a)*b*f[i,j+1] + a*b*f[i+1,j+1]


def trace_flux_boundary(R, Z, psi, axis, boundary_psi, *, angle_count=80, ray_samples=1000, ray_length=10.0):
    """Trace ordered first ``q>1`` crossings with a tensor cubic spline."""
    from scipy.interpolate import RectBivariateSpline
    r, z = _axis(R, "R"), _axis(Z, "Z")
    f = np.asarray(psi, dtype=float)
    if f.shape != (r.size, z.size) or not np.all(np.isfinite(f)):
        raise ValueError("psi must be finite with shape (len(R), len(Z))")
    a = np.asarray(axis, dtype=float)
    if a.shape != (3,) or not np.all(np.isfinite(a)):
        raise ValueError("axis must be a finite (R,Z,psi) triplet")
    den = float(boundary_psi) - a[2]
    if not np.isfinite(den) or den == 0.0 or int(angle_count) < 1 or int(ray_samples) < 2:
        raise ValueError("boundary normalization and sampling controls must be finite and nondegenerate")
    spline = RectBivariateSpline(r, z, f, kx=min(3, r.size-1), ky=min(3, z.size-1), s=0)
    out = []
    for k in range(int(angle_count)):
        theta = 2.0 * np.pi * k / int(angle_count)
        r0, z0 = a[0], a[1]; r1, z1 = r0 + ray_length * np.sin(theta), z0 + ray_length * np.cos(theta)
        if abs(r1-r0) > 1e-6:
            rc = np.clip(r1, r[0], r[-1]); z1 = z0 + (z1-z0) * abs((rc-r0)/(r1-r0)); r1 = rc
        if abs(z1-z0) > 1e-6:
            zc = np.clip(z1, z[0], z[-1]); r1 = r0 + (r1-r0) * abs((zc-z0)/(z1-z0)); z1 = zc
        t = np.linspace(0.0, 1.0, int(ray_samples)); rr = r0 + t*(r1-r0); zz = z0 + t*(z1-z0)
        q = (spline.ev(rr, zz) - a[2]) / den
        hits = np.flatnonzero(q > 1.0)
        if hits.size == 0 or hits[0] == 0:
            raise ValueError(f"ray {k} has no valid strict boundary crossing")
        j = int(hits[0]); diff = q[j] - q[j-1]
        if not np.isfinite(diff) or diff == 0.0:
            raise ValueError(f"ray {k} has invalid adjacent crossing samples")
        frac = (q[j] - 1.0) / diff
        out.append(((1-frac)*rr[j] + frac*rr[j-1], (1-frac)*zz[j] + frac*zz[j-1]))
    result = np.asarray(out, dtype=float)
    return np.vstack((result, result[0]))


def solve_limited_boundary(R, Z, psi, limiter, *, angle_count=80, ray_samples=1000):
    """Compute O/X candidates, limiter contact flux and closed boundary."""
    r, z = _axis(R, "R"), _axis(Z, "Z"); f = np.asarray(psi, dtype=float); poly = _polygon(limiter)
    if np.any(poly[:, 0] <= r[0]) or np.any(poly[:, 0] >= r[-1]) or np.any(poly[:, 1] <= z[0]) or np.any(poly[:, 1] >= z[-1]):
        raise ValueError("limiter vertices must be strictly inside the grid domain")
    critical = find_critical_points(r, z, f, poly)
    refined = refine_limiter_polygon(r, z, poly)
    values = bilinear_interpolate(r, z, f, refined)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("limiter has no finite refined boundary values")
    boundary_psi = float(np.max(values))
    boundary = trace_flux_boundary(r, z, f, critical["opoints_RZpsi"][0], boundary_psi, angle_count=angle_count, ray_samples=ray_samples)
    return {**critical, "boundary_psi": boundary_psi, "closed_boundary_RZ": boundary}


def solve_finite_limited_boundary(inputs):
    """Mapping adapter for ``solve_limited_boundary``."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    try:
        return solve_limited_boundary(inputs["R"], inputs["Z"], inputs["psi"], inputs["limiter"], angle_count=inputs.get("angle_count", 80), ray_samples=inputs.get("ray_samples", 1000))
    except KeyError as exc:
        raise ValueError("inputs requires R, Z, psi and limiter") from exc
