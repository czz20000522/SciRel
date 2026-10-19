function artifacts=fb_em_plot(result,jplt)
% Source-derived, dimensionally corrected labels; source em3d_Lpole.m:250-302 graphical and MAT outputs; default jplt2.
if nargin<2, jplt=2; end
fb_unpack_workspace(result,{'kxx','xx','kn','wn','kz','N','S','B0','n00','T00','ns_unit','ms','me','qs','qe','Ts_unit','jcase'});
%%
close all;
h=figure('unit','normalized','Position',[0.01 0.05 0.5 0.5],...
  'DefaultAxesLineWidth',2,...
  'DefaultAxesFontSize',14);
if(jplt==1)
  subplot(121);
  plot(real(kxx(:,1))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(real(kxx(:,2))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(real(kxx(:,3))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(real(kxx(:,4))/kn,xx/wn,'x','LineWidth',2); hold on;
  xlim([0,5]);ylim([0,5]);
  xlabel('Re(k_\perp)/k_n');ylabel('\omega/\omega_n');
  subplot(122);
  plot(abs(imag(kxx(:,1)))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(abs(imag(kxx(:,2)))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(abs(imag(kxx(:,3)))/kn,xx/wn,'x','LineWidth',2); hold on;
  plot(abs(imag(kxx(:,4)))/kn,xx/wn,'x','LineWidth',2); hold on;
  % xlim([0,5]);
  ylim([0,5]);
  xlabel('|Im(k_\perp)|/k_n');ylabel('\omega/\omega_n');
else
  subplot(121);
  semilogy(xx/wn,real(kxx(:,1)),'x','LineWidth',2); hold on;
  semilogy(xx/wn,real(kxx(:,2)),'x','LineWidth',2); hold on;
  % semilogy(xx/wn,real(kxx(:,3)),'x','LineWidth',2); hold on;
  % semilogy(xx/wn,real(kxx(:,4)),'x','LineWidth',2); hold on;
  xlim([0,5]);
  % ylim([1e0,1e4]);
  ylabel('Re(k_\perp) [m^{-1}]');xlabel('\omega/\omega_n');
  subplot(122);
  semilogy(xx/wn,abs(imag(kxx(:,1))),'x','LineWidth',2); hold on;
  semilogy(xx/wn,abs(imag(kxx(:,2))),'x','LineWidth',2); hold on;
  % semilogy(xx/wn,abs(imag(kxx(:,3))),'x','LineWidth',2); hold on;
  % semilogy(xx/wn,abs(imag(kxx(:,4))),'x','LineWidth',2); hold on;
  xlim([0,5]);
  % ylim([1e0,1e4]);
  ylabel('|Im(k_\perp)| [m^{-1}]');xlabel('\omega/\omega_n');
end
title(['k_z=',num2str(kz),', N=',num2str(N)]);

filename=['em3d_Lpole_S=',num2str(S),',B0=',num2str(B0,3),...
  ',n00=',num2str(n00,3),',T00=',num2str(T00,3),',ns=',num2str(ns_unit,3),...
  ',ms=',num2str(ms/me,4),',qs=',num2str(qs/qe,3),...
  ',Ts=',num2str(Ts_unit,3),',k_z=',num2str(kz,3),',N=',num2str(N),'.png']; print(gcf,'-dpng',filename);

if(jcase==1)
  matfile=['ICW_Lpole_kz=',num2str(kz),'_N=',num2str(N),'.mat']; save(matfile,'kxx','xx','kn','wn','kz','N');
  % save('BW_Lpole.mat','kxx','xx','kn','wn','kz','N');
else
  matfile=['ECW_Lpole_kz=',num2str(kz),'_N=',num2str(N),'.mat']; save(matfile,'kxx','xx','kn','wn','kz','N');
end
artifacts=struct('figures',findall(0,'type','figure'),'files',{{filename,matfile}});
end
