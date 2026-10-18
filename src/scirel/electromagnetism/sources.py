"""Weighted circular-filament sources and aggregate devices."""
from __future__ import annotations
import numpy as np
from scirel.geometry import Mesh, rotate
from .greens import compute_greens


def _points(value):
    """Validate and copy a finite cylindrical ``(R, Z)`` point cloud."""
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError('rz_pts must have shape (N, 2)')
    if np.any(~np.isfinite(arr)) or np.any(arr[:, 0] < 0):
        raise ValueError('rz_pts must be finite with non-negative radius')
    return arr


def _common_current(value):
    """A source's common current is one finite scalar, in amperes."""
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 0 or not np.isfinite(arr):
        raise ValueError('current must be a finite scalar')
    return float(arr)


def _rebuild_atomic(source, changes):
    """Rebuild a parameterized source, committing only a valid complete state."""
    old = {name: getattr(source, name) for name in changes}
    old_points = source._rz_pts.copy()
    try:
        for name, value in changes.items():
            if name in ('_nr', '_nz'):
                if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) < 1:
                    raise ValueError('point count must be positive integer')
                value = int(value)
            else:
                value = float(value)
                if not np.isfinite(value):
                    raise ValueError('geometry parameters must be finite')
                if name in ('_dr', '_dz', '_width', '_height') and value <= 0:
                    raise ValueError('geometry dimensions must be positive')
                if name == '_r0' and value < 0:
                    raise ValueError('radius must be non-negative')
            setattr(source, name, value)
        source._build()
        _points(source._rz_pts)
        if hasattr(source, '_weights') and len(source._weights) != len(source._rz_pts):
            raise ValueError(
                'point count must match weights; construct a new source to resize'
            )
    except Exception:
        for name, value in old.items():
            setattr(source, name, value)
        source._rz_pts = old_points
        raise
    source._invalidate()


def _replace_points_atomic(source, points):
    """Replace a point cloud only after validating its complete state."""
    arr = _points(points)
    if hasattr(source, '_weights') and len(arr) != len(source._weights):
        raise ValueError('point count must match weights; construct a new source to resize')
    source._rz_pts = arr.copy()
    source._invalidate()

class CurrentFilamentSet:
    """Finite weighted circular filaments with a common set current."""
    def __init__(self, current=1., weights=None, mesh=None, **kwargs):
        self._mesh = None
        _points(self._rz_pts)
        self._current = float(current)
        if not np.isfinite(self._current):
            raise ValueError('current must be finite')
        self._weights = np.ones(self.npts, dtype=float) if weights is None else np.asarray(weights, dtype=float)
        if self._weights.ndim != 1 or len(self._weights) != self.npts or np.any(~np.isfinite(self._weights)):
            raise ValueError('weights must be a finite vector matching npts')
        if mesh is not None:
            self.mesh = mesh
        self._cache_key = None
        self._cache = None
    @property
    def npts(self): return len(self._rz_pts)
    @property
    def rz_pts(self): return self._rz_pts
    @rz_pts.setter
    def rz_pts(self, value):
        _replace_points_atomic(self, value)
    @property
    def weights(self): return self._weights
    @weights.setter
    def weights(self, value):
        arr = np.asarray(value, dtype=float)
        if arr.ndim != 1 or len(arr) != self.npts or np.any(~np.isfinite(arr)):
            raise ValueError('invalid weights')
        self._weights = arr.copy()
        self._invalidate()
    @property
    def current(self): return self._current
    @current.setter
    def current(self, value):
        value=float(value)
        if not np.isfinite(value): raise ValueError('current must be finite')
        self._current=value; self._invalidate()
    @property
    def total_current(self): return self.current * np.sum(self.weights)
    @total_current.setter
    def total_current(self, value):
        s=float(np.sum(self.weights))
        if not np.isfinite(s) or s == 0.: raise ValueError('cannot set total_current when weight sum is zero')
        self.current=float(value)/s; self._invalidate()
    @property
    def rzw(self): return np.column_stack((self.rz_pts, self.weights))
    @property
    def mesh(self): return self._mesh
    @mesh.setter
    def mesh(self, value):
        self._mesh = value if value is None or isinstance(value, Mesh) else Mesh.from_array(value); self._invalidate()
    def _invalidate(self): self._cache_key=None; self._cache=None
    def _mesh_points(self, mesh):
        mesh = self.mesh if mesh is None else (mesh if isinstance(mesh, Mesh) else Mesh.from_array(mesh))
        if mesh is None: raise ValueError('a mesh is required for field evaluation')
        return mesh, Mesh.to_points(mesh)
    def _key(self, mesh):
        mesh, pts = self._mesh_points(mesh)
        return (id(mesh), pts.shape, pts.tobytes(), self.rzw.tobytes())
    def _greens(self, mesh=None):
        mesh, pts = self._mesh_points(mesh); key=self._key(mesh)
        if self._cache_key != key:
            self._cache=compute_greens(self.rzw, pts)
            self._cache_key=key
        return self._cache
    def gpsi(self, mesh=None): return self._greens(mesh)[0].copy()
    def gBR(self, mesh=None): return self._greens(mesh)[1].copy()
    def gBZ(self, mesh=None): return self._greens(mesh)[2].copy()
    def psi(self, current=None, mesh=None): return _common_current(self.current if current is None else current)*self._greens(mesh)[0]
    def BR(self, current=None, mesh=None): return _common_current(self.current if current is None else current)*self._greens(mesh)[1]
    def BZ(self, current=None, mesh=None): return _common_current(self.current if current is None else current)*self._greens(mesh)[2]
    def translate(self, vector):
        delta = np.asarray(vector, dtype=float)
        if delta.shape != (2,) or np.any(~np.isfinite(delta)):
            raise ValueError('translation must contain finite (R, Z)')
        _replace_points_atomic(self, self.rz_pts + delta)
    def rotate(self, angle, pivot=(0.,0.)):
        angle = float(angle)
        pivot = np.asarray(pivot, dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or np.any(~np.isfinite(pivot)):
            raise ValueError('rotation requires a finite angle and 2-vector pivot')
        _replace_points_atomic(self, rotate(self.rz_pts, angle, pivot))
    @property
    def patch(self): return None
    def simplify(self): raise NotImplementedError('simplify is not supported for finite weighted filaments')


class ArbitraryPoints(CurrentFilamentSet):
    def __init__(self, rz_pts, **kwargs):
        self._rz_pts=np.asarray(rz_pts, dtype=float)
        if self._rz_pts.ndim != 2 or self._rz_pts.shape[1] != 2: raise ValueError('rz_pts must have shape (N, 2)')
        super().__init__(**kwargs)

class RectangularCoil(CurrentFilamentSet):
    def __init__(self, r0=1., z0=0., nr=1, nz=1, dr=.1, dz=.1, angle=0., **kwargs):
        if isinstance(nr,bool) or isinstance(nz,bool) or int(nr)!=nr or int(nz)!=nz or nr<1 or nz<1: raise ValueError('nr and nz must be positive integers')
        if not np.isfinite([r0,z0,dr,dz,angle]).all() or r0 < 0 or dr <= 0 or dz <= 0: raise ValueError('invalid coil geometry')
        self._r0,self._z0,self._nr,self._nz,self._dr,self._dz,self._angle=float(r0),float(z0),int(nr),int(nz),float(dr),float(dz),float(angle); self._build(); super().__init__(**kwargs)
    def _build(self):
        r=np.linspace(self._r0-self._dr*(self._nr-1)/2,self._r0+self._dr*(self._nr-1)/2,self._nr); z=np.linspace(self._z0-self._dz*(self._nz-1)/2,self._z0+self._dz*(self._nz-1)/2,self._nz); p=np.array([(ri,zi) for ri in r for zi in z]); self._rz_pts=rotate(p,self._angle,(self._r0,self._z0)) if self._angle else p
    npts=property(lambda s:s._nr*s._nz); r0=property(lambda s:s._r0,lambda s,v:s._set_geom('_r0',v)); z0=property(lambda s:s._z0,lambda s,v:s._set_geom('_z0',v)); nr=property(lambda s:s._nr,lambda s,v:s._set_count('_nr',v)); nz=property(lambda s:s._nz,lambda s,v:s._set_count('_nz',v)); dr=property(lambda s:s._dr,lambda s,v:s._set_positive('_dr',v)); dz=property(lambda s:s._dz,lambda s,v:s._set_positive('_dz',v)); angle=property(lambda s:s._angle,lambda s,v:s._set_geom('_angle',v)); centroid=property(lambda s:np.array([s.r0,s.z0]),lambda s,v:(setattr(s,'r0',v[0]),setattr(s,'z0',v[1])))
    def _set_geom(self,n,v):
        _rebuild_atomic(self, {n: v})
    def _set_positive(self,n,v):
        _rebuild_atomic(self, {n: v})
    def _set_count(self,n,v):
        candidate = int(v) if not isinstance(v, (bool, np.bool_)) and int(v) == v else v
        other = self._nz if n == '_nr' else self._nr
        if isinstance(candidate, (bool, np.bool_)) or not isinstance(candidate, (int, np.integer)) or candidate * other != len(self._weights):
            raise ValueError('point count changes must preserve the existing weight cardinality')
        _rebuild_atomic(self, {n: candidate})
    area=property(lambda s:s._nr*s._nz*s._dr*s._dz); current_density=property(lambda s:s.total_current/s.area)
    def _set_centroid(self, value):
        center = np.asarray(value, dtype=float)
        if center.shape != (2,) or np.any(~np.isfinite(center)):
            raise ValueError('centroid must contain finite (R, Z)')
        _rebuild_atomic(self, {'_r0': center[0], '_z0': center[1]})
    centroid=property(lambda s:np.array([s.r0,s.z0]),lambda s,v:s._set_centroid(v))
    def translate(self, vector):
        delta = np.asarray(vector, dtype=float)
        if delta.shape != (2,) or np.any(~np.isfinite(delta)):
            raise ValueError('translation must contain finite (R, Z)')
        _rebuild_atomic(self, {'_r0': self._r0 + delta[0], '_z0': self._z0 + delta[1]})
    def rotate(self, angle, pivot=(0., 0.)):
        angle = float(angle)
        pivot = np.asarray(pivot, dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or np.any(~np.isfinite(pivot)):
            raise ValueError('rotation requires a finite angle and 2-vector pivot')
        center = rotate(np.array([[self._r0, self._z0]]), angle, pivot)[0]
        _rebuild_atomic(self, {'_r0': center[0], '_z0': center[1], '_angle': self._angle + angle})

class MagnetRing(CurrentFilamentSet):
    """Construct a finite signed-filament rectangular magnet approximation.

    Parameters
    ----------
    r0 : float, default=1.0
        Center radius in metres; must be nonnegative and finite.
    z0 : float, default=0.0
        Center height in metres.
    width, height : float, default=0.01
        Positive radial and axial dimensions in metres.
    mu_hat : float, default=0.0
        Finite orientation angle in degrees.
    **kwargs
        Inherited source options such as finite common ``current``, an even
        positive ``weights`` vector, and an optional target ``mesh``.

    Returns
    -------
    MagnetRing
        A weighted circular-filament source exposing generated ``rz_pts``,
        ``total_current`` and mesh-dependent field responses.

    Raises
    ------
    ValueError
        If geometry, weights, current or mesh inputs violate their finite
        shape/domain contracts.
    FloatingPointError
        If a field evaluation produces a nonrepresentable kernel result.
    NotImplementedError
        If an unsupported source operation such as simplification is called.

    Notes
    -----
    This is a bounded signed-filament geometry approximation.  It does not
    establish experimental material constants or a magnetic constitutive law.
    Failed parameterized setters preserve the preceding valid geometry.
    """
    def __init__(self, r0=1., z0=0., width=.01, height=.01, mu_hat=0., **kwargs):
        self._r0,self._z0,self._width,self._height,self._mu_hat=map(float,(r0,z0,width,height,mu_hat))
        if r0<0 or width<=0 or height<=0 or not np.isfinite([r0,z0,width,height,mu_hat]).all(): raise ValueError('invalid magnet geometry')
        weights=kwargs.pop('weights',None)
        if weights is None: weights=np.r_[-np.ones(8),np.ones(8)]
        if len(weights)%2 or len(weights)<2: raise ValueError('weights must have an even positive length')
        self._weights=np.asarray(weights,dtype=float); self._build(); super().__init__(weights=self._weights,**kwargs)
    def _build(self):
        n=len(self._weights); h=n//2; zs=np.linspace(self._z0-self._height/2,self._z0+self._height/2,h); p=np.vstack((np.column_stack((np.full(h,self._r0-self._width/2),zs)),np.column_stack((np.full(h,self._r0+self._width/2),zs)))); self._rz_pts=rotate(p,self._mu_hat,(self._r0,self._z0)) if self._mu_hat else p
    npts=property(lambda s:len(s._weights)); r0=property(lambda s:s._r0,lambda s,v:s._set('_r0',v)); z0=property(lambda s:s._z0,lambda s,v:s._set('_z0',v)); width=property(lambda s:s._width,lambda s,v:s._set('_width',v)); height=property(lambda s:s._height,lambda s,v:s._set('_height',v)); mu_hat=property(lambda s:s._mu_hat,lambda s,v:s._set('_mu_hat',v))
    def _set(self,n,v):
        _rebuild_atomic(self, {n: v})
    def _set_centroid(self, value):
        center = np.asarray(value, dtype=float)
        if center.shape != (2,) or np.any(~np.isfinite(center)):
            raise ValueError('centroid must contain finite (R, Z)')
        _rebuild_atomic(self, {'_r0': center[0], '_z0': center[1]})
    centroid=property(lambda s:np.array([s.r0,s.z0]),lambda s,v:s._set_centroid(v))
    def translate(self, vector):
        delta=np.asarray(vector,dtype=float)
        if delta.shape != (2,) or np.any(~np.isfinite(delta)):
            raise ValueError('translation must contain finite (R, Z)')
        _rebuild_atomic(self, {'_r0': self._r0 + delta[0], '_z0': self._z0 + delta[1]})
    def rotate(self, angle, pivot=(0.,0.)):
        angle=float(angle); pivot=np.asarray(pivot,dtype=float)
        if not np.isfinite(angle) or pivot.shape != (2,) or np.any(~np.isfinite(pivot)):
            raise ValueError('rotation requires a finite angle and 2-vector pivot')
        center=rotate(np.array([[self._r0,self._z0]]),angle,pivot)[0]
        _rebuild_atomic(self, {'_r0': center[0], '_z0': center[1], '_mu_hat': self._mu_hat + angle})

class Device:
    """Ordered filament sets with linear current-vector field superposition.

    Per-source Green matrices have shape ``(Nset, Ntarget)``. A finite scalar
    override applies that common current to every set; a finite vector gives
    one current per set. Mesh assignment propagates to all registered children.
    Content-sensitive child caches supply matrices without stale parent state.
    """
    def __init__(self, mesh=None, **kwargs):
        object.__setattr__(self,'_mesh',None if mesh is None else (mesh if isinstance(mesh,Mesh) else Mesh.from_array(mesh))); object.__setattr__(self,'_current_sets',{}); object.__setattr__(self,'_cache_key',None); object.__setattr__(self,'_cache',None)
        for n,v in kwargs.items(): setattr(self,n,v)
    def __setattr__(self,name,value):
        if name not in {'_mesh','_current_sets','_cache_key','_cache'} and hasattr(self,'_current_sets'):
            if isinstance(value,CurrentFilamentSet):
                if any(child is value and registered != name for registered,child in self._current_sets.items()):
                    raise AttributeError('this current set is already registered')
                self._current_sets[name]=value
                if self.mesh is not None:
                    value.mesh=self.mesh
            elif name in self._current_sets: del self._current_sets[name]
            self._cache_key=None; self._cache=None
        object.__setattr__(self,name,value)
    def __delattr__(self,name):
        if name in self._current_sets: del self._current_sets[name]; self._cache_key=None; self._cache=None
        object.__delattr__(self,name)
    @property
    def mesh(self): return self._mesh
    @mesh.setter
    def mesh(self,value):
        target=value if value is None or isinstance(value,Mesh) else Mesh.from_array(value)
        self._mesh=target; self._cache_key=None; self._cache=None
        for source in self.current_sets: source.mesh=target
    def __iter__(self): return iter(self.current_sets)
    @property
    def current_sets(self): return list(self._current_sets.values())
    @property
    def current(self): return np.array([source.current for source in self.current_sets])
    @property
    def R(self):
        if self.mesh is None: raise ValueError('a mesh is required for coordinates')
        return self.mesh.R
    @property
    def Z(self):
        if self.mesh is None: raise ValueError('a mesh is required for coordinates')
        return self.mesh.Z
    @property
    def rzw(self): return [c.rzw for c in self.current_sets]
    def _matrix(self, name, mesh=None):
        target=self.mesh if mesh is None else mesh
        if target is None: raise ValueError('a mesh is required for field evaluation')
        if not self.current_sets: return np.zeros((0,len(Mesh.to_points(target))))
        return np.stack([getattr(source,name)(mesh=target) for source in self.current_sets])
    def gpsi(self, mesh=None): return self._matrix('gpsi',mesh)
    def gBR(self, mesh=None): return self._matrix('gBR',mesh)
    def gBZ(self, mesh=None): return self._matrix('gBZ',mesh)
    def _field(self, name, current=None, mesh=None):
        # Preserve the saved successor's positional mesh call as well as the
        # frozen FieldsOperator current-first signature. Matrix-shaped first
        # arguments are coordinate meshes; current overrides are scalar/1-D.
        if mesh is None and isinstance(current, Mesh):
            mesh, current=current,None
        elif mesh is None and current is not None and np.asarray(current).ndim >= 2:
            mesh, current=current,None
        values=np.asarray(self.current if current is None else current,dtype=float)
        if values.ndim == 0:
            values=np.full(len(self.current_sets),_common_current(values))
        if values.shape != (len(self.current_sets),) or np.any(~np.isfinite(values)):
            raise ValueError('current must be finite scalar or vector matching current_sets')
        return values @ self._matrix(name,mesh)
    def psi(self, current=None, mesh=None): return self._field('gpsi',current,mesh)
    def BR(self, current=None, mesh=None): return self._field('gBR',current,mesh)
    def BZ(self, current=None, mesh=None): return self._field('gBZ',current,mesh)

__all__=['CurrentFilamentSet','ArbitraryPoints','RectangularCoil','MagnetRing','Device']
