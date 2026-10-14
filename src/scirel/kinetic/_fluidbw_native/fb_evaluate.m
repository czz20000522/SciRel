function result=fb_evaluate(kx,state,method)
previous=fb_global_state('get'); cleanup=onCleanup(@()fb_global_state('set',previous));
fb_validate_state(state); fb_global_state('set',state);
if strcmp(method,'fDR'), [DD,K,D]=fDR(kx);
elseif strcmp(method,'fD'), [DD,K,D]=fb_tensor(kx,state,5);
elseif strcmp(method,'fDtensor'), [DD,K,D]=fb_tensor(kx,state,15);
else, error('fluidbw:method','unknown dispersion method'); end
result=struct('determinant',DD,'K',K,'D',D,'state_after',fb_global_state('get'));
end
