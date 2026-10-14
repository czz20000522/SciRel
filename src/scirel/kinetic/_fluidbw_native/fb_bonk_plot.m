function artifacts=fb_bonk_plot(result)
% Exact source graphical/material action main_tst.m:114-179.
fb_unpack_workspace(result,{'jcase','xx','wcn','nf','S','B0','kz','n00','T00','ns_unit','ms','me','qs','qe','Ts_unit','nx','runtime'});
if(jcase==1)

close all;
h=figure('unit','normalized','Position',[0.01 0.05 0.5 0.7],...
    'DefaultAxesLineWidth',2,...
    'DefaultAxesFontSize',14);
% subplot(2,2,[1,3]);

ax1=axes('position',[0.1,0.1,0.4,0.8]);
semilogy(xx/wcn,real(nf(:,1)),'.',...
    'linewidth',3,'Markersize',12);
hold on;
semilogy([1,1],[1e-2,1e4],'k:',[2,2],[1e-2,1e4],'k:',...
    [3,3],[1e-2,1e4],'k:',[4,4],[1e-2,1e4],'k:','linewidth',1);
ylim([1e0,1e4]);

xlabel('\omega/\omega_{ci}');
ylabel('Re(k_\perp) [m^{-1}]');
title(['S=',num2str(S),', B_0=',num2str(B0,3),'T, k_z=',num2str(kz,3),...
    'm^{-1}, n_{00}=',num2str(n00,3),'m^{-3}, T_{00}=',num2str(T00,3),'eV,',10, ...
    'n_s=[',num2str(ns_unit,3),'], m_s/m_e=[',num2str(ms/me,4),...
    '], q_s/q_e=[',num2str(qs/qe,3),...
    '], T_s/T_{00}=[',num2str(Ts_unit,3),']']);

% subplot(224);
ax3=axes('position',[0.62,0.1,0.35,0.3]);
semilogy(xx/wcn,abs(imag(nf(:,1))),'b.',...
    'linewidth',3,'Markersize',12);hold on;
% semilogy([1,1],[1e-2,1e4],'k:',[2,2],[1e-2,1e4],'k:',...
%     [3,3],[1e-2,1e4],'k:',[4,4],[1e-2,1e4],'k:','linewidth',1);
% ylim([1,1e3]);
xlabel('\omega/\omega_{cn}');ylabel('|Im(k_\perp)| [m^{-1}]');
% 
% ax3=axes('position',[0.62,0.1,0.35,0.3]);
% semilogy(xx/wci,-1./imag(nf(:,2)),'r.',...
%     'linewidth',3,'Markersize',12);hold on;

title(['nx=',num2str(nx),', runtime=',num2str(runtime,3),'s']);
% semilogy([1,1],[1e-2,1e4],'k:',[2,2],[1e-2,1e4],'k:',...
%     [3,3],[1e-2,1e4],'k:',[4,4],[1e-2,1e4],'k:','linewidth',1);
% ylim([-1e1,1e1]);
% ylim([0.1,1e2]);
% xlabel('\omega/\omega_{ci}');ylabel('-Im(k_\perp)^{-1} [m]');

% save figure
% set(gcf,'Units','inches');
% screenposition = get(gcf,'Position');
% set(gcf,'PaperPosition',[0 0 screenposition(3:4)],...
%   'PaperSize',[screenposition(3:4)]);

filename=['bonkR_S=',num2str(S),',B0=',num2str(B0,3),...
    ',n00=',num2str(n00,3),',T00=',num2str(T00,3),',ns=',num2str(ns_unit,3),...
    ',ms=',num2str(ms/me,4),',qs=',num2str(qs/qe,3),...
    ',Ts=',num2str(Ts_unit,3),',k_z=',num2str(kz,3),'.png']; print(gcf,'-dpng',filename);

else

subplot(121);
plot(xx/wcn,abs(real(nf(:,1))),'r:x');
set(gca,'yscale','linear');
xlabel('\omega/\omega_n'); ylabel('|Re(k_\perp)| [m^{-1}]');
subplot(122);
plot(xx/wcn,abs(imag(nf(:,1))),'r:x');
set(gca,'yscale','log');
xlabel('\omega/\omega_n'); ylabel('|Im(k_\perp)| [m^{-1}]');
filename=['bonkR_case',num2str(jcase),'.png']; print(gcf,'-dpng',filename);
% ylim([0,5]);xlim([0,5]);
% xlabel('k_\perp');ylabel('\omega_r');
end
artifacts=struct('figures',findall(0,'type','figure'),'files',{{filename}});
end
