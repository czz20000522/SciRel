% D1 EM1D downstream plot source lines32-48, arithmetic unchanged.

% figure;set(gcf,'DefaultAxesFontSize',15);
% plot(k*cwp,wre/wci,'r+',k*cwp,wie/wci,'o','LineWidth',2);
subplot(121); hold on;
plot(k*cwp,wre/wcs1,'k+','LineWidth',2);
subplot(122); hold on;
plot(k*cwp,wie/wcs1,'k+','LineWidth',2);
grid on;
% xlabel('kc/\omega_{pi}');ylabel('\omega/\omega_{cp}');
% xlim([kmin,kmax]); title('EM1D \theta=0');
%%
if(pm==-1)
subplot(121);
legend('pdrk-1','pdrk-2','pdrk-3','pdrk-4','EM1D DR-1','EM1D DR-2',...
    'location','northwest'); legend('boxoff');
end
% legend('\omega_r','\gamma','location','northwest'); legend('boxoff');
