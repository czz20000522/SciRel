run pdrk_polarization;
% % To do: add group velocity, etc, 18-10-18 15:00
%%
close all;
if(iout==2)
h=figure('units','pixels','Position',[50,50,1200,800],...
  'DefaultAxesFontSize',15);
for jpl=1:npl1
    if(ipa==ipb) % plot 1D polarizations, to update. 2018-10-19 18:10
      subplot(331); hold on; box on;
      plot(pas,real(wws2(:,1,jpl)),'-','Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]); %ylim([-2.5,1.0]);
      xlabel(strpa);ylabel('\omega_r/\omega_{c1}');
      
      subplot(332); hold on; box on;
      plot(pas,imag(wws2(:,1,jpl)),'-','Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('\omega_i/\omega_{c1}');
      
      subplot(333); hold on; box on;
      plot(pas,Pola(:,1,jpl,7)./Pola(:,1,jpl,8),'-','Color',...
          pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('Energy E/Energy B');
      
      subplot(334); hold on; box on;
      plot(pas,real(Pola(:,1,jpl,2)./(1i*Pola(:,1,jpl,1))),'-','Color',...
          pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('E_y/(iE_x)');
      
      subplot(335); hold on; box on;
      plot(pas,real(Pola(:,1,jpl,1)),'-','Color',pltc(jpl,:),'linewidth',2);
      hold on;
      plot(pas,imag(Pola(:,1,jpl,1)),'--','Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('E_x');
      legend('Re','Im'); legend('boxoff');
      
      subplot(336); hold on; box on;
      plot(pas,real(Pola(:,1,jpl,2)),'-','Color',pltc(jpl,:),'linewidth',2);
      hold on;
      plot(pas,imag(Pola(:,1,jpl,2)),'--','Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('E_y');
      
      subplot(337); hold on; box on;
      plot(pas,real(Pola(:,1,jpl,3)),'-','Color',pltc(jpl,:),'linewidth',2);
      hold on;
      plot(pas,imag(Pola(:,1,jpl,3)),'--','Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('E_z');
      
      subplot(338); hold on; box on;
      plot(pas,sqrt(c2)*real(Pola(:,1,jpl,4)),'-',...
          'Color',pltc(jpl,:),'linewidth',2);
      hold on;
      plot(pas,sqrt(c2)*imag(Pola(:,1,jpl,4)),'--',...
          'Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('c*B_x');
      
      subplot(339); hold on; box on;
      plot(pas,sqrt(c2)*real(Pola(:,1,jpl,6)),'-',...
          'Color',pltc(jpl,:),'linewidth',2);
      hold on;
      plot(pas,sqrt(c2)*imag(Pola(:,1,jpl,6)),'--',...
          'Color',pltc(jpl,:),'linewidth',2);
      xlim([min(pa),max(pa)]);
      xlabel(strpa);ylabel('c*B_z');
    else % plot 2D polarizations, to update
      
      wwjp=squeeze(wws2(:,:,jpl));
      Polajp=squeeze(Pola(:,:,jpl,:));
      
      subplot(221);
      surf(ppa,ppb,real(wwjp)); hold on; box on; set(gca,'BoxStyle','full');
      xlabel([strpa,',ilogx=',num2str(iloga)]);
      ylabel([strpb,',ilogy=',num2str(ilogb)]);axis tight;
      zlabel('\omega_r/\omega_{c1}');
      
      subplot(222);
      surf(ppa,ppb,imag(wwjp)); hold on; box on;set(gca,'BoxStyle','full');
      xlabel(strpa); ylabel(strpb); axis tight;
      zlabel('\omega_i/\omega_{c1}');
    
      EyoveriEx=Polajp(:,:,2)./(1i*Polajp(:,:,1));
      
      subplot(223);
      surf(ppa,ppb,real(EyoveriEx));
      hold on; box on;set(gca,'BoxStyle','full');
      xlabel(strpa); ylabel(strpb); axis tight;
      zlabel('Re[E_y/(iE_x)]');
      
      subplot(224);
      surf(ppa,ppb,imag(EyoveriEx));
      hold on; box on;set(gca,'BoxStyle','full');
      xlabel(strpa); ylabel(strpb); axis tight;
      zlabel('Im[E_y/(iE_x)]');
      
    end
end

scirel_prepare_plot(gcf);
print(gcf,'-dpng','-S1200,800',[savepath,'fig_pdrk_',figstr,'_pola.png']);
savefig([savepath,'fig_pdrk_',figstr,'_pola.fig']);

end

filename=['out_pdrk_S=',num2str(S),'_J=',num2str(J),...
    '_N=',num2str(N),'_B0=',num2str(B0),'.mat'];

allvars=whos;
tosave=cellfun(@isempty, regexp({allvars.class}, ...
    '^matlab\.(ui|graphics)\.')); % save workspace exclude figure(s)
save([savepath,filename], allvars(tosave).name); 
