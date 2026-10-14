% Hua-sheng XIE, huashengxie@gmail.com, IFTS-ZJU, 2014-06-01 17:00
% pdrk_em3d.m, Plasma Dispersion Relastion solver, kinetic, EM3D,
% bi-Maxwellian equilibrium distribution with parallel drift.
% Transform to matrix eigenvalue problem lambda*X=M*X.
% J-pole approximation for Z(zeta)=sum(b_j/(zeta-c_j))
%
% sparse, eigs
%
% 2014-08-22 01:09, support T_perp/T_para \neq 1,  vds \neq 0
%
% Ref:
%  [Xie2016] H. S. Xie & Y. Xiao, PDRK: A General Kinetic Dispersion
%    Relation Solver for Magnetized Plasma, Plasma Science and Technology,
%    Vol.18, No.2, p97 (2016). (Also 2014arXiv, note: have several typos)
%
% Documents/codes/Erratum: http://hsxie.me/codes/pdrk/
%
% 18-09-28 12:42 We find that omega_cs=-qB/m in Miyamoto2004, not the
% standard omega_cs=qB/m. This sign difference affect several terms. This
% version we have fixed the bugs of the sign of omega_cs.
% 18-10-01 09:43 based on new derivations, fixed a bug in b33 term, where a
% wcs^2 is missed.
% 16:01 Benchmark with Gary1993 Fig.7.4 and several other cases ok.
%
% Ref (typos/bugs fixed):
%  H. S. Xie, Detailed Derivations of PDRK-EM3D Equations, 2018-10-03 (
%  10 pages).
% 
% 18-10-03 13:14 This version should be bugs free now.
% 18-10-13 10:37 update to with loss-cone distribution, which thus can
% handle all the same input cases as WHAMP [Ronnmark1982] code
% ------------------------------------------------------------------------
% This file is the kernel part of pdrk-em3d code.
% Modify sp and nw if you only need one or several solutions around the
% initial guess value wg.

wwp=zeros(npa,npb,nw);
[ppa,ppb]=ndgrid(pa,pb);
kxx=0.*ppa; % for store kx
kzz=0.*ppa; % for store kz
kk=0.*ppa; % for store k
tt=0.*ppa; % for store theta
%tic;
for jpa = 1:npa % scan 1st parameter a
  
  for jpb = 1:npb % scan 2nd parameter b
    
    % ------- to update 2018-10-18 20:10 --------
    if(iloga==0)
      par(ipa)=pa(jpa);
    else
      par(ipa)=10^(pa(jpa));
    end
    if(ipa~=ipb)
      if(ilogb==0)
        par(ipb)=pb(jpb);
      else
        par(ipb)=10^(pb(jpb));  
      end
    end
    
    k=abs(par(1))/cwp; % k only >=0
    theta=par(2); % the angle between k and B0
    if(ipa>2 && ipb>2) % !! to update
      kz=par(3)/cwp;
      kx=par(4)/cwp;
    else
      kz=cos(theta*pi/180)*k;
      kx=sin(theta*pi/180)*k;
    end
    k=sqrt(kx*kx+kz*kz); % update k
    theta=angle(kz+1i*kx)*180/pi; % update theta
    % !! if you want scan other parameters, modify here, e.g.,
    % betasz=par(5); % or vds(1)=par(5); % etc
    % ---------------
    
    if(iem==1) % electromagnetic run
      run pdrk_em3d_matrix;
    else % electrostatic run, 18-10-20 20:02
      run pdrk_es3d_matrix;
    end
    
    run pdrk_eigensolve;

    if(jpb==1) % initial guess for pb(jpa+1,jpb)
      wg0=wg;
    end

    wwp(jpa,jpb,1:nw)=w(1:nw);
    
    % D2: retain every actual matrix coordinate, also after polarization.
    kxx(jpa,jpb)=kx;
    kzz(jpa,jpb)=kz;
    kk(jpa,jpb)=k;
    tt(jpa,jpb)=theta;
  end %jpb
  
  wg=wg0; % update the new initial guess
  
end %jpa
%runtime=toc;
if(icalp==0)
  ww=wwp; % store all the solutions in the first run
end
