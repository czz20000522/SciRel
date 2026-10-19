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
    
