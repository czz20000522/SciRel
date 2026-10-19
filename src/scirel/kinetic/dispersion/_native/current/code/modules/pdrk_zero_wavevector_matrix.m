% Exact uniform-field magnetized response, independent of harmonic cutoff.
% Two active cyclotron pole slots per species fit even source N0/J4 dimensions.
% Cp(+/-Omega)=wp2/2*[1,+/-i,0;-/+i,1,0;0,0,0], C0zz=sum(wp2).
% All other source auxiliary slots are undriven aliases, not physical modes.
k=0;bsab=zeros(2,S);bsab2=bsab;M=sparse(NN,NN);csnj=zeros(1,3*SNJ);
b11snj=csnj*0;b12snj=csnj*0;b13snj=csnj*0;
b21snj=csnj*0;b22snj=csnj*0;b23snj=csnj*0;
b31snj=csnj*0;b32snj=csnj*0;b33snj=csnj*0;
for s=1:S
  for scirel_sign=[1,-1]
    snj=(s-1)*(2*N+1)*J+1+(scirel_sign==-1);
    csnj(snj)=scirel_sign*wcs(s);
    scirel_Cp=wps2(s)/2*[1,1i*scirel_sign,0;-1i*scirel_sign,1,0;0,0,0];
    scirel_ix=[snj,snj+SNJ1,snj+2*SNJ1];
    M(scirel_ix,scirel_ix)=csnj(snj)*eye(3);
    M(scirel_ix,SNJ3+(1:3))=-scirel_Cp;
    M(SNJ3+(1:3),scirel_ix)=-eye(3);
    b11snj(snj)=-scirel_Cp(1,1);b12snj(snj)=-scirel_Cp(1,2);
    b21snj(snj)=-scirel_Cp(2,1);b22snj(snj)=-scirel_Cp(2,2);
  end
end
b11=0;b12=0;b13=0;b21=0;b22=0;b23=0;b31=0;b32=0;b33=-sum(wps2);
scirel_ix=[SNJ1,2*SNJ1,3*SNJ1];M(scirel_ix,SNJ3+(1:3))=diag([0,0,b33]);M(SNJ3+(1:3),scirel_ix)=-eye(3);
if any(~isfinite(nonzeros(M)));error('scirel:matrixRange','Uniform field matrix not representable');end
clear scirel_sign scirel_Cp scirel_ix;
