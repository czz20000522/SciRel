% D2: exact parallel ratios; perpendicular model uses separate full-I pole pencil.
if(kz==0), error('scirel:perpendicular_dispatch','Use qualified perpendicular pole pencil'); end
% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_em3d.m@887498b2f9820d0d942504b6a061b19be52b318f
SNJ=S*(2*N+1)*J;
SNJ1=SNJ+1;
SNJ3=3*SNJ1;
NN=SNJ3+6;
    k=sqrt(kz^2+kx^2);
    bs=kx*rhocs;
% D2 exact zero/underflow ratios below replace the source epsilon clamp.

    bs2=bs.^2;
    M=sparse(NN,NN);
    snj=0;

    % initialize
    b11=0; b12=0; b13=0; b21=0; b22=0; b23=0; b31=0; b32=0; b33=0;
    csnj=zeros(1,3*SNJ);
    b11snj=csnj.*0; b12snj=csnj.*0; b13snj=csnj.*0;
    b21snj=csnj.*0; b22snj=csnj.*0; b23snj=csnj.*0;
    b31snj=csnj.*0; b32snj=csnj.*0; b33snj=csnj.*0;

    for s=1:S % species
      for n=-N:N % Bessel function
        %             Gamn=exp(-bs2(s))*besseli(n,bs2(s)); % large k_perp will NaN
        %             Gamnp=exp(-bs2(s))*(besseli(n+1,bs2(s))+...
        %                 besseli(n-1,bs2(s))-2*besseli(n,bs2(s)))/2;
        Gamn=besseli(n,bs2(s),1); % 2014-10-13 12:51
        Gamnp=(besseli(n+1,bs2(s),1)+...
          besseli(n-1,bs2(s),1)-2*besseli(n,bs2(s),1))/2;
        % D2 exact parallel/underflow limits from scaled-Bessel Taylor series.
        if(bs2(s)==0)
          n2GammaOverB2=double(abs(n)==1)/2;
          nGammaOverB=double(abs(n)==1)*n*bs(s)/2;
        else
          n2GammaOverB2=n^2*Gamn/bs2(s);
          nGammaOverB=n*Gamn/bs(s);
        end
        for j=1:J % poles of Z(zeta)
          snj=snj+1;

          csnj(snj)=czj(j)*kz*vtzs(s)+kz*vs0(s)+n*wcs(s);

          cnj=csnj(snj);
          bj0=vs0(s)+(1-1/lmdT(s))*czj(j)*vtzs(s);

          %
          if(n==0)  % for A_nj
            bnj1=bj0/(czj(j)*vtzs(s)+vs0(s)); % avoid cnj=0
          else
            bnj1=kz*bj0/cnj;
          end
          bnj2=1-bnj1;

          tmp=wps2(s)*bzj(j);

          b11snj(snj)=tmp*bnj2*n2GammaOverB2;
          b11=b11+tmp*bnj1*n2GammaOverB2;

          b12snj(snj)=tmp*bnj2*1i*n*Gamnp;
          b12=b12+tmp*bnj1*1i*n*Gamnp;
          b21snj(snj)=-b12snj(snj);
          b21=-b12;

          b22snj(snj)=tmp*bnj2*(n2GammaOverB2-2*bs2(s)*Gamnp);
          b22=b22+tmp*bnj1*(n2GammaOverB2-2*bs2(s)*Gamnp);

          %
          if(n==0)  % for eta_n*A_nj
            bnj1=0; % avoid cnj=0 when kz=0
          else
            bnj1=n*wcs(s)*bj0/cnj/vtzs(s);
          end
          bnj2=czj(j)/lmdT(s)+bnj1;

          b13snj(snj)=tmp*bnj2*sqrt(2*lmdT(s))*nGammaOverB;
          b13=b13-tmp*bnj1*sqrt(2*lmdT(s))*nGammaOverB;
          b31snj(snj)=b13snj(snj);
          b31=b13;

          b23snj(snj)=-1i*tmp*bnj2*sqrt(2*lmdT(s))*Gamnp*bs(s);
          b23=b23+1i*tmp*bnj1*sqrt(2*lmdT(s))*Gamnp*bs(s);
          b32snj(snj)=-b23snj(snj);
          b32=-b23;

          %
          if(bj0==0)  % for eta_n^2*A_nj
            bnj1=0;
            bnj2=czj(j)*czj(j);
          else
            % bnj1=n^2*bj0/cnj/vtzs(s)^2/kz;
            bnj1=n^2*wcs(s)^2*bj0/cnj/vtzs(s)^2/kz; % !!fixed bug of missed wcs^2, 18-10-01 10:19
            bnj2=(vs0(s)/vtzs(s)+czj(j))*czj(j)/lmdT(s)+...
              n*wcs(s)*bj0*(1-n*wcs(s)/cnj)/vtzs(s)^2/kz;
          end

          b33snj(snj)=tmp*bnj2*2*lmdT(s)*Gamn;
          b33=b33+tmp*bnj1*2*lmdT(s)*Gamn;
        end
      end
    end

    for snj=1:SNJ % set the eigen matrix
      jjx=snj+0*SNJ1;
      jjy=snj+1*SNJ1;
      jjz=snj+2*SNJ1;
      % v_snjx
      M=M+sparse(jjx,jjx,csnj(snj),NN,NN)+...
        sparse(jjx,SNJ3+1,b11snj(snj),NN,NN)+...
        sparse(jjx,SNJ3+2,b12snj(snj),NN,NN)+...
        sparse(jjx,SNJ3+3,b13snj(snj),NN,NN);

      % v_snjy
      M=M+sparse(jjy,jjy,csnj(snj),NN,NN)+...
        sparse(jjy,SNJ3+1,b21snj(snj),NN,NN)+...
        sparse(jjy,SNJ3+2,b22snj(snj),NN,NN)+...
        sparse(jjy,SNJ3+3,b23snj(snj),NN,NN);

      % v_snjz
      M=M+sparse(jjz,jjz,csnj(snj),NN,NN)+...
        sparse(jjz,SNJ3+1,b31snj(snj),NN,NN)+...
        sparse(jjz,SNJ3+2,b32snj(snj),NN,NN)+...
        sparse(jjz,SNJ3+3,b33snj(snj),NN,NN);

    end

    % E(J), J_{x,y,z}=j_{x,y,z}+sum(v_snj{x,y,z})
    tp=-1;
    jj=(0*SNJ1+1):(1*SNJ1); ii=0.*jj+SNJ3+1; M=M+sparse(ii,jj,tp,NN,NN);
    jj=(1*SNJ1+1):(2*SNJ1); ii=0.*jj+SNJ3+2; M=M+sparse(ii,jj,tp,NN,NN);
    jj=(2*SNJ1+1):(3*SNJ1); ii=0.*jj+SNJ3+3; M=M+sparse(ii,jj,tp,NN,NN);

    % jx(E), jy(E), jz(E)
    M=M+sparse(1*SNJ1,SNJ3+1,b11,NN,NN)+...
      sparse(1*SNJ1,SNJ3+2,b12,NN,NN)+...
      sparse(1*SNJ1,SNJ3+3,b13,NN,NN)+...
      sparse(2*SNJ1,SNJ3+1,b21,NN,NN)+...
      sparse(2*SNJ1,SNJ3+2,b22,NN,NN)+...
      sparse(2*SNJ1,SNJ3+3,b23,NN,NN)+...
      sparse(3*SNJ1,SNJ3+1,b31,NN,NN)+...
      sparse(3*SNJ1,SNJ3+2,b32,NN,NN)+...
      sparse(3*SNJ1,SNJ3+3,b33,NN,NN);

    % E(B)
    M=M+sparse(SNJ3+1,SNJ3+5,c2*kz,NN,NN)+...
      sparse(SNJ3+2,SNJ3+4,-c2*kz,NN,NN)+...
      sparse(SNJ3+2,SNJ3+6,c2*kx,NN,NN)+...
      sparse(SNJ3+3,SNJ3+5,-c2*kx,NN,NN);

    % B(E)
    M=M+sparse(SNJ3+4,SNJ3+2,-kz,NN,NN)+...
      sparse(SNJ3+5,SNJ3+1,kz,NN,NN)+...
      sparse(SNJ3+5,SNJ3+3,-kx,NN,NN)+...
      sparse(SNJ3+6,SNJ3+2,kx,NN,NN);
  
    % % -- main program end of set the matrix elements --
