function result=fb_assemble(state,omega,J,N)
poles=fb_em_poles(J); M=fb_em_matrix(state,poles,omega,N);
result=struct('M',M,'poles',poles,'state',state,'omega',omega,'N',N);
end
