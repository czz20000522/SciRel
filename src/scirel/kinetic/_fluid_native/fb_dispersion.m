function [value, state_after] = fb_dispersion(kx, state, method)
% D2 corrected fD/fDR call with explicit before/after globals.
% State ports: S,c2,wcs,wps2,rhocs,w,kz,vts, in original shapes and units.
% Both corrected implementations retain signed kz without mutation.
% No default method is invented: pass 'fD' or 'fDR'. Native failures rethrow.
  if ~strcmp(method,'fD') && ~strcmp(method,'fDR')
    error('fluidbw:method','method must be fD or fDR');
  end
  previous = fb_global_state('get');
  restore = onCleanup(@() fb_global_state('set',previous));
  fb_global_state('set',state);
  value = feval(method,kx);
  state_after = fb_global_state('get');
end
