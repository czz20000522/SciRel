function matM=fb_em_matrix(state,poles,w,N)
% Source em3d_Lpole.m:150-236: EM3D L-pole matrix in kx eigenproblem.
% SI physical ports in state, w rad/s; default N6, source supported table n0..7.
if nargin<4, N=6; end
fb_validate_state(setfield(state,'w',w));
if ~isscalar(N)||N~=fix(N)||N<0||N>7, error('fluidbw:table','N must be an integer in 0..7'); end
fb_unpack_workspace(state,{'S','c2','wcs','wps2','rhocs','kz','vts','epsilon0'}); fb_unpack_workspace(poles,{'J','L','cn','bzj','czj'});
absrhocs=abs(rhocs); sgns=sign(rhocs);
if ~isfield(state,'epsilon0')||~isnumeric(epsilon0)||~isscalar(epsilon0)||~isreal(epsilon0)||~isfinite(epsilon0)||epsilon0<=0
 error('fluidbw:state','positive finite SI epsilon0 required'); end
% w is explicit; state may carry no source loop-frequency w.
  nL=sum(L(1:(N+1)));
  NSL=S*nL;
  NSL3=3*NSL;
  NN=NSL3+4;
  matM=zeros(NN,NN);

  % kx*X=M*X, with X=[vxsl,vys,vzsl,Ey,Ez,By,Bz], Jx=sum(vxsl),
  % Jy=sum(vysl), Jz=sum(vzsl)
  snl=0;
  for s=1:S
    xsj=zeros(J,1);
    for j=1:J
      xsj(j)=(w-abs(kz)*vts(s)*czj(j))/wcs(s);
    end

    for n=0:N
      for l=1:L(abs(n)+1)
        snl=snl+1;
        pln=cn{abs(n)+1}.pl(l);
        rln=cn{abs(n)+1}.rl(l);
        csnl=pln/abs(rhocs(s));

        ctmpxx=0; ctmpxy=0; ctmpxz=0;
        ctmpyy=0; ctmpyz=0; ctmpzz=0;
        for j=1:J
          ctmpxx=ctmpxx+bzj(j)/pln^2*(n^2*xsj(j)/(xsj(j)^2-n^2));
          ctmpxy=ctmpxy+bzj(j)*( ...
            0.5*(n+1)^2/(xsj(j)^2-(n+1)^2)- ...
            (n>=1)*n^2/(xsj(j)^2-n^2)+ ...
            (n>=2)*0.5*(n-1)^2/(xsj(j)^2-(n-1)^2));
          ctmpxz=ctmpxz+sgns(s)/pln*bzj(j)*czj(j)*(n^2/(xsj(j)^2-n^2));
          ctmpyy=ctmpyy+bzj(j)*(xsj(j)/pln^2*n^2/(xsj(j)^2-n^2)+ ...
            pln^2/xsj(j)*( -(n+1)^2/(xsj(j)^2-(n+1)^2)+ ...
            (n>=1)*2*n^2/(xsj(j)^2-n^2)- ...
            (n>=2)*(n-1)^2/(xsj(j)^2-(n-1)^2)));
          ctmpyz=ctmpyz+sgns(s)*pln*bzj(j)*czj(j)/xsj(j)*( ...
            0.5*(n+1)^2/(xsj(j)^2-(n+1)^2)- ...
            (n>=1)*n^2/(xsj(j)^2-n^2)+ ...
            (n>=2)*0.5*(n-1)^2/(xsj(j)^2-(n-1)^2));
          ctmpzz=ctmpzz+bzj(j)*czj(j)^2*xsj(j)*( ...
            1+(n>=1))/(xsj(j)^2-n^2);
        end
        if any(~isfinite([ctmpxx,ctmpxy,ctmpxz,ctmpyy,ctmpyz,ctmpzz])), error('fluidbw:pole','singular rational response'); end

        btmp=epsilon0*wps2(s)/wcs(s)*rln/absrhocs(s);
        blxx=-2i*btmp*ctmpxx;
        blxy=2*btmp*ctmpxy;
        blyx=-blxy;
        blxz=-2i*sqrt(2)*sign(kz)*btmp*ctmpxz;
        blzx=blxz;
        blyy=-2i*btmp*ctmpyy;
        blyz=-2*sqrt(2)*sign(kz)*btmp*ctmpyz; % signed causal reflection
        blzy=-blyz;
        blzz=-2i*btmp*ctmpzz;

        % v_snl,v_snl
        matM(snl,snl)=matM(snl,snl)+csnl; % x
        matM(NSL+snl,NSL+snl)=matM(NSL+snl,NSL+snl)+csnl; % y
        matM(2*NSL+snl,2*NSL+snl)=matM(2*NSL+snl,2*NSL+snl)+csnl; % z

        matM(0*NSL+snl,NSL3+1)=blxy; % vx_snl,Ey
        matM(0*NSL+snl,NSL3+2)=blxz; % vx_snl,Ez
        matM(0*NSL+snl,NSL3+3)=kz*c2/w*blxx; % vx_snl,By
        matM(1*NSL+snl,NSL3+1)=blyy; % vy_snl,Ey
        matM(1*NSL+snl,NSL3+2)=blyz; % vy_snl,Ez
        matM(1*NSL+snl,NSL3+3)=kz*c2/w*blyx; % vy_snl,By
        matM(2*NSL+snl,NSL3+1)=blzy; % vz_snl,Ey
        matM(2*NSL+snl,NSL3+2)=blzz; % vz_snl,Ez
        matM(2*NSL+snl,NSL3+3)=kz*c2/w*blzx; % vz_snl,By

        for lp=1:NSL % vxyz_snl, vx_snl'
          matM(0*NSL+snl,lp)=matM(0*NSL+snl,lp)-1i/(w*epsilon0)*blxx;
          matM(1*NSL+snl,lp)=matM(1*NSL+snl,lp)-1i/(w*epsilon0)*blyx;
          matM(2*NSL+snl,lp)=matM(2*NSL+snl,lp)-1i/(w*epsilon0)*blzx;
        end

        matM(NSL3+2,0*NSL+snl)=-1i*kz/(w*epsilon0); % (Ez,Jx), Jx=sum{vx_snl}
        matM(NSL3+3,2*NSL+snl)=-1i/(c2*epsilon0); % (By,Jz), Jz=sum{vz_snl}
        matM(NSL3+4,1*NSL+snl)=1i/(c2*epsilon0); % (Bz,Jy), Jy=sum{vy_snl}
      end
    end
  end

  % Ey,Ez,By,Bz
  matM(NSL3+1,NSL3+4)=w; % (Ey,Bz)
  matM(NSL3+2,NSL3+3)=kz^2*c2/w-w; % (Ez,By)
  matM(NSL3+3,NSL3+2)=-w/c2; % (By,Ez)
  matM(NSL3+4,NSL3+1)=w/c2-kz^2/w; % (Bz,Ey)
  % D2 scientific correction: polynomial parts of z^2 Gamma_L and z Gamma_L
  % were dropped by source partial-fraction assembly. Preserve the proper-pole
  % blocks and restore the finite rational Maxwell relation by four additions.
  % Gamma'_n here is the neighbor mapping, NOT the derivative of a fitted
  % rational function. m=0 counted once, m>0 with both signed harmonics;
  % derivative support includes +/- (N+1). Independent derivation/validation
  % and the before matrix are preserved in this D2 handoff.
  A=0; B=0; C=0;
  for s=1:S
    for j=1:J
      Y=(w-abs(kz)*vts(s)*czj(j))/wcs(s);
      for m=0:N
        if m==0, signed_m=0; else, signed_m=[m,-m]; end
        cm=sum(0.5./(Y-signed_m-1)+0.5./(Y-signed_m+1)-1./(Y-signed_m));
        am=sum(cn{m+1}.rl); bm=sum(cn{m+1}.rl.*cn{m+1}.pl);
        prefactor=wps2(s)/(w*wcs(s))*bzj(j)*cm;
        A=A-2*prefactor*abs(rhocs(s))*am;
        B=B-2*prefactor*bm;
        C=C-1i*sqrt(2)*prefactor*sign(kz)*sgns(s)*czj(j)*am;
      end
    end
  end
  alpha=-1i*w*epsilon0*A; beta=-1i*w*epsilon0*B; gamma=-1i*w*epsilon0*C;
  matM(NSL3+3,NSL3+1)=matM(NSL3+3,NSL3+1)+1i*gamma/(c2*epsilon0);
  matM(NSL3+4,NSL3+1)=matM(NSL3+4,NSL3+1)+1i*beta/(c2*epsilon0);
  matM(NSL3+4,NSL3+2)=matM(NSL3+4,NSL3+2)+1i*gamma/(c2*epsilon0);
  matM(NSL3+4,NSL3+4)=matM(NSL3+4,NSL3+4)+1i*alpha*w/(c2*epsilon0);
  if any(~isfinite(matM(:))), error('fluidbw:pole','nonfinite finite rational matrix'); end
end
