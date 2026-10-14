function result=fb_bonk_sweep(state,xx)
% Source main_tst.m:87-111: independent fsolve at every frequency.
% Fixed bounded seed list per frequency; no continuation update.
% TolFun/TolX 1e-16 unchanged; each attempt MaxIter400/MaxFunEvals100.
% Explicit global state is isolated and caller globals restored on success/error.
prior=fb_global_state('get'); cleanup=onCleanup(@()fb_global_state('set',prior));
global S c2 wcs wps2 rhocs w kz vts;
fb_unpack_workspace(state,{'S','c2','wcs','wps2','rhocs','kz','vts','kn','wcn'});
if nargin<2, xx=(0.11:0.05:3.95).*wcn+0*wcn; end
if ~isvector(xx)||isempty(xx)||~isreal(xx)||any(~isfinite(xx))||any(xx==0), error('fluidbw:axis','nonempty finite nonzero real omega vector required'); end
nx=length(xx); fDr=zeros(nx,1); runtime=cputime;
for jx=1:nx
    w=xx(jx);
    % D2: dimensionless real/imaginary search replaces the dimensionful
    % raw determinant search, which falsely saved a nonroot near kx=0.
    % Fixed, declared seeds apply at every frequency, never branch continuation.
    seeds=[.6+0i,.6+.1i,.6-.1i,1+0i,2+0i];
    options=optimset('Display','off','TolFun',1e-16,'TolX',1e-16,...
      'MaxIter',400,'MaxFunEvals',100);
    attempt_rows={}; best=Inf; root_valid(jx,1)=false;
    for attempt=1:numel(seeds)
      seed=seeds(attempt); [~,~,D0]=fDR(seed*kn);
      reference=max(1,prod(sqrt(sum(abs(D0).^2,2))));
      [q,scaled_fval,info,out]=fsolve(@(q)fb_bonk_scaled(q,kn,reference),[real(seed);imag(seed)],options);
      candidate=(q(1)+1i*q(2))*kn; [raw_f,K,D]=fDR(candidate);
      scale=max(abs(D),[],2); scale(scale==0)=1; sv=svd(D./scale);
      row_diagnostic=min(sv)/max(sv);
      physical_sv=svd(D); wave_res=min(physical_sv)/max(1,max(physical_sv));
      determinant_res=abs(det(D))/max(1,prod(sqrt(sum(abs(D).^2,2))));
      valid=isfinite(wave_res)&&isfinite(determinant_res)&&wave_res<=1e-8&&determinant_res<=1e-8;
      attempt_rows{attempt}=struct('seed_kn',seed,'candidate',candidate,'solver_info',info,...
       'raw_determinant',raw_f,'scaled_fval',scaled_fval,'wave_residual',wave_res,...
       'determinant_residual',determinant_res,'dynamic_row_residual_diagnostic',row_diagnostic,'iterations',out.iterations,'function_evals',out.funcCount);
      if valid||wave_res<best
        best=wave_res; kx1=candidate; residual(jx,1)=wave_res; normalized_determinant(jx,1)=determinant_res;
        exit_status(jx,1)=info; solver_residual(jx,1)=raw_f; iterations(jx,1)=out.iterations; function_evals(jx,1)=out.funcCount;
      end
      if valid
        root_valid(jx,1)=true; break;
      end
    end
    solver_attempts{jx}=attempt_rows;
    nf(jx,1)=kx1;
end
runtime=cputime-runtime;
result=state; fields=fb_pack_workspace();
for name=fieldnames(fields).', result.(name{1})=fields.(name{1}); end
result.complete_physical_modes=false;
result.root_contract='bounded dimensionless fixed-seed searches; raw fsolve status retained; root_valid requires independent determinant and dimensionless normwise Maxwell residuals <=1e-8';
end
