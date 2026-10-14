% 18-10-05 16:42 Hua-sheng XIE, huashengxie@gmail.com, FRI-ENN, China
% Try a stratege to select given dispersion surface. Steps:
% 1. select a initial point in the solutions, e.g., (k,w_j)
% 2. determined the corresponding w_j for other k, use interp or least
% squre, or nearest neighbor
% 3. store the (k,w_j) as one dispersion surface
% 4. repeat the above step for another surface
% better for smaller dk
% 18:41 Test 1D nearest neighbor can work, but not well for omega past zero
% 19:33 try interp1, works very well!
% 18-10-06 00:48 2D scan not perfect yet

% % Search the most close dispersion surfaces to these data.
% % Initial data for find the corresponding dispersion surfaces.
% % Please use pdrk_plot_all.m to visualize all the solutions, and then
% % modify here the initial point of which mode(s) you want plot/store.
% if(ipa==ipb) % for 1D scan case
% % wpdat(:,1) is pa; wpdat(:,2) is arbitrary; wpdat(:,3) is Re or Im(omega)
% wpdat=[
%     %80,0,-0.061i; % theta=75
%     83.5,0,5.7e5;
%   68.5,0,-3.23e2*1i;
%   56,5,-2.45e2*1i];
% % wpdat=[0.65,0,-0.45i;
% %   0.4,0,-0.37i;
% %   0.8,0,-1.75i]; % modify here for other dispersion surfaces
% else % for 2D scan case
%     % wpdat(:,1) is pa; wpdat(:,2) is pb; wpdat(:,3) is Re or Im(omega)
% wpdat=[70,0,-152i;
%   90.5,85,-261.5i;
%   94.5,85,-433i];
% end

% run ../input/pdrk_wpdat;

% % find the most unstable/least damped solution
% maxgam=max(max(max(imag(wwn))));
% [indww,indpa,indpb]=find(imag(wwn)==maxgam);
% wpdat=[pa(indpa),pb(indpb),maxgam*1i;
%     wpdat]; % alway plot the most unstable dispersion surface

% [npl,nplb]=size(wpdat);
npl=size(wpdat,1); % 18-10-27 14:27
wws=zeros(npa,npb,npl);

%% This module is to search the same dispersion surface(s) of 'wpdat'
for jpl=1:npl
% for jpl=2:2

  datstart=wpdat(jpl,:);

  if(ipa==ipb) % 1D plot
      
      % determine the start point solution
      indpa=find(abs(pa-datstart(1))==min(abs(pa-datstart(1)))); 
      indpa=indpa(1);
      pastart=pa(indpa); % pa=k/cwp, etc

      if(real(datstart(3))==0) % search by imag part if real part equal 0
        indww=find(abs(imag(wwn(indpa,1,:))-imag(datstart(3)))==...
          min(abs(imag(wwn(indpa,1,:))-imag(datstart(3)))));
      else % search by real part
        indww=find(abs(real(wwn(indpa,1,:))-real(datstart(3)))==...
          min(abs(real(wwn(indpa,1,:))-real(datstart(3)))));
      end
      indww=indww(1);
      wwstart=wwn(indpa,1,indww); % wwn=ww/wcs1;

      % determine the solution for next parameter a
      jj=1:npa; pas=0.*jj; ws=0.*jj;
      jjpa=indpa; jjww=indww; pas(indpa)=pa(indpa); ws(indpa)=wwstart;
      while(length(jjpa)<npa)
        jjpa0=jjpa;
        if(max(jjpa)<npa) % seach the right direction of pa
          indm=max(jjpa);
          indpa=indm+1;
          jjpa=[jjpa,indpa];
        else % seach the left direction of pa
          indm=min(jjpa);
          indpa=indm-1;
          jjpa=[indpa,jjpa];
        end
        if(length(jjpa)<=2)
          wpred=ws(indm); % nearest neighbor
        else % interp1 to give the best guess
          wpred=interp1(pas(jjpa0),ws(jjpa0),pa(indpa),...
              'pchip','extrap'); % try 'cubic', 'spline' or 'pchip'
        end
        indww=find(abs(wwn(indpa,1,:)-wpred)==...
          min(abs(wwn(indpa,1,:)-wpred))); % find next solution
        indww=indww(1);
        jjww=[jjww,indww];
        pas(indpa)=pa(indpa);
        ws(indpa)=wwn(indpa,1,indww);
      end
      wws(1:npa,1,jpl)=ws(1:npa); % store the solutions

  else % 2D plot
      
      % determine the start point solution
      indpa=find(abs(pa-datstart(1))==min(abs(pa-datstart(1)))); 
      indpa=indpa(1);
      pastart=pa(indpa); % pa start point for search
      indpb=find(abs(pb-datstart(2))==min(abs(pb-datstart(2)))); 
      indpb=indpb(1);
      pbstart=pb(indpb); % pb start point for search

      if(real(datstart(3))==0) % search by imag part if real part equal 0
        indww=find(abs(imag(wwn(indpa,indpb,:))-imag(datstart(3)))==...
          min(abs(imag(wwn(indpa,indpb,:))-imag(datstart(3)))));
      else % search by real part
        indww=find(abs(real(wwn(indpa,indpb,:))-real(datstart(3)))==...
          min(abs(real(wwn(indpa,indpb,:))-real(datstart(3)))));
      end
      indww=indww(1);
      wwstart=wwn(indpa,indpb,indww); % wwn=ww/wcs1;
      
      % determine the solution for next parameter a, b
      ws=zeros(npa,npb); ws(indpa,indpb)=wwstart;
      jjpb=indpb; wpredb=wwstart; indpa0=indpa; indpb0=indpb;
      while(length(jjpb)<=npb)
          
          indpa=indpa0; jjpa=indpa; jjww=indww; jstart=1;
          while(length(jjpa)<npa || jstart==1) % for next parameter a
            jjpa0=jjpa;
               
            if(jstart==1)
               wpred=wpredb;
               jstart=0;
            else
                if(max(jjpa)<npa) % seach the right direction of pa
                  indm=max(jjpa);
                  indpa=indm+1;
                  jjpa=[jjpa,indpa];
                else % seach the left direction of pa
                  indm=min(jjpa);
                  indpa=indm-1;
                  jjpa=[indpa,jjpa];
                end
                if(length(jjpa)<=2)
                  wpred=ws(indm,indpb); % nearest neighbor
                else % interp1 to give the best guess.
                  wpred=interp1(pa(jjpa0),squeeze(ws(jjpa0,indpb)),...
                      pa(indpa),'pchip','extrap'); % 'pchip', 'cubic', 'spline'
                end
            end
            indww=find(abs(wwn(indpa,indpb,:)-wpred)==...
              min(abs(wwn(indpa,indpb,:)-wpred))); % find next solution
            indww=indww(1);
            jjww=[jjww,indww];
            ws(indpa,indpb)=wwn(indpa,indpb,indww);
          end
          
          % % for next parameter b
          jjpb0=jjpb;
          if(max(jjpb)<npb) % seach the right direction of pb
              indbm=max(jjpb);
              indpb=indbm+1;
              jjpb=[jjpb,indpb];
          else % seach the left direction of pb
              indbm=min(jjpb);
              indpb=indbm-1;
              jjpb=[indpb,jjpb];
          end
          
          if(length(jjpb)<=npb)
              if(length(jjpb)<=2)
                wpredb=ws(indpa0,indbm); % nearest neighbor
              else % interp1 to give the best guess. To do: how about interp2?
                wpredb=interp1(pb(jjpb0),squeeze(ws(indpa0,jjpb0)),...
                    pb(indpb),'pchip','extrap'); % 'pchip', 'cubic', 'spline'
              end
          end
          
      end
      wws(1:npa,1:npb,jpl)=ws(1:npa,1:npb); % store the solutions
  end
  
end

