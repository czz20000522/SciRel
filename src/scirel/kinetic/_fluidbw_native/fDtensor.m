function [DD,Kxx,Kxy,Kxz,Kyx,Kyy,Kyz,Kzx,Kzy,Kzz]=fDtensor(B0,qs,ms,ns0,Ts0,f,kz,kx)
% Frozen SI ports; D2 removes kx/kz zero singularities with analytic limits.
if ~isscalar(B0)||~isreal(B0)||~isfinite(B0)||B0==0||~isscalar(f)||~isreal(f)||~isfinite(f)||f==0
 error('fluidbw:domain','finite nonzero real B0 and f required');
end
S=numel(qs);
for a={qs,ms,ns0,Ts0}
 if ~isvector(a{1})||numel(a{1})~=S||~isreal(a{1})||any(~isfinite(a{1}))
  error('fluidbw:domain','matched finite real species vectors required');
 end
end
if S==0||any(qs==0)||any(ms<=0)||any(ns0<=0)||any(Ts0<=0)
 error('fluidbw:domain','positive mass, density, Kelvin temperature; nonzero charge required');
end
kB=1.38064852e-23; eps0=8.854187817e-12;
s=struct('S',S,'c2',2.99792458e8^2,'wcs',qs*B0./ms,'wps2',ns0.*qs.^2./ms/eps0,'rhocs',sqrt(kB*Ts0./ms)./(qs*B0./ms),'vts',sqrt(2*kB*Ts0./ms),'w',2*pi*f,'kz',kz);
[DD,K]=fb_tensor(kx,s,15);
Kxx=K(1,1);Kxy=K(1,2);Kxz=K(1,3);Kyx=K(2,1);Kyy=K(2,2);Kyz=K(2,3);Kzx=K(3,1);Kzy=K(3,2);Kzz=K(3,3);
end
