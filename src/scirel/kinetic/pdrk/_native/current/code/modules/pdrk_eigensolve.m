% Lifted exact D0 pdrk_kernel.m eigensolve/growth-sort block.
    % calculate the solution use either eig() or eigs()
    if(sp==0) % solve all the roots, slow for large N
      % d=eig(full(M));
% D2: wrapping an already computed double eigenvalue does not add precision.
      d0=eig(full(M));d=d0;
    else % solve only nw solutions, fast for large N, similar to WHAMP
      % d=eigs(M,nw,wg);
      if(iem==1 && iout==2 && icalp==1) % for pdrk_output.m
        disp(['jpa=',num2str(jpa),', jpb=',num2str(jpb)]);
        eps=1i*1e-8; % 18-10-06 10:29
        wg=wws(jpa,jpb,jpl)*wcs1+eps; % add eps to avoid singular warning
        %d0=eigs(M,nw,wg);d=d0;
        [V,D]=eigs(M,nw,wg);
        %[V0,D0]=vpa(eigs(M,nw,wg)); V=double(V0); D=double(D0);
        % D2: the new eigenpair owns frequency/state, not predecessor d.
        d=diag(D); d0=d;
        [dEB,UE,UB]=pdrk_normalize_field_mode(V((NN-5):NN,1),epsilon0,mu0);
        Pola(jpa,jpb,jpl,1:6)=dEB; % store dEB
        wws2(jpa,jpb,jpl)=D(1,1)/wcs1; % store new wws, in case
        
        dEx=dEB(1);
        dEy=dEB(2);
        dEz=dEB(3);
        dBx=dEB(4);
        dBy=dEB(5);
        dBz=dEB(6);
        % D2: UE and UB are owned by the same checked normalization helper.
        Pola(jpa,jpb,jpl,7)=UE;
        Pola(jpa,jpb,jpl,8)=UB;
        
        % kdotE=abs(kx*dEx+kz*dEz); % to add more
        % kcrossE=abs(sqrt((-kz*dEy)^2+(kz*dEx-kx*dEz)^2+(kx*dEy)^2)); %
        % abs(k \dot E), abs(k \times E)
        % Pola(jpa,jpb,jpl,9)=kdotE; %
        % Pola(jpa,jpb,jpl,10)=kcrossE; %
        
      else % calcute also the polarizations
        d0=eigs(M,nw,wg);d=d0;
      end
    end
    omega=d;
    [wi,ind]=sort(imag(omega),'descend'); % sort the solution by growth rate
    w=omega(ind);
    wg=w(1); % update the initial guess for pa(jpa,jpb+1) use previous solution
    
