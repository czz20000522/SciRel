function fb_validate_state(s)
% Full explicit SI state. No mutation, coercion, clipping or hidden defaults.
required={'S','c2','wcs','wps2','rhocs','w','kz','vts'};
for k=1:numel(required)
 if ~isfield(s,required{k})||~isnumeric(s.(required{k}))||any(~isfinite(s.(required{k})(:)))||isempty(s.(required{k}))
  error('fluidbw:state','missing, empty or nonfinite state field');
 end
end
if ~isscalar(s.S)||s.S~=fix(s.S)||s.S<1||~isscalar(s.c2)||~isreal(s.c2)||s.c2<=0||~isscalar(s.w)||~isreal(s.w)||s.w==0||~isscalar(s.kz)||~isreal(s.kz)
 error('fluidbw:state','invalid species count, c2, real nonzero omega or real kz');
end
for name={'wcs','wps2','rhocs','vts'}
 value=s.(name{1});
 if ~isvector(value)||numel(value)~=s.S||~isreal(value)
  error('fluidbw:state','species fields must be real vectors of length S');
 end
end
if any(s.wcs==0)||any(s.rhocs==0)||any(s.wps2<=0)||any(s.vts<=0)
 error('fluidbw:state','nonzero signed gyrofrequency/radius and positive density/thermal scales required');
end
expected=s.vts(:)./(sqrt(2)*s.wcs(:));
if any(abs(s.rhocs(:)-expected)>128*eps*max(abs(expected),realmin))
 error('fluidbw:state','rho must equal vthermal/(sqrt(2)*Omega) in the isotropic Maxwellian state');
end
end
