% D2: corrected full harmonic R response, signed kz reflection and explicit finite-domain validation.
% Hua-sheng XIE, huashengxie@gmail.com, ENN, 2021-08-31 17:03
% Hot magnetized plasma dispersion relation, only Maxwellian.
% Ref: Xie, H.; Ma, H. & Bai, Y., Plasma Waves Accessibility Diagrams: A
%   Tutorial to Include the Fluid and Kinetic Thermal Effects, arXiv, 2021.
% Note the sqrt(2) of notations have been updated.
% 21-11-12 19:37 fixed a bug on Dxz & Dzx
% 22-06-06 14:19 update for YANG Hua (ASIPP) ICRF full wave
% 25-01-25 23:42 update with Ronnmark83 method, J-pole for Z fun & sum_n
% Bessel function to a single function R(x,lambda) to avoid convergence
% problem at large kperp
% 25-02-13 08:08 use Ronnmark83's RYLA to fast calcualte R & dR
% 25-07-24 15:07 fixed bug of Xsn_yy term a Rsj should be dRsj

% 2021-08-28 17:00 modified from previous (2013-06-17) pdrko.m
function [f,K,D]=fDR(kx) % DR, only Maxwellian
% you can also modify to input kx to solve omega as f=fDR(w), and set
% global kx

global S c2 wcs wps2 rhocs w kz vts;

% vts=sqrt(2*kB*Ts./ms); % rhocs=vts/(sqrt(2)*wcs);

fb_validate_state(fb_global_state('get'));
if ~isscalar(kx)||~isfinite(kx), error('fluidbw:domain','finite scalar kx required'); end
reflection=sign(kz);
nx=sqrt(c2)*kx/w; nz=sqrt(c2)*kz/w;
as=kx*rhocs;
bs=as.^2;

J=8;
if(J==8) % J-pole, usually J=8 is sufficient; other choice: 4, 12
    % 18-12-28 11:11
    bzj(1)=   -0.017340112270401 - 0.046306439626294i;
    bzj(2)=   -0.739917811220052 + 0.839518284620274i;
    bzj(3)=   5.840632105105495 + 0.953602751322040i;
    bzj(4)=   -5.583374181615043 -11.208550459628098i;
    czj(1)=   2.237687725134293 - 1.625941024120362i;
    czj(2)=   1.465234091939142 - 1.789620299603315i;
    czj(3)=   0.839253966367922 - 1.891995211531426i;
    czj(4)=   0.273936218055381 - 1.941787037576095i;

    bzj(5:8)=conj(bzj(1:4));
    czj(5:8)=-conj(czj(1:4));
elseif(J==12) % from Cal_J_pole_bjcj.m
    % J=12; I=12; 18-12-28 22:35
    bzj(1)=  - 10.020983259474214017 - 14.728932929429874883i;
    bzj(2)= - 0.58878169153449514493 + 0.19067303610080007359i;
    bzj(3)= - 0.27475707659732384029 + 3.617920717493884482i;
    bzj(4)= 0.00045713742777499515344 + 0.00027155393843737098852i;
    bzj(5)=  0.017940627032508378515 - 0.036436053276701248142i;
    bzj(6)=  10.366124263145749629 - 2.5069048649816145967i;
    czj(1)= 0.22660012611958088507627 - 2.0716877594897791206264i;
    czj(2)= - 1.70029215163003500750575 - 1.8822474221612724460388i;
    czj(3)= 1.17139325085601178534269 - 1.97725033192085410977458i;
    czj(4)= 3.0666201126826972102007 - 1.59002082593259971758095i;
    czj(5)= 2.307327490410578276422 - 1.7546732543728200653674i;
    czj(6)= 0.687200524906019065672977 - 2.040288525975844018682i;

    bzj(7:12)=conj(bzj(1:6));
    czj(7:12)=-conj(czj(1:6));
end

Kxx=1; Kxy=0; Kxz=0;
Kyx=0; Kyy=1; Kyz=0;
Kzx=0; Kzy=0; Kzz=1;
for s=1:S
    b=bs(s);
    a=as(s);
    for j=1:J
        xsj=(w-abs(kz)*vts(s)*czj(j))/wcs(s);

        RC=RYLA(xsj, b);  % 25-01-29 14:47 from Ronnmark82 WHAMP code
        Rsj=RC(1,1); dRsj=RC(1,2);
        % Rsj=fRxb(xsj,b); dRsj=fdRxb(xsj,b);

        Xsn_xx=Rsj;
        Xsn_xy=1i*dRsj/xsj;
        Xsn_xz=reflection*sqrt(2)*a*czj(j)/xsj*Rsj;
        Xsn_yx=-Xsn_xy;
        % Xsn_yy=Rsj-2*b/xsj^2*Rsj; % wrong
        Xsn_yy=Rsj-2*b/xsj^2*dRsj; % 25-07-24 15:07 fixed bug
        Xsn_yz=-1i*reflection*sqrt(2)*a*czj(j)/xsj^2*dRsj;
        Xsn_zx=Xsn_xz;
        Xsn_zy=-Xsn_yz;
        Xsn_zz=2*czj(j)^2/xsj^2*(xsj+b*Rsj);

        term1=wps2(s)/(w*wcs(s))*bzj(j);

        Kxx=Kxx+term1*Xsn_xx;
        Kxy=Kxy+term1*Xsn_xy;
        Kxz=Kxz+term1*Xsn_xz;
        Kyx=Kyx+term1*Xsn_yx;
        Kyy=Kyy+term1*Xsn_yy;
        Kyz=Kyz+term1*Xsn_yz;
        Kzx=Kzx+term1*Xsn_zx;
        Kzy=Kzy+term1*Xsn_zy;
        Kzz=Kzz+term1*Xsn_zz;
    end
    % Kzz=Kzz+2*z0^2; % 21-09-02 21:26 wrong?
    % Kzz=Kzz+wps2(s)/w^2*2*z0^2;
end

Dxx=Kxx-nz^2; Dyx=Kyx; Dxy=Kxy;
% Dxz=Kxz-nx*nz; Dyy=Kyy-(nx^2+nz^2); Dzx=Kzx-nx*nz; % wrong
Dxz=Kxz+nx*nz; Dyy=Kyy-(nx^2+nz^2); Dzx=Kzx+nx*nz; % 21-11-12 19:37
Dzy=Kzy; Dyz=Kyz; Dzz=Kzz-nx^2;

DD=Dxx*Dyy*Dzz+Dyx*Dzy*Dxz+Dzx*Dyz*Dxy-...
    Dxz*Dyy*Dzx-Dyz*Dzy*Dxx-Dzz*Dyx*Dxy;
f=DD;
K=[Kxx,Kxy,Kxz;Kyx,Kyy,Kyz;Kzx,Kzy,Kzz];
D=[Dxx,Dxy,Dxz;Dyx,Dyy,Dyz;Dzx,Dzy,Dzz];
if any(~isfinite(D(:)))||~isfinite(f), error('fluidbw:precision','Ronnmark tensor is not representable'); end

end

% function Rxb=fRxb(x,b) % 25-01-25 23:55
% % fphi=@(phi)cos(x*phi).*exp(-b*(1+cos(phi)));
% % gz(jz)=x/(sin(pi*x))*integral(fphi,0,pi);
% 
% % fphi=@(phi)sin(x*phi).*sin(phi).*exp(-b*(1+cos(phi)));
% % Rxb=-x/(sin(pi*x))*integral(fphi,0,pi);
% 
% % 25-01-29 14:47
% RC = RYLA(x, b); % from Ronnmark82 WHAMP code
% Rxb=RC(1);
% 
% end
% 
% function dRxb=fdRxb(x,b) % 25-01-26 19:40
% dRxb=0.5*x^2/(x+1)^2*(b*fRxb(x+1,b)+(x+1))+...
%     0.5*x^2/(x-1)^2*(b*fRxb(x-1,b)+(x-1))-(b*fRxb(x,b)+x);
% end
