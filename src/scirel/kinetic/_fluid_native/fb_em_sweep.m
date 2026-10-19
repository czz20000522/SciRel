function result=fb_em_sweep(state,poles,N,xx)
% Source ordered frequency sweep. No root continuation; final d/matM also observable.
if nargin<3, N=6; end
if nargin>=4, xx_input=xx; end
fb_unpack_workspace(state,{'S','c2','wcs','wps2','rhocs','kz','vts','epsilon0','kn'});
if nargin<4, xx=state.xx; else, xx=xx_input; end
if ~isvector(xx)||isempty(xx)||~isreal(xx)||any(~isfinite(xx))||any(xx==0), error('fluidbw:axis','nonempty finite nonzero real omega vector required'); end
nx=length(xx); kxx=zeros(nx,5); runtime=cputime;
for jx=1:nx
  jx
  w=xx(jx);
  matM=fb_em_matrix(state,poles,w,N);
  [roots,d,kx,eigen_diagnostics]=fb_em_roots(matM,kn,state,w);
  spectra{jx}=d; selected_candidates{jx}=kx; diagnostic_rows{jx}=eigen_diagnostics;
  kxx(jx,1:5)=roots;
end
runtime=cputime-runtime;
result=state; fields=fb_pack_workspace();
for name=fieldnames(fields).', result.(name{1})=fields.(name{1}); end
result.J=poles.J; result.cn=poles.cn; result.cn_raw=poles.cn_raw; result.moment_normalization=poles.moment_normalization; result.bzj=poles.bzj; result.czj=poles.czj;
end
