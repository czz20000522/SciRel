function [DD,K,D]=fb_tensor(kx,state,lmx)
% D2 stable finite-harmonic Maxwellian tensor, exp(i k.x-i omega t).
% Source: frozen fD/fDtensor; fixes removable kx=0, signed/zero kz,
% and finite-cutoff misuse of infinite Gamma identities in Kzz and Kyz.
% Each truncated contribution is formed after exact symmetric/infinite-sum
% cancellation. This intentionally differs from the defective finite source.
% lmx is an approximation control, not a proof of kinetic mode completeness.
fb_validate_state(state); s=state;
if ~isscalar(kx)||~isfinite(kx)||~isscalar(lmx)||lmx~=fix(lmx)||lmx<1||lmx>4096
  error('fluidbw:domain','finite scalar kx and integer lmx in 1..4096 required');
end
K=eye(3); w=s.w; kp=abs(s.kz); reflection=sign(s.kz);
for j=1:s.S
  a=kx*s.rhocs(j); b=a^2; n=(-lmx:lmx).';
  g=Gamman(n,b); gp=Gammapn(n,b);
  if b==0
    xx=double(abs(n)==1)/2; na=zeros(size(n));
  else
    xx=n.^2.*g/b; na=n.*g/a;
  end
  xy=1i*n.*gp; yy=xx-2*b*gp; delta=w-n*s.wcs(j);
  weight=s.wps2(j)/w^2;
  if kp==0
    active=(abs(xx)+abs(xy)+abs(yy)+abs(g))>0;
    if any(delta(active)==0), error('fluidbw:pole','zero-kz cyclotron resonance has no finite tensor'); end
    p=zeros(size(delta)); p(active)=-w./delta(active);
    K(1,1)=K(1,1)+weight*sum(p.*xx);
    K(1,2)=K(1,2)+weight*sum(p.*xy);
    K(2,2)=K(2,2)+weight*sum(p.*yy);
    K(3,3)=K(3,3)+weight*sum(p.*g);
  else
    z0=w/(kp*s.vts(j)); z=delta/(kp*s.vts(j));
    [Z,Q]=fb_z_stable(z);
    p=z0*Z;
    K(1,1)=K(1,1)+weight*sum(p.*xx);
    K(1,2)=K(1,2)+weight*sum(p.*xy);
    K(2,2)=K(2,2)+weight*sum(p.*yy);
    K(1,3)=K(1,3)+weight*sum(sqrt(2)*reflection*z0*Q.*na);
    K(2,3)=K(2,3)+weight*sum(-1i*sqrt(2)*reflection*z0*Q*a.*gp);
    K(3,3)=K(3,3)+weight*sum(2*z0*z.*Q.*g);
  end
end
K(2,1)=-K(1,2); K(3,1)=K(1,3); K(3,2)=-K(2,3);
nx=sqrt(s.c2)*kx/w; nz=sqrt(s.c2)*s.kz/w;
D=K+[ -nz^2,0,nx*nz;0,-nx^2-nz^2,0;nx*nz,0,-nx^2]; DD=det(D);
if any(~isfinite(K(:)))||any(~isfinite(D(:)))||~isfinite(DD)
 error('fluidbw:precision','tensor or determinant is not representable');
end
end
