function [RC,diagnostics]=fb_r_harmonic(Y,b)
% D2 successor of RTAY/RASY/RINT/RYLA, frozen D1 1a6704a7.
% R=2Y/b sum_{n>=1} n^2 Gamma_n(b)/(Y^2-n^2).
% RC=[R, d(bR)/db; Y*dR/dY, Y*d/dY(d(bR)/db)].
% The original branch approximations, not the relation, are replaced. In
% particular the second column is NOT dR/db. Complex b uses exp(-b)*I_n(b).
% Independent integral derivation and failure observations are bound in D2.
if ~isscalar(Y)||~isscalar(b)||~isfinite(Y)||~isfinite(b)
  error('fluidbw:domain','Y and b must be finite scalars');
end
Y=double(Y); b=double(b);
if b==0
  if Y^2==1, error('fluidbw:pole','Y=+/-1 is a genuine pole at b=0'); end
  RC=[Y/(Y^2-1),Y/(Y^2-1);-Y*(Y^2+1)/(Y^2-1)^2,-Y*(Y^2+1)/(Y^2-1)^2];
  diagnostics=struct('terms',0,'roundoff_estimate',0,'tail_bound',0); return;
end
if Y==0, RC=zeros(2); diagnostics=struct('terms',0,'roundoff_estimate',0,'tail_bound',0); return; end
if isreal(Y)&&Y==fix(Y)
  error('fluidbw:pole','nonzero integer Y is a cyclotron harmonic pole');
end
% Absolute Bessel-series majorant:
% |Gamma_n(b)| <= exp(-Re b)*(|b|/2)^n/n!*exp(|b|^2/(4(n+1))).
% For n>2|Y|, denominators bound by 3n^2/4; successive
% majorants have ratio <= |b|/(2(n+1)). Include neighbor terms for Gamma'.
a=abs(b); N=max(32,ceil(2*abs(Y)+2));
while true
  if N>65536, error('fluidbw:precision','harmonic tail cannot be bounded within 65536 terms'); end
  logB=-real(b)+N*log(a/2)-gammaln(N+1)+a^2/(4*(N+1));
  q=a/(2*(N+1));
  if q<0.5 && logB < log(1e-15/(64*(1+abs(Y))*(1+1/a)))
    break;
  end
  N=2*N;
  if N>65536, error('fluidbw:precision','harmonic tail cannot be bounded within 65536 terms'); end
end
n=(1:N).'; g=Gamman(n,b); gp=Gammapn(n,b);
den=Y^2-n.^2;
c=2*Y*n.^2./den; cy=-2*Y*n.^2.*(Y^2+n.^2)./den.^2;
terms=[c.*g/b,c.*gp,cy.*g/b,cy.*gp];
v=sum(terms,1); sumabs=sum(abs(terms),1);
gammaN=N*eps/(1-N*eps);
roundoff=(gammaN+32*eps)*sumabs; % sum roundoff plus term-evaluation estimate
tail=64*(1+abs(Y))*(1+1/a)*exp(logB)/(1-q);
if any(~isfinite(v))||any(roundoff+tail>1e-10*(1+abs(v)))
  error('fluidbw:precision','harmonic cancellation or overflow prevents the declared accuracy');
end
RC=[v(1),v(2);v(3),v(4)];
diagnostics=struct('terms',N,'roundoff_estimate',max(roundoff),'tail_bound',tail);
end
