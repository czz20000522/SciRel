% SciRel D2 exact kz=0 Maxwell-current pencil.
% Independent velocity-integral residue: Cp=2*weight*wp2/vtp2*<Pi_n>.
% K=I-totalwp2/omega^2-sum(p*Cp/[omega^2*(omega-p)]).
% Q=omega*(I-K)=C0/omega+sum(Cp/(omega-p)), C0=totalwp2*I-sum(Cp).
% Source E-row convention is -I; auxiliary E coefficients are -Cp.
% One of J coincident pole slots carries each residue; the others have zero
% driving, retained for constant source dimensions across the whole scan.
k=abs(kx); bsab=kx*rhocsab; bsab2=bsab.^2;
M=sparse(NN,NN); csnj=zeros(1,3*SNJ);
b11snj=csnj*0; b12snj=csnj*0; b13snj=csnj*0;
b21snj=csnj*0; b22snj=csnj*0; b23snj=csnj*0;
b31snj=csnj*0; b32snj=csnj*0; b33snj=csnj*0;
scirel_C0=sum(wps2)*eye(3);
for s=1:S
  for n=-N:N
    scirel_Cp=zeros(3,3);
    for iab=1:2
      if rsab(iab,s)==0 || wps2(s)==0; continue; end
      scirel_vtp2=vtzs(s)^2/lmdTab(iab,s);
      if kx==0
        % Analytic b=0 ordinary-Bessel moment; no arbitrary kx clamp.
        if abs(n)==1
          scirel_T=scirel_vtp2/4*[1,1i*n,0;-1i*n,1,0;0,0,0];
        else
          scirel_T=zeros(3,3);
        end
      elseif n~=0
        scirel_b=bsab2(iab,s);
        scirel_gamma=besseli(n,scirel_b,1);
        scirel_der=(besseli(n-1,scirel_b,1)+besseli(n+1,scirel_b,1)-2*scirel_gamma)/2;
        scirel_xx=(n*wcs(s)/kx)^2*scirel_gamma;
        scirel_yy=scirel_vtp2/2*(n*n*scirel_gamma/scirel_b-2*scirel_b*scirel_der);
        scirel_xy=1i*n*scirel_vtp2/2*scirel_der;
        scirel_xz=n*wcs(s)/kx*scirel_gamma*vds(s);
        scirel_yz=-1i*vds(s)*kx*scirel_vtp2/(2*wcs(s))*scirel_der;
        scirel_zz=(vds(s)^2+vtzs(s)^2/2)*scirel_gamma;
        scirel_T=[scirel_xx,scirel_xy,scirel_xz;-scirel_xy,scirel_yy,scirel_yz;scirel_xz,-scirel_yz,scirel_zz];
      else
        scirel_T=zeros(3,3);
      end
      scirel_Cp=scirel_Cp+rsab(iab,s)*2*wps2(s)/scirel_vtp2*scirel_T;
    end
    scirel_C0=scirel_C0-scirel_Cp;
    for j=1:J
      snj=((s-1)*(2*N+1)+(n+N))*J+j;
      csnj(snj)=n*wcs(s);
      scirel_ix=[snj,snj+SNJ1,snj+2*SNJ1];
      M(scirel_ix,scirel_ix)=n*wcs(s)*eye(3);
      M(SNJ3+(1:3),scirel_ix)=-eye(3);
      if j==1; M(scirel_ix,SNJ3+(1:3))=-scirel_Cp; end
    end
    snj=((s-1)*(2*N+1)+(n+N))*J+1;
    b11snj(snj)=-scirel_Cp(1,1); b12snj(snj)=-scirel_Cp(1,2); b13snj(snj)=-scirel_Cp(1,3);
    b21snj(snj)=-scirel_Cp(2,1); b22snj(snj)=-scirel_Cp(2,2); b23snj(snj)=-scirel_Cp(2,3);
    b31snj(snj)=-scirel_Cp(3,1); b32snj(snj)=-scirel_Cp(3,2); b33snj(snj)=-scirel_Cp(3,3);
  end
end
scirel_ix=[SNJ1,2*SNJ1,3*SNJ1];
M(scirel_ix,SNJ3+(1:3))=-scirel_C0;
M(SNJ3+(1:3),scirel_ix)=-eye(3);
b11=-scirel_C0(1,1); b12=-scirel_C0(1,2); b13=-scirel_C0(1,3);
b21=-scirel_C0(2,1); b22=-scirel_C0(2,2); b23=-scirel_C0(2,3);
b31=-scirel_C0(3,1); b32=-scirel_C0(3,2); b33=-scirel_C0(3,3);
scirel_cross=[0,0,0;0,0,-kx;0,kx,0];
M(SNJ3+(1:3),SNJ3+(4:6))=-c2*scirel_cross;
M(SNJ3+(4:6),SNJ3+(1:3))=scirel_cross;
if any(~isfinite(nonzeros(M)))
  error('scirel:matrixRange','Exact perpendicular pencil is not representable');
end
clear scirel_C0 scirel_Cp scirel_T scirel_vtp2 scirel_b scirel_gamma scirel_der scirel_xx scirel_yy scirel_xy scirel_xz scirel_yz scirel_zz scirel_ix scirel_cross;
