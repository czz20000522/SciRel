function [roots,d,kx,diagnostics]=fb_em_roots(matM,kn,state,w)
% Source em3d_Lpole.m:238-246: eigenvalues, positive-real filter, abs-imag sort.
  d=eig(matM);
  if ~isscalar(kn)||~isreal(kn)||~isfinite(kn)||kn<=0||any(~isfinite(d))
    error('fluidbw:eigen','positive finite kn and finite spectrum required');
  end
  % matMv=vpa(matM,20); d=eig(matMv); % 25-02-08 15:00 vpa slow & not must

  kx=d(real(d)>1e-5*kn);
  [tmp,ind]=sort(abs(imag(kx))); % keep Re(kx)>0 and min(abs(Im(kx))) solutions
  kx=kx(ind);
if numel(kx)<5, error('fluidbw:roots','fewer than five positive-real candidate eigenvalues'); end
roots=kx(1:5).';
% Keep the original eigenvalues-only driver/order above exactly. A separate
% vector calculation never permutes or replaces d or roots. Componentwise
% relative error is retained diagnostically, but is ill-conditioned at zero
% eigencomponents. The predeclared independent gate uses physical similarity
% scaling: E0=1 V/m, J0=epsilon0*abs(w)*E0, B0=E0/c, k0=kn.
[V,E]=eig(matM); e=diag(E); eta=zeros(size(e));
for k=1:numel(e)
 v=V(:,k); r=abs(matM*v-e(k)*v); scale=abs(matM)*abs(v)+abs(e(k)*v);
 active=scale>0; eta(k)=max(r(active)./scale(active));
end
ns=(rows(matM)-4)/3;
scales=[state.epsilon0*abs(w)*ones(3*ns,1);1;1;1/sqrt(state.c2);1/sqrt(state.c2)];
A=(matM.*scales.')./scales/kn; U=V./scales;
physical_eta=zeros(size(e));
for k=1:numel(e)
 u=U(:,k); lambda=e(k)/kn;
 physical_eta(k)=norm(A*u-lambda*u,inf)/((norm(A,inf)+abs(lambda))*norm(u,inf));
end
diagnostics=struct('eigenvector_values',e,'componentwise_backward_error',eta,...
 'physical_state_scaled_backward_error',physical_eta,'physical_gate_tolerance',2e-12,...
 'finite_matrix_mode_count',numel(d),'complete_finite_matrix_spectrum',numel(d)==rows(matM),...
 'complete_physical_modes',false,'selection_is_heuristic',true);
if any(~isfinite(physical_eta))||any(physical_eta>2e-12), error('fluidbw:eigen','physical state-scaled eigenpair backward residual failed'); end
end
