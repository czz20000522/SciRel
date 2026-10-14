function value=fb_special(method,x,parameter)
if strcmp(method,'zfun')
 if any(~isfinite(x(:)))||isempty(x), error('fluidbw:domain','finite nonempty Z arguments required'); end
 value=zfun(x);
elseif any(strcmp(method,{'Gamman','Gammapn'}))
 if any(~isfinite(x(:)))||any(x(:)~=fix(x(:)))||~isreal(x)||isempty(x)||any(~isfinite(parameter(:)))||isempty(parameter)
  error('fluidbw:domain','finite integer orders and finite Bessel arguments required');
 end
 value=feval(method,x,parameter);
elseif any(strcmp(method,{'RTAY','RASY','RINT','RYLA'}))
 value=feval(method,x,parameter);
else, error('fluidbw:method','unknown method'); end
if any(~isfinite(value(:))), error('fluidbw:precision','special function is not representable'); end
end
