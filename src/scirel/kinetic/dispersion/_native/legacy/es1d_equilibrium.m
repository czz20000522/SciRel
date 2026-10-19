% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_es1d.m@887498b2f9820d0d942504b6a061b19be52b318f
par.data=deck;
[S, col]=size(par.data);
if(col~=5)
    disp('Wrong input data !!!');
end

for j=1:S
    qs(j)=par.data(j,1);
    ms(j)=par.data(j,2);
    ns0(j)=par.data(j,3);
    Ts(j)=par.data(j,4);
    vs0(j)=par.data(j,5);
end
vts=sqrt(2*Ts./ms); % thermal velocity
lambdaDs=sqrt(Ts./(ns0.*qs.^2)); % Deybe length
kDs=1./lambdaDs;
wps=sqrt(ns0.*qs.^2./ms); % plasma frequency
