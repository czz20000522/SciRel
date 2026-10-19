% 18-10-06 07:36 Hua-sheng XIE, huashengxie@gmail.com, FRI-ENN, China
% Ackn.: Richard Denton (Dartmouth), Xin Tao (USTC), Jin-song Zhao (PMO), 
% etc ...
% This file initialize the parameters for pdrk_kernel.m

c2=(2.9979E8)^2; % speed of ligth c^2
epsilon0=8.8542E-12;
mu0=1/(c2*epsilon0);
kB=1.3807e-23;

% % read input parameters
pardat = importdata('../input/pdrk.in', ' ', 1);
[S, col]=size(pardat.data);
if(col~=8)
  disp('Wrong input data !!!');
end

for s=1:S
  qs0(s)=pardat.data(s,1); % charge, q/e
  ms0(s)=pardat.data(s,2); % mass, m/mp
  ns0(s)=pardat.data(s,3); % desity, m^-3
  Tzs0(s)=pardat.data(s,4); % parallel temperature, eV
  Tps0(s)=pardat.data(s,5); % perp temperature, eV
  alphas(s)=pardat.data(s,6); % loss-cone size/anisotropic
  Deltas(s)=pardat.data(s,7); % loss-cone depth, =0 (max) to 1 (no)
  vds0(s)=pardat.data(s,8); % para drift velocity, vds/c
  
  if(alphas(s)==1) % 18-10-13 10:19
    rsab(1,s)=1;
    rsab(2,s)=0;
  else
    % sigma=a, core fv ratio
    rsab(1,s)=(1-alphas(s)*Deltas(s))/(1-alphas(s));
    % sigma=b, loss cone fv ratio
    rsab(2,s)=alphas(s)*(Deltas(s)-1)/(1-alphas(s));
  end
end

Qtotal=sum(qs0.*ns0);
Jtotal=sum(qs0.*ns0.*vds0);

if((Qtotal~=0) || (Jtotal~=0))
  disp('Warning: Total charge or current not zero !!!');
  %input(['Warning: Total charge or current not zero!!',...
  %    'Press any key to continue.']);
end

qs=qs0*1.6022e-19; % * electron charge, e -> C (coulomb)
ms=ms0*1.6726e-27; % * proton mass, m_p -> kg, 18-10-13 09:57
Tzs=Tzs0*1.6022e-19/kB; % T//, eV -> K (eV -> J * J -> K)
Tps=Tps0*1.6022e-19/kB; % Tpr, eV -> K
vds=vds0*sqrt(c2); % vds, speed of light c -> m/s

vtzs=sqrt(2*kB*Tzs./ms); % para thermal velocity, note the sqrt(2)
lambdaDs=sqrt(epsilon0*kB*Tzs./(ns0.*qs.^2)); % Debye length, Tzs
kDs=1./lambdaDs;
wps=sqrt(ns0.*qs.^2./ms/epsilon0); % plasma frequency
wcs=B0*qs./ms; % cyclotron frequency
% rhocs=sqrt(kB*Tps./ms)./abs(wcs); % cyclotron radius
rhocs=sqrt(kB*Tps./ms)./wcs; % cyclotron radius, 2018-06-13 21:47

wps2=wps.^2;
lmdT=Tzs./Tps;

% for sigma=a,b due to the two perp temperatures for core and loss cone fv
Tpsab(1,:)=Tps; Tpsab(2,:)=alphas.*Tps;
lmdTab(1,:)=Tzs./Tpsab(1,:); lmdTab(2,:)=Tzs./Tpsab(2,:);
rhocsab(1,:)=sqrt(kB*Tpsab(1,:)./ms)./wcs;
rhocsab(2,:)=sqrt(kB*Tpsab(2,:)./ms)./wcs;

betasz=2*mu0*kB.*ns0.*Tzs./B0^2; % beta_para
betasp=2*mu0*kB.*ns0.*Tps./B0^2; % beta_perp
vA=B0/sqrt(mu0*sum(ms.*ns0)); % Alfven speed

% % !!--- change here if not: ion has max mass. 2018-10-05 11:06
% isa=find(ms==max(ms)); isa=isa(1); % find ion index 'is'
% isb=find(qs<0); % find electron index 'is'
% if(isempty(isb)) % in case only ion in 'pdrk_em3d.in'
%   isb=1;
% else
%   isb=isb(1);
% end
% % cS=sqrt(2*min(kB*Tzs)/max(ms)); % sound speed
% % wpi=sqrt(ns0(1)*qs(1)^2/max(ms)/epsilon0);
% cS=sqrt(2*kB*Tzs(isb)/ms(isa)); % sound speed
% wci=min(abs(wcs)); % omega_{ci}
% wpi=sqrt(ns0(isb)*qs(isb)^2/ms(isa)/epsilon0); % ion plasma frequency using electron density
% cwp=sqrt(c2)/wpi; % c/omega_{pi}
% vAwp=vA/wci; % v_A/omega_{ci}

% normalized by omega_c and omega_p of the first species, 18-10-18 19:25
cSs1=sqrt(2*kB*Tzs(1)/ms(1)); % sound speed
wcs1=abs(wcs(1)); % omega_{ci}
wps1=sqrt(ns0(1)*qs(1)^2/ms(1)/epsilon0);

cwp=sqrt(c2)/wps1; % c/omega_{p1}
vAwp=vA/wcs1; % v_A/omega_{c1}

run pdrk_poles;

SNJ=S*(2*N+1)*J;
SNJ1=SNJ+1;
if(iem==1) % electromagnetic case
  SNJ3=3*SNJ1;
  NN=SNJ3+6;
else % electrostatic case
  NN=SNJ1;
end

if(sp==0)
  nw=NN; % number of roots to obtain
else % using sparse matrix
  nw=1; % !! only nw solutions around the initial guesses are given
  wg=wg0*wcs1;
end
nw0=nw;
sp0=sp;

npa=round((pa2-pa1)/dpa)+1; pa=pa1+(0:npa-1)*dpa;  
if(ipa==ipb) % if ipa==ipb, do only 1D scan of pa
  npb=1;
  pb=pa(1); % 18-10-06 01:00
else % do 2D scan (pa,pb)
  npb=round((pb2-pb1)/dpb)+1; pb=pb1+(0:npb-1)'*dpb;
end

% Typical cases of (ipa,ipb): 
%   1. (1,1) scan k, fixed theta
%   2. (2,2) scan theta, fixed k
%   3. (1,2) scan 2D (k, theta)
%   4. (3,3) scan kz, fixed kx
%   5. (4,4) scan kx, fixed kz
%   6. (3,4) scan 2D (kz,kx)
%   7. (..,..) others, please modify 'pdrk_si_kernel.m'
ireturn=0;
if(ipa==1 && ipb==1)
  strpa='kc/\omega_p'; strpb='\theta^\circ';
  strscan='1. (1,1) scan k, fixed theta';
  ipbtmp=2;
elseif(ipa==2 && ipb==2)
  strpa='\theta'; strpb='kc/\omega_p';
  strscan='2. (2,2) scan theta, fixed k';
  ipbtmp=1;
elseif(ipa==3 && ipb==3)
  strpa='k_zc/\omega_p'; strpb='k_xc/\omega_p';
  strscan='4. (3,3) scan kz, fixed kx';
  ipbtmp=4;
elseif(ipa==4 && ipb==4)
  strpa='k_xc/\omega_p'; strpb='k_zc/\omega_p';
  strscan='5. (4,4) scan kx, fixed kz';
  ipbtmp=3;
elseif(ipa==1 && ipb==2)
  strpa='kc/\omega_p'; strpb='\theta';
  strscan='3. (1,2) scan 2D (k, theta)';
elseif(ipa==3 && ipb==4)
  strpa='k_zc/\omega_p'; strpb='k_xc/\omega_p';
  strscan='6. (3,4) scan 2D (kz,kx)';
else
  strpa='--'; strpb='--';
  strscan=['7. (..,..), not support this scan (ipa,ipb) yet, ',...
      'please modify ''pdrk_kernel.m''!!!'];
  ireturn=1;
end

if(~exist(savepath,'dir')) % in case savepath not exist
  mkdir(savepath);
end
