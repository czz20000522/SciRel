function [cn,ledger]=fb_normalize_poles(raw)
% D2 scientific fit repair, not a reinterpretation of raw decimal coefficients.
% For n>=1 Gamma_n(k^2 rho^2) must vanish at least quadratically at k=0.
% Project residues in real conjugate-pair coordinates onto inverse moments
% sum(r/p)=sum(r/p^2)=0, preserving sum(r) and sum(r*p) (large-z moments).
% Poles and array order are unchanged; raw tables remain separately available.
% All constitutive components use this same corrected finite rational model.
cn=raw; ledger=cell(size(raw));
for n=2:numel(raw)
 p=raw{n}.pl(:); r=raw{n}.rl(:); h=numel(p)/2;
 if any(p(2:2:end)~=conj(p(1:2:end)))
  error('fluidbw:table','source conjugate pole pairing is inconsistent'); end
 q=p(1:2:end); paired=(r(1:2:end)+conj(r(2:2:end)))/2;
 u=[real(paired);imag(paired)];
 C=[2*real(1./q).',-2*imag(1./q).';2*real(1./q.^2).',-2*imag(1./q.^2).';...
    2*ones(1,h),zeros(1,h);2*real(q).',-2*imag(q).'];
 target=[0;0;real(sum(r));real(sum(r.*p))];
 u=u-pinv(C)*(C*u-target);
 rr=zeros(size(r)); rr(1:2:end)=u(1:h)+1i*u(h+1:end); rr(2:2:end)=conj(rr(1:2:end));
 cn{n}.rl=reshape(rr,size(raw{n}.rl));
 ledger{n}=struct('harmonic',n-1,'residue_change_max',max(abs(rr-r)),...
   'inverse_moments_before',[sum(r./p),sum(r./p.^2)],...
   'inverse_moments_after',[sum(rr./p),sum(rr./p.^2)],...
   'large_z_moment_changes',[sum(rr)-sum(r),sum(rr.*p)-sum(r.*p)]);
end
end
