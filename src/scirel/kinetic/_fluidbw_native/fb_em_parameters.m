function state=fb_em_parameters(jcase)
% Source em3d_Lpole.m:14-85. Defaults case2; forced kz=0.1*kn preserved.
if nargin<1, jcase=2; end
if ~isscalar(jcase)||~any(jcase==[1 2]), error('fluidbw:case','undefined source case'); end
% 1. default SI unit
c2=(2.99792458E8)^2; % speed of ligth c^2
epsilon0=8.854187817E-12;
mu0=1/(c2*epsilon0);
kB=1.38064852e-23;
qe=1.60217662e-19; % electron charge, coulombs
mp=1.6726219e-27; % proton mass, kg
me=9.1094e-31; % electron mass, kg

% 2. set parameters, modify here for your own case
if(jcase==1)
  ms=[me,2*mp]; % speceis mass
  qs=[-1,1]*qe; % speceis charge
  ns_unit=[1,1]; % *den0, species density, m^-3
  Ts_unit=[1,1]; % eV
  S=length(ms);

  B0=6e0; % background B field, Tesla
  n00=2e20; % m^-3
  % f=28e9; % Hz

  T00=2*2e3; % eV
  % w=f*2*pi; % omega

  kz=2*5.0;
elseif(jcase==2)
  ms=me; % speceis mass
  qs=-1*qe; % speceis charge
  ns_unit=1; % *den0, species density, m^-3
  Ts_unit=1; % eV
  S=length(ms);

  B0=1e0; % background B field, Tesla
  n00=6.075e19; % m^-3
  % f=28e9; % Hz

  T00=1e3; % eV
  kz=0.0;
end

ns0=ns_unit*n00;
Ts0=Ts_unit*T00*1.6022e-19/kB; % Ts, eV -> K
vts=sqrt(2*kB*Ts0./ms); % thermal velocity
c=sqrt(c2);

wcs=qs*B0./ms; % the gyro frequency
wps=sqrt(ns0.*qs.^2./ms/epsilon0); % plasma frequency
wcs2=wcs.^2;
wps2=wps.^2;
wp2=sum(wps2);
rhocs=sqrt(kB*Ts0./ms)./wcs; % cyclotron radius
absrhocs=abs(rhocs);
sgns=sign(rhocs);
% sgns=abs(sign(rhocs));

lambdaDs=sqrt(epsilon0*kB*Ts0./(ns0.*qs.^2)); % Debye length, Tzs
kDs=1./lambdaDs;
% kn=abs(kDs(1));

wcn=min(abs(wcs));
rhocn=max(abs(rhocs));
kn=1/rhocn;
% kn=1/abs(rhocs(1));
wn=wcn;

kz=0.1*kn; % 25-02-02 01:54

xx=(0.05:0.05:3.95)*wn;
% xx=(1.5:0.05:1.50)*wn;
nx=length(xx);
runtime=cputime;
state=fb_pack_workspace();
end
