function observation = fb_dispersion_observe(kx, state, method)
% Explicit failure/state observation interface. Scientific failure is data.
% Direct fD/fDR and fb_dispersion still expose the corrected thrown failure.
  if ~strcmp(method,'fD') && ~strcmp(method,'fDR')
    error('fluidbw:method','method must be fD or fDR');
  end
  previous = fb_global_state('get');
  restore = onCleanup(@() fb_global_state('set',previous));
  fb_global_state('set',state);
  observation = struct('ok',false,'value',[],'error_identifier','','error_message','','state_after',struct());
  try
    observation.value = feval(method,kx);
    observation.ok = true;
  catch err
    observation.error_identifier = err.identifier;
    observation.error_message = err.message;
  end
  observation.state_after = fb_global_state('get');
end
