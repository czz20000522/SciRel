% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_em3d.m@887498b2f9820d0d942504b6a061b19be52b318f
par.data=deck;
c2=(2.9979E8)^2; epsilon0=8.8542E-12;
mu0=1/(c2*epsilon0);
kB=1.3807e-23;
[S, col]=size(par.data);
if(col~=6)
  disp('Wrong input data !!!');
end

for s=1:S
  qs0(s)=par.data(s,1); % charge
  ms0(s)=par.data(s,2); % mass
  ns0(s)=par.data(s,3); % desity, m^-3
  Tzs0(s)=par.data(s,4); % parallel temperature, eV
  Tps0(s)=par.data(s,5); % perp temperature, eV
  vs0(s)=par.data(s,6); % para drift velocity
end

qs=qs0*1.6022e-19; % * electron charge, e -> C (coulomb)
ms=ms0*9.1094E-31; % * electron mass, m_e -> kg
Tzs=Tzs0*1.6022e-19/kB; % T//, eV -> K (eV -> J * J -> K)
Tps=Tps0*1.6022e-19/kB; % Tpr, eV -> K
vs0=vs0*sqrt(c2); % vs0, speed of light c -> m/s

vtzs=sqrt(2*kB*Tzs./ms); % para thermal velocity, note the sqrt(2)
lambdaDs=sqrt(epsilon0*kB*Tzs./(ns0.*qs.^2)); % Debye length, Tzs
kDs=1./lambdaDs;
wps=sqrt(ns0.*qs.^2./ms/epsilon0); % plasma frequency
wcs=B0*qs./ms; % cyclotron frequency
% rhocs=sqrt(kB*Tps./ms)./abs(wcs); % cyclotron radius
rhocs=sqrt(kB*Tps./ms)./wcs; % cyclotron radius, 2018-06-13 21:47

wps2=wps.^2;
lmdT=Tzs./Tps;

betasz=2*mu0*kB.*ns0.*Tzs./B0^2; % beta_para
betasp=2*mu0*kB.*ns0.*Tps./B0^2; % beta_perp
vA=B0/sqrt(mu0*sum(ms.*ns0)); % Alfven speed
cS=sqrt(2*min(kB*Tzs)/max(ms));

% change here if the second species is not ion
wci=abs(wcs(2)); % omega_{ci}
wpi=sqrt(ns0(1)*qs(2)^2/ms(2)/epsilon0); % ion plasma frequency using electron density
cwp=sqrt(c2)/wpi; % c/omega_{pi}
vAwp=vA/wci; % v_A/omega_{ci}
