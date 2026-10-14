%% for plot
close all;
h=figure('units','pixels','Position',[50,50,1200,800],...
  'DefaultAxesFontSize',15);
pltc=[0.0  1.0  0.0 % different colors
  1.0  0.0  0.0
  0.2  0.2  1.0
  0.8 0.8 0.0
  1.0  0.6  0.0
  0.9  0.0  0.9
  0.0  0.8  0.8
  0.0  0.0  0.0
  0.6  0.0  0.0
  0.4  0.7  0.4 
  0.0  0.0  0.5 
  0.6  0.0  0.6 
  0.0  0.5  1.0
  ];
% for jpl=1:2
for jpl=1:npl
    
  if(ipa==ipb) % 1D plot
      subplot(121); hold on;
      if(iloga==0)
        plot(rex*pas,rez*real(wws(:,1,jpl)),'--','Color',...
            pltc(jpl,:),'linewidth',2);
        xlim([rex*min(pas),rex*max(pas)]);
      else
        semilogx(rex*10.^pas,rez*real(wws(:,1,jpl)),'--',...
            'Color',pltc(jpl,:),'linewidth',2);
        %xlim([10^min(pas),10^max(pas)]); 
      end
      box on; grid on; % ylim([-2.5e3,2.0e3]);
      xlabel([num2str(rex),'*',strpa,', npa=',num2str(npa)]);
      title(['(a) \beta_{||}=',num2str(betasz,3),...
        ', \beta_\perp=',num2str(betasp,3)]);
      ylabel([num2str(rez),'*\omega_r/\omega_{c1}, \alpha=',num2str(alphas,3)]);
      
      subplot(122); hold on;
      if(iloga==0)
        plot(rex*pas,rez*imag(wws(:,1,jpl)),'--',...
            'Color',pltc(jpl,:),'linewidth',2);
        xlim([rex*min(pas),rex*max(pas)]);
      else  
        semilogx(rex*10.^pas,rez*imag(wws(:,1,jpl)),'--',...
            'Color',pltc(jpl,:),'linewidth',2);
        %xlim([10^min(pas),10^max(pas)]);
      end
      box on; grid on; %ylim([-0.4e4,0.1e4]);
      xlabel([num2str(rex),'*',strpa,', iem=',num2str(iem)]);
      ylabel([num2str(rez),'*\omega_i/\omega_{c1}, \Delta=',num2str(Deltas,3)]);
      title(['(b) v_A/c=',num2str(vA/sqrt(c2),2),', ',strpb,'=',...
        num2str(par(ipbtmp)),', (S=',num2str(S),',N=',num2str(N),...
        ',J=',num2str(J),')']);
  else
    subplot(121);
    wwjp=squeeze(wws(:,:,jpl));
    surf(rex*ppa,rey*ppb,rez*real(wwjp)); hold on; box on; set(gca,'BoxStyle','full');
    xlabel([num2str(rex),'*',strpa,',ilogx=',num2str(iloga)]);
    ylabel([num2str(rey),'*',strpb,',ilogy=',num2str(ilogb)]);axis tight;
    zlabel([num2str(rez),'*\omega_r/\omega_{c1},npa=',num2str(npa),',npb=',num2str(npb)]);
    title(['(a) \beta_{||}=',num2str(betasz,3),...
      ', \beta_\perp=',num2str(betasp,3)]);
    subplot(122);
    surf(rex*ppa,rey*ppb,rez*imag(wwjp)); hold on; box on;set(gca,'BoxStyle','full');
    xlabel([num2str(rex),'*',strpa]); ylabel([num2str(rey),'*',strpb]); axis tight;
    zlabel([num2str(rez),'*\omega_i/\omega_{c1},S=',num2str(S),',N=',num2str(N),...
        ',J=',num2str(J)]);
    % zlim([-0.1,0.1]);
    title(['(b) runtime=',num2str(runtime),'s']);

  end
  
end

scirel_prepare_plot(gcf);
print(gcf,'-dpng','-S1200,800',[savepath,'fig_pdrk_',figstr,'_select.png']);
savefig([savepath,'fig_pdrk_',figstr,'_select.fig']);
