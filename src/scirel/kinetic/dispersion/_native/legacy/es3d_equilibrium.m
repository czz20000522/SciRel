% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_es3d.m@887498b2f9820d0d942504b6a061b19be52b318f
par.data=deck;
[S, col]=size(par.data);
if(col~=6)
    disp('Wrong input data !!!');
end

for s=1:S
    qs(s)=par.data(s,1); % charge
    ms(s)=par.data(s,2); % mass
    ns0(s)=par.data(s,3); % desity
    Tzs(s)=par.data(s,4); % parallel temperature
    Tps(s)=par.data(s,5); % perp temperature
    vs0(s)=par.data(s,6); % para drift velocity
end
vtzs=sqrt(2*Tzs./ms); % para thermal velocity
lambdaDs=sqrt(Tzs./(ns0.*qs.^2)); % Debye length, Tzs
kDs=1./lambdaDs;
wps=sqrt(ns0.*qs.^2./ms); % plasma frequency
wcs=B0*qs./ms; % cyclotron frequency
rhocs=sqrt(Tps./ms)./abs(wcs); % cyclotron radius
