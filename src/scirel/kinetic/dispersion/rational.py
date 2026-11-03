"""Pure-Python rational the kinetic dispersion formulation models with explicit axis limits and diagnostics.

The operators validate units, assemble corrected descriptor forms, and qualify
finite roots. Packaged decks and coefficient JSON are read as data; no the reference solver
process or source-runtime fallback is consulted.
"""
from pathlib import Path
from dataclasses import dataclass
import json
import numpy as np
from ._rational_frequency import solve_rational_frequency
__all__ = [
    'default_deck', 'equilibrium', 'pole_table', 'point_matrix', 'solve_matrix',
    'em_coordinates', 'jpole_grid_coordinates', 'jpole_evaluate',
    'jpole_coefficients',
]
_DATA = Path(__file__).resolve().parent / '_data'
_POLE_JSON = _DATA / 'jpole12-regenerated.json'
_MODELS = ('es1d', 'es3d', 'em')
_EQ = {'es1d': ('S', 'qs', 'ms', 'ns0', 'Ts', 'vs0', 'vts', 'lambdaDs', 'kDs', 'wps'), 'es3d': ('S', 'qs', 'ms', 'ns0', 'Tzs', 'Tps', 'vs0', 'vtzs', 'lambdaDs', 'kDs', 'wps', 'wcs', 'rhocs'), 'em': ('S', 'qs0', 'ms0', 'ns0', 'Tzs0', 'Tps0', 'qs', 'ms', 'Tzs', 'Tps', 'vs0', 'vtzs', 'lambdaDs', 'kDs', 'wps', 'wcs', 'rhocs', 'wps2', 'lmdT', 'betasz', 'betasp', 'vA', 'cS', 'wci', 'wpi', 'cwp', 'vAwp', 'c2', 'epsilon0', 'mu0', 'kB')}
_IN = {'es1d': ('S', 'J', 'bzj', 'czj', 'vts', 'vs0', 'kDs', 'k'), 'es3d': ('S', 'N', 'J', 'bzj', 'czj', 'kx', 'kz', 'rhocs', 'kDs', 'wcs', 'vtzs', 'vs0', 'Tzs', 'Tps'), 'em': ('S', 'N', 'J', 'bzj', 'czj', 'kx', 'kz', 'rhocs', 'wcs', 'vtzs', 'vs0', 'lmdT', 'wps2', 'c2')}
_OUT = {'es1d': ('M', 'SJ', 'csj', 'bsj'), 'es3d': ('SNJ', 'k', 'bs', 'bs2', 'aSNJ', 'csnj', 'bsnj'), 'em': ('M', 'SNJ', 'SNJ1', 'SNJ3', 'NN', 'k', 'bs', 'bs2', 'csnj', 'b11', 'b12', 'b13', 'b21', 'b22', 'b23', 'b31', 'b32', 'b33')}

def _model(model):
    if model not in _MODELS:
        raise ValueError('unknown legacy physical model')
    return model

def _scalar(value, name, *, positive=False, nonzero=False):
    v = np.asarray(value)
    if v.shape != () or v.dtype.kind not in 'iuf' or (not np.isfinite(v)) or (positive and v <= 0) or (nonzero and v == 0):
        raise ValueError(name + ' must be finite real scalar in the physical domain')
    try:
        narrowed = float(v)
    except (OverflowError, ValueError):
        raise ValueError(name + ' not representable in float64') from None
    if not np.isfinite(narrowed) or (positive and narrowed <= 0) or (nonzero and narrowed == 0):
        raise ValueError(name + ' not representable in declared float64 domain')
    return narrowed

def _complex_scalar(value, name):
    v = np.asarray(value)
    if v.shape != () or v.dtype.kind not in 'iufc' or (not np.isfinite(v)):
        raise ValueError(name + ' must be finite numeric scalar')
    try:
        narrowed = complex(v)
    except (OverflowError, ValueError):
        raise ValueError(name + ' not representable in complex128') from None
    if not np.isfinite(narrowed):
        raise ValueError(name + ' not representable in complex128')
    return narrowed

def _integer(value, name, minimum=0):
    v = _scalar(value, name)
    if v != int(v) or v < minimum:
        raise ValueError(name + ' must be integer in the declared domain')
    return int(v)

@dataclass(frozen=True)
class _PythonReceipt:
    """Execution evidence for a deterministic in-process scientific operator."""

    backend: str
    operation: str
    dependencies: tuple[str, ...] = ('numpy', 'scipy')


def _result(state, operation):
    return {'state': state, 'receipt': _PythonReceipt('Python/NumPy', operation)}


def _row(values, dtype=None):
    array = np.asarray(values, dtype=dtype)
    return array.reshape(1, -1) if array.ndim == 1 else array


def _fixed_poles(J, *, variant='em'):
    """Return the packaged finite-pole tables without invoking a native runtime."""
    J = int(J)
    if J == 12:
        table = json.loads(_POLE_JSON.read_text(encoding='utf-8'))
        b = np.asarray(table['bzj'], dtype=float)
        c = np.asarray(table['czj'], dtype=float)
        return b[:, 0] + 1j * b[:, 1], c[:, 0] + 1j * c[:, 1]
    if J == 8:
        b = np.array([
            -1.734012457471826e-2 - 4.630639291680322e-2j,
            -7.399169923225014e-1 + 8.395179978099844e-1j,
            5.840628642184073 + 9.536009057643667e-1j,
            -5.583371525286853 - 1.120854319126599e1j,
        ])
        c = np.array([
            2.237687789201900 - 1.625940856173727j,
            1.465234126106004 - 1.789620129162444j,
            .8392539817232638 - 1.891995045765206j,
            .2739362226285564 - 1.941786875844713j,
        ])
        return np.r_[b, np.conj(b)], np.r_[c, -np.conj(c)]
    if J == 4:
        b = np.array([.546796859834032 + .037196505239277j,
                      -1.046796859834027 + 2.101852568038518j])
        c = np.array([1.23588765343592 - 1.21498213255731j,
                      -.378611612386277 - 1.350943585432730j])
        return np.r_[b, np.conj(b)], np.r_[c, -np.conj(c)]
    if variant == 'es1d' and J == 3:
        b = np.array([.1822 + .5756j, -1.3643 + 0j])
        c = np.array([-.9217 - .9091j, -1.0204j])
        return np.r_[b, np.conj(b[0])], np.r_[c, -np.conj(c[0])]
    if variant == 'es1d' and J == 2:
        b = np.array([-(.5 + .81j)])
        c = np.array([.51 - .81j])
        return np.r_[b, np.conj(b)], np.r_[c, -np.conj(c)]
    raise ValueError('unsupported pole order for selected family')


def _es1d_poles(J, opt):
    if J == 8 and opt == 2:
        b = np.array([
            -.0173401116032742 - .0463064419344598j,
            -.739917851897683 + .839518298070637j,
            5.84063227513760 + .953602843950785j,
            -5.58337431170864 - 11.2085508179677j,
        ])
        c = np.array([
            2.23768772215616 - 1.62594103256666j,
            1.46523409042510 - 1.78962030806222j,
            .839253965702731 - 1.89199521968963j,
            .273936217871668 - 1.94178704551807j,
        ])
        return np.r_[b, np.conj(b)], np.r_[c, -np.conj(c)]
    if J == 4 and opt == 1:
        b = np.array([.5468 - .0372j, -1.0468 + 2.1018j])
        c = np.array([-1.2359 - 1.2150j, -.3786 - 1.3509j])
        return np.r_[b, np.conj(b)], np.r_[c, -np.conj(c)]
    return _fixed_poles(J, variant='es1d')

def default_deck(model='es1d'):
    """Exact read-only legacy deck; callers explicitly select its unit convention."""
    name = {'es1d': 'es1d_deck.in', 'es3d': 'es3d_deck.in', 'em': 'em3d_deck.in'}[_model(model)]
    return np.loadtxt(_DATA / name, skiprows=1, ndmin=2)

def equilibrium(model, deck, *, B0=None):
    """Positive finite Maxwellian species scales; source constants explicit in output.

 ES1D q,m,n,T,v dimensionless; ES3D q,m,n,Tparallel,Tperp,v dimensionless.
 EM q/e,m/me,n[m^-3],Tparallel/perp[eV],v/c; source normalizers require two
 species. ES3D rho is absolute; EM rho signed. Zero B in magnetized models
 requires a different unmagnetized relation and is not replaced by epsilon.
 """
    model = _model(model)
    d = np.asarray(deck)
    cols = 5 if model == 'es1d' else 6
    if d.ndim != 2 or d.shape[1] != cols or len(d) < (2 if model == 'em' else 1) or (d.dtype.kind not in 'iuf') or (not np.isfinite(d).all()):
        raise ValueError('invalid physical species deck')
    if np.any(d[:, 0] == 0) or np.any(d[:, 1:4] <= 0) or (cols == 6 and np.any(d[:, 4] <= 0)):
        raise ValueError('charges must be nonzero, masses/densities/temperatures positive')
    state = {'deck': d}
    if model != 'es1d':
        state['B0'] = _scalar((1 if model == 'es3d' else 1e-07) if B0 is None else B0, 'B0', nonzero=True)
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        d = np.asarray(d, dtype=np.float64)
    if not np.isfinite(d).all() or np.any(d[:, 0] == 0) or np.any(d[:, 1:4] <= 0) or (cols == 6 and np.any(d[:, 4] <= 0)):
        raise ValueError('physical deck not representable in float64')
    state['deck'] = d
    S = d.shape[0]
    q, m, n = d[:, 0], d[:, 1], d[:, 2]
    if model == 'es1d':
        T, vd = d[:, 3], d[:, 4]
        with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
            vts = np.sqrt(2 * T / m)
            lambda_d = np.sqrt(T / (n * q * q))
            k_d = 1 / lambda_d
            wp = np.sqrt(n * q * q / m)
        result = dict(S=np.array([[S]], float), qs=_row(q), ms=_row(m), ns0=_row(n),
                      Ts=_row(T), vs0=_row(vd), vts=_row(vts), lambdaDs=_row(lambda_d),
                      kDs=_row(k_d), wps=_row(wp))
    elif model == 'es3d':
        Tz, Tp, vd = d[:, 3], d[:, 4], d[:, 5]
        B = state['B0']
        with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
            vtz = np.sqrt(2 * Tz / m)
            lambda_d = np.sqrt(Tz / (n * q * q))
            k_d = 1 / lambda_d
            wp = np.sqrt(n * q * q / m)
            wc = B * q / m
            rho = np.sqrt(Tp / m) / np.abs(wc)
        result = dict(S=np.array([[S]], float), qs=_row(q), ms=_row(m), ns0=_row(n),
                      Tzs=_row(Tz), Tps=_row(Tp), vs0=_row(vd), vtzs=_row(vtz),
                      lambdaDs=_row(lambda_d), kDs=_row(k_d), wps=_row(wp),
                      wcs=_row(wc), rhocs=_row(rho))
    else:
        qe, me, c, eps0, kb = 1.6022e-19, 9.1094e-31, 2.9979e8, 8.8542e-12, 1.3807e-23
        Tz0, Tp0, vd0 = d[:, 3], d[:, 4], d[:, 5]
        qs, ms = q * qe, m * me
        Tz, Tp, vd = Tz0 * qe / kb, Tp0 * qe / kb, vd0 * c
        c2, mu0 = c * c, 1 / (c * c * eps0)
        B = state['B0']
        with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
            vtz = np.sqrt(2 * kb * Tz / ms)
            lambda_d = np.sqrt(eps0 * kb * Tz / (n * qs * qs))
            k_d = 1 / lambda_d
            wp = np.sqrt(n * qs * qs / (ms * eps0))
            wc = B * qs / ms
            rho = np.sqrt(kb * Tp / ms) / wc
            wpi = np.sqrt(n[0] * qs[1] ** 2 / (ms[1] * eps0))
            cwp = c / wpi
            vA = B / np.sqrt(mu0 * np.sum(ms * n))
            cS = np.sqrt(2 * np.min(kb * Tz) / np.max(ms))
        result = dict(S=np.array([[S]], float), qs0=_row(q), ms0=_row(m), ns0=_row(n),
                      Tzs0=_row(Tz0), Tps0=_row(Tp0), qs=_row(qs), ms=_row(ms),
                      Tzs=_row(Tz), Tps=_row(Tp), vs0=_row(vd), vtzs=_row(vtz),
                      lambdaDs=_row(lambda_d), kDs=_row(k_d), wps=_row(wp), wcs=_row(wc),
                      rhocs=_row(rho), wps2=_row(wp * wp), lmdT=_row(Tz / Tp),
                      betasz=_row(2 * mu0 * kb * n * Tz / B ** 2),
                      betasp=_row(2 * mu0 * kb * n * Tp / B ** 2), vA=np.array([[vA]]),
                      cS=np.array([[cS]]), wci=np.array([[abs(wc[1])]]),
                      wpi=np.array([[wpi]]), cwp=np.array([[cwp]]),
                      vAwp=np.array([[vA / abs(wc[1])]]), c2=np.array([[c2]]),
                      epsilon0=np.array([[eps0]]), mu0=np.array([[mu0]]),
                      kB=np.array([[kb]]))
    if not all(np.isfinite(np.asarray(v)).all() for v in result.values()):
        raise FloatingPointError('derived equilibrium is not representable')
    return _result(result, model + '_equilibrium')

def pole_table(model='es1d', J=8, *, opt=None):
    """Explicit source-family pole data; no silent fallback to a different order.

 ES1D J2,3,4,8,12; ES3D/EM J4,8,12. opt=1/2 distinguishes ES1D J4/J8
 source tables. Table choice is approximation metadata, not a global accuracy
 claim. General upper/lower-plane error domains still require qualification.
 """
    model = _model(model)
    J = _integer(J, 'J', 1)
    if J not in ((2, 3, 4, 8, 12) if model == 'es1d' else (4, 8, 12)):
        raise ValueError('unsupported pole order for selected family')
    p = {'J': J}
    if model == 'es1d':
        opt = (2 if J == 4 else 1) if opt is None else _integer(opt, 'opt', 1)
        if opt not in (1, 2):
            raise ValueError('opt must select table1 or2')
        p['opt'] = opt
    if model == 'es1d':
        bzj, czj = _es1d_poles(J, opt)
    else:
        bzj, czj = _fixed_poles(J, variant=model)
    return _result({'J': np.array([[J]], float), 'bzj': _row(bzj), 'czj': _row(czj)}, model + '_poles')

def point_matrix(model, state, *, k=None, kx=None, kz=None, N=None):
    """Build model-specific eigenmatrix or corrected Harris descriptor coefficients.

 ES3D deliberately does not expose the source's incorrect ordinary matrix M.
 Exact parallel Bessel limits and a separate exact-perpendicular full-I pole
 pencil retain both axes. Signed wavevectors select the causal pole sheet.
 Signed and exact-axis responses have bounded independent qualification;
 installed public contracts are checked separately.
 """
    model = _model(model)
    s = dict(state)
    if model == 'es1d':
        s['k'] = _scalar(k, 'k', nonzero=True)
    else:
        s['kx'] = _scalar(kx, 'kx')
        s['kz'] = _scalar(kz, 'kz')
        s['N'] = _integer((10 if model == 'es3d' else 2) if N is None else N, 'N')
        if model == 'es3d' and s['kx'] == 0 and (s['kz'] == 0):
            raise ValueError('zero ES wavevector requires separate longitudinal limit')
    direction = s['k'] if model == 'es1d' else s['kz']
    if direction < 0:
        s['czj'] = -np.asarray(s['czj'])
    if model == 'em' and s['kz'] == 0:
        from ._perpendicular_em import perpendicular_maxwell_pencil
        gyro = np.asarray(s['wcs']).ravel()
        vtz = np.asarray(s['vtzs']).ravel()
        rho = np.asarray(s['rhocs']).ravel()
        wp2 = np.asarray(s['wps2']).ravel()
        vd = np.asarray(s['vs0']).ravel()
        components = [dict(gyro=g, wp2=p, vtz=z, vtp=np.sqrt(2) * abs(g * r), drift=v, weight=1.0) for (g, p, z, r, v) in zip(gyro, wp2, vtz, rho, vd)]
        p = perpendicular_maxwell_pencil(components=components, kx=s['kx'], N=s['N'], c2=float(np.asarray(s['c2']).item()))
        na = p['M'].shape[0] - 6
        p.update(NN=p['M'].shape[0], SNJ3=na, SNJ1=na // 3, SNJ=na // 3 - 1, k=abs(s['kx']), kz=0.0, kx=s['kx'], representation='analytic uniform cold pole pencil' if s['kx'] == 0 else 'exact perpendicular full-I Gaussian pole pencil', source_auxiliary_capacity=3 * (int(np.asarray(s['S']).item()) * (2 * s['N'] + 1) * int(np.asarray(s['J']).item()) + 1), source_auxiliary_aliases='not certified as physical waves; compressed pole representation retains E/B observables')
        return {'state': p, 'receipt': {'backend': 'Python scaled-Bessel pole pencil', 'source_axis_repair_sha256': 'e5f28e534ff231ceb8a1fa3b234e2c4006cb34a8c5a00b6e50943d1ba329b532', 'causal_sheet': 1}}
    from scipy import sparse
    from scipy.special import ive

    bzj = np.asarray(s['bzj'], complex).ravel()
    czj = np.asarray(s['czj'], complex).ravel()
    S = int(np.asarray(s['S']).item())
    J = int(np.asarray(s['J']).item())
    if model == 'es1d':
        vts = np.asarray(s['vts']).ravel()
        vd = np.asarray(s['vs0']).ravel()
        kd = np.asarray(s['kDs']).ravel()
        csj = np.concatenate([s['k'] * (czj * vts[i] + vd[i]) for i in range(S)])
        bsj = np.concatenate([vts[i] * bzj * czj * (kd[i] ** 2 / s['k']) for i in range(S)])
        M = np.broadcast_to(-bsj, (len(bsj), len(bsj))).copy()
        np.fill_diagonal(M, np.diag(M) + csj)
        return _result({'M': M, 'SJ': np.array([[S * J]], float),
                        'csj': _row(csj), 'bsj': _row(bsj),
                        'causal_sheet': -1 if direction < 0 else 1}, 'es1d_matrix')

    kx_value, kz_value = s['kx'], s['kz']
    k_value = float(np.hypot(kx_value, kz_value))
    if model == 'es3d':
        tz = np.asarray(s['Tzs']).ravel()
        tp = np.asarray(s['Tps']).ravel()
        vd = np.asarray(s['vs0']).ravel()
        wc = np.asarray(s['wcs']).ravel()
        rho = np.asarray(s['rhocs']).ravel()
        kd = np.asarray(s['kDs']).ravel()
        bs = kx_value * rho
        bs2 = bs * bs
        csnj, bsnj = [], []
        a = 1.0
        for i in range(S):
            a += kd[i] ** 2 / k_value ** 2
            for n in range(-s['N'], s['N'] + 1):
                gamma = float(ive(n, bs2[i]))
                for j in range(J):
                    tmp = n * wc[i] + czj[j] * kz_value * np.sqrt(2 * tz[i] / np.asarray(s['ms']).ravel()[i])
                    csnj.append(kz_value * vd[i] + tmp)
                    bsnj.append((kd[i] ** 2 / k_value ** 2) * gamma * bzj[j] *
                                (tmp - (1 - tz[i] / tp[i]) * n * wc[i]))
                    a += (kd[i] ** 2 / k_value ** 2) * gamma * bzj[j]
        csnj, bsnj = np.asarray(csnj), np.asarray(bsnj)
        out = {'SNJ': np.array([[len(csnj)]], float), 'k': np.array([[k_value]]),
               'bs': _row(bs), 'bs2': _row(bs2), 'aSNJ': np.array([[a]], complex),
               'csnj': _row(csnj), 'bsnj': _row(bsnj),
               'constant': complex(a), 'poles': csnj.copy(), 'residues': bsnj.copy(),
               'causal_sheet': -1 if direction < 0 else 1}
        if kz_value == 0:
            out['perpendicular_inputs'] = {'alpha': (kd / abs(kx_value)) ** 2,
                'rho': rho, 'gyro': wc, 'temperature_ratio': tz / tp,
                'kx': kx_value, 'N': s['N'], 'source_pole_order': J}
        return _result(out, 'es3d_matrix')

    # EM oblique Maxwell pencil. Exact perpendicular and zero-k limits are
    # handled by the maintained pure-Python assemblers above.
    tz = np.asarray(s['vtzs']).ravel()
    vd = np.asarray(s['vs0']).ravel()
    wc = np.asarray(s['wcs']).ravel()
    rho = np.asarray(s['rhocs']).ravel()
    wp2 = np.asarray(s['wps2']).ravel()
    lmd = np.asarray(s['lmdT']).ravel()
    c2 = float(np.asarray(s['c2']).item())
    SNJ = S * (2 * s['N'] + 1) * J
    SNJ1, SNJ3, NN = SNJ + 1, 3 * (SNJ + 1), 3 * (SNJ + 1) + 6
    M = sparse.lil_matrix((NN, NN), dtype=complex)
    csnj = np.zeros(SNJ, complex)
    b11s = np.zeros(SNJ, complex); b12s = np.zeros(SNJ, complex); b13s = np.zeros(SNJ, complex)
    b21s = np.zeros(SNJ, complex); b22s = np.zeros(SNJ, complex); b23s = np.zeros(SNJ, complex)
    b31s = np.zeros(SNJ, complex); b32s = np.zeros(SNJ, complex); b33s = np.zeros(SNJ, complex)
    b11 = b12 = b13 = b21 = b22 = b23 = b31 = b32 = b33 = 0j
    bs = kx_value * rho; bs2 = bs * bs
    index = 0
    for i in range(S):
        for n in range(-s['N'], s['N'] + 1):
            for j in range(J):
                gamma = float(ive(n, bs2[i]))
                derivative = (float(ive(n + 1, bs2[i])) + float(ive(n - 1, bs2[i])) - 2 * gamma) / 2
                if bs2[i] == 0:
                    n2g = (0.5 if abs(n) == 1 else 0.0)
                    ng = (n * bs[i] / 2 if abs(n) == 1 else 0.0)
                else:
                    n2g = n * n * gamma / bs2[i]
                    ng = n * gamma / bs[i]
                cnj = czj[j] * kz_value * tz[i] + kz_value * vd[i] + n * wc[i]
                csnj[index] = cnj
                bj0 = vd[i] + (1 - 1 / lmd[i]) * czj[j] * tz[i]
                bnj1 = bj0 / (czj[j] * tz[i] + vd[i]) if n == 0 else kz_value * bj0 / cnj
                bnj2 = 1 - bnj1; tmp = wp2[i] * bzj[j]
                b11s[index] = tmp * bnj2 * n2g; b11 += tmp * bnj1 * n2g
                b12s[index] = tmp * bnj2 * 1j * n * derivative; b12 += tmp * bnj1 * 1j * n * derivative
                b21s[index] = -b12s[index]; b21 = -b12
                b22s[index] = tmp * bnj2 * (n2g - 2 * bs2[i] * derivative); b22 += tmp * bnj1 * (n2g - 2 * bs2[i] * derivative)
                bnj1 = 0 if n == 0 else n * wc[i] * bj0 / cnj / tz[i]
                bnj2 = czj[j] / lmd[i] + bnj1
                b13s[index] = tmp * bnj2 * np.sqrt(2 * lmd[i]) * ng; b13 -= tmp * bnj1 * np.sqrt(2 * lmd[i]) * ng
                b31s[index] = b13s[index]; b31 = b13
                b23s[index] = -1j * tmp * bnj2 * np.sqrt(2 * lmd[i]) * derivative * bs[i]; b23 += 1j * tmp * bnj1 * np.sqrt(2 * lmd[i]) * derivative * bs[i]
                b32s[index] = -b23s[index]; b32 = -b23
                if bj0 == 0:
                    bnj1, bnj2 = 0, czj[j] ** 2
                else:
                    bnj1 = n * n * wc[i] ** 2 * bj0 / cnj / tz[i] ** 2 / kz_value
                    bnj2 = (vd[i] / tz[i] + czj[j]) * czj[j] / lmd[i] + n * wc[i] * bj0 * (1 - n * wc[i] / cnj) / tz[i] ** 2 / kz_value
                b33s[index] = tmp * bnj2 * 2 * lmd[i] * gamma; b33 += tmp * bnj1 * 2 * lmd[i] * gamma
                index += 1
    field = SNJ3
    for q in range(SNJ1):
        M[field, q] = -1; M[field + 1, SNJ1 + q] = -1; M[field + 2, 2 * SNJ1 + q] = -1
    for idx in range(SNJ):
        jx, jy, jz = idx, SNJ1 + idx, 2 * SNJ1 + idx
        M[jx, jx] = M[jy, jy] = M[jz, jz] = csnj[idx]
        M[jx, field:field + 3] = [b11s[idx], b12s[idx], b13s[idx]]
        M[jy, field:field + 3] = [b21s[idx], b22s[idx], b23s[idx]]
        M[jz, field:field + 3] = [b31s[idx], b32s[idx], b33s[idx]]
    M[SNJ1 - 1, field:field + 3] = [b11, b12, b13]
    M[2 * SNJ1 - 1, field:field + 3] = [b21, b22, b23]
    M[3 * SNJ1 - 1, field:field + 3] = [b31, b32, b33]
    M[field, field + 4] = c2 * kz_value; M[field + 1, field + 3] = -c2 * kz_value; M[field + 1, field + 5] = c2 * kx_value; M[field + 2, field + 4] = -c2 * kx_value
    M[field + 3, field + 1] = -kz_value; M[field + 4, field] = kz_value; M[field + 4, field + 2] = -kx_value; M[field + 5, field + 1] = kx_value
    if direction < 0:
        signs = np.ones(NN); signs[2 * SNJ1:SNJ3] = -1; signs[field + 2] = -1; signs[field + 3:field + 5] = -1
        M = sparse.diags(signs) @ M.tocsc() @ sparse.diags(signs)
        b13, b31, b23, b32 = -b13, -b31, -b23, -b32
        b13s, b31s, b23s, b32s = -b13s, -b31s, -b23s, -b32s
    out = {'M': M.tocsc(), 'SNJ': np.array([[SNJ]], float), 'SNJ1': np.array([[SNJ1]], float),
           'SNJ3': np.array([[SNJ3]], float), 'NN': np.array([[NN]], float), 'k': np.array([[k_value]]),
           'bs': _row(bs), 'bs2': _row(bs2), 'csnj': _row(csnj),
           'b11': np.array([[b11]]), 'b12': np.array([[b12]]), 'b13': np.array([[b13]]),
           'b21': np.array([[b21]]), 'b22': np.array([[b22]]), 'b23': np.array([[b23]]),
           'b31': np.array([[b31]]), 'b32': np.array([[b32]]), 'b33': np.array([[b33]]),
           'b11snj': _row(b11s), 'b12snj': _row(b12s), 'b13snj': _row(b13s),
           'b21snj': _row(b21s), 'b22snj': _row(b22s), 'b23snj': _row(b23s),
           'b31snj': _row(b31s), 'b32snj': _row(b32s), 'b33snj': _row(b33s),
           'causal_sheet': -1 if direction < 0 else 1}
    return _result(out, 'em_matrix')

def solve_matrix(matrix, *, model='es1d', sp=0, nw=None, wg=0):
    """Frequency solve with full eigenvectors/backward residual and explicit shift.

 EM is binary64 eig/eigs, avoiding the source's post-eig VPA conversion which
 does not improve eigenvalue accuracy. This intentional dependency change is
 not a claim of identical incidental LAPACK root order. Physical roots require
 independent dielectric checks as well as a backward-stable matrix solve.
 """
    model = _model(model)
    if model == 'es3d':
        if 'perpendicular_inputs' in matrix:
            from ._harris_perpendicular import solve_perpendicular_harris
            return solve_perpendicular_harris(**matrix['perpendicular_inputs'])
        r = solve_rational_frequency(constant=matrix['constant'], poles=matrix['poles'], residues=matrix['residues'])
        if 'accepted' in r and (not np.all(r['accepted'])):
            error = ArithmeticError('unqualified finite descriptor modes; inspect attached diagnostics')
            error.diagnostics = r
            raise error
        return r
    is_sparse = any((cls.__module__.startswith('scipy.sparse.') for cls in type(matrix).__mro__))
    M = matrix if is_sparse else np.asarray(matrix, dtype=complex)
    finite_values = M.data if is_sparse else M
    if len(M.shape) != 2 or M.shape[0] != M.shape[1] or M.shape[0] == 0 or (not np.isfinite(finite_values).all()):
        raise ValueError('finite square frequency matrix required')
    sp = _integer(sp, 'sp')
    if sp not in (0, 1):
        raise ValueError('sp must be dense0 or shifted sparse1')
    if sp:
        count = _integer(1 if nw is None else nw, 'nw', 1)
        if count >= M.shape[0] - 1:
            raise ValueError('sparse eigs requires nw<dimension-1')
        shift = _complex_scalar(wg, 'wg')
        if not np.isfinite(shift):
            raise ValueError('finite frequency shift required')
    from scipy import sparse
    from scipy.linalg import eig
    from scipy.sparse.linalg import eigs
    if sp:
        (d, V) = eigs(sparse.csc_matrix(M), k=count, sigma=shift)
    else:
        (d, V) = eig(M.toarray() if is_sparse else M)
    norm = sparse.linalg.norm(M) if is_sparse else np.linalg.norm(M)
    residual = np.linalg.norm(M @ V - V * d, axis=0) / ((norm + abs(d)) * np.linalg.norm(V, axis=0))
    if not np.isfinite(d).all() or not np.isfinite(residual).all() or np.any(residual > max(1e-11, 128 * len(d) * np.finfo(float).eps)):
        raise ArithmeticError('frequency eigensolver failed backward residual gate')
    order = np.argsort(-d.imag, kind='stable')
    w = d[order]
    return dict(d=d, omega=d, V=V, w=w, wi=w.imag, ind=order, indices='zero-based', backward_residual=residual, wg=w[0])

def em_coordinates(kj, cwp, *, theta_degrees=71):
    """Explicit legacy kc/omega_pi and degrees to SI wavevector components."""
    k = _scalar(kj, 'kj') / _scalar(cwp, 'cwp', positive=True)
    theta = np.deg2rad(_scalar(theta_degrees, 'theta_degrees'))
    return dict(kx=k * np.sin(theta), kz=k * np.cos(theta), theta=theta, k=k)

def ordered_spectrum(model='es1d', deck=None, *, J=8, opt=None, N=None, B0=None, points=None, sp=0, wg0=1.5):
    """Corrected numeric graph; explicit point axes and per-point spectra/state.

 Defaults retain source sampling grids: ES1D .4:-.02:.01; ES3D kx .05:.1:5
 with kz=0; EM kc/omega_pi .01:.02:1 at71 degrees. EM shift starts wg0*wci
 and follows input order. Physical descriptor root counts may vary; no padding.
 """
    model = _model(model)
    eq = equilibrium(model, default_deck(model) if deck is None else deck, B0=B0)
    tab = pole_table(model, J, opt=opt)
    s = {**eq['state'], **tab['state']}
    if points is None:
        grids = {
            'es1d_grid': np.arange(20, 0, -1, dtype=float) * 0.02,
            'es3d_grid': np.arange(50, dtype=float) * 0.1 + 0.05,
            'em_grid': np.arange(50, dtype=float) * 0.02 + 0.01,
        }
        if model == 'es1d':
            points = [(k,) for k in np.asarray(grids['es1d_grid']).ravel()]
        elif model == 'es3d':
            points = [(k, 0.0) for k in np.asarray(grids['es3d_grid']).ravel()]
        else:
            points = [(em_coordinates(k, float(np.asarray(s['cwp']).item()))['kx'], em_coordinates(k, float(np.asarray(s['cwp']).item()))['kz']) for k in np.asarray(grids['em_grid']).ravel()]
    points = [tuple(p) for p in points]
    spectra = []
    guess = _complex_scalar(wg0, 'wg0') * float(np.asarray(s['wci']).item()) if model == 'em' else 0
    for p in points:
        r = point_matrix(model, s, **{'k': p[0]} if model == 'es1d' else {'kx': p[0], 'kz': p[1], 'N': N})
        solved = solve_matrix(r['state'] if model == 'es3d' else r['state']['M'], model=model, sp=sp, wg=guess)
        if model == 'em':
            guess = solved['wg']
        spectra.append({'matrix': r, 'solution': solved})
    return dict(model=model, points=np.asarray(points), equilibrium=eq, pole_table=tab, spectra=spectra, wg=guess, mode_axis='per-point explicit spectrum')

def jpole_grid_coordinates():
    """Source diagnostic grid; this is not an approximation-validity declaration."""
    x = np.linspace(-5, 5, 101)
    y = np.linspace(-3, 5, 101)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    return _result({'x': xx, 'y': yy, 'z': xx + 1j * yy}, 'jpole_coordinates')

def jpole_evaluate(bzj, czj, z):
    """Evaluate a simple-pole rational approximation, preserving the z shape."""
    b = np.asarray(bzj, dtype=complex).ravel()
    c = np.asarray(czj, dtype=complex).ravel()
    z = np.asarray(z, dtype=complex)
    if len(b) == 0 or b.shape != c.shape or (not all((np.isfinite(v).all() for v in (b, c, z)))):
        raise ValueError('finite aligned pole data and evaluation points required')
    if np.any(z[..., None] == c):
        raise ZeroDivisionError('evaluation at a rational pole')
    out = (b / (z[..., None] - c)).sum(axis=-1)
    if not np.isfinite(out).all():
        raise FloatingPointError('rational evaluation not representable')
    return {'ZJ': out}

def jpole_coefficients(J=12, I=16, *, precision=80):
    """High-precision two-sided Maxwellian Padé construction, pending refinement.

 Original J12 system condition~3.52e14 motivates explicit precision. No claim
 of universal Z accuracy or monotonic improvement. Residues assume simple roots;
 a repeated root requires a separate higher-order-pole representation.
 """
    from ._pade import construct_maxwellian_pade
    return construct_maxwellian_pade(J=J, I=I, precision=precision)

def jpole_generator(J=12, I=16, *, precision=80):
    """Composition of coefficient construction and historical diagnostic grid."""
    p = jpole_coefficients(J, I, precision=precision)
    g = jpole_grid_coordinates()['state']
    return {**p, **g, **jpole_evaluate(p['bzj'], p['czj'], g['z'])}

