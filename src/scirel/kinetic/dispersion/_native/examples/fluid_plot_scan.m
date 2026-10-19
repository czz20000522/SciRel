% Hua-sheng XIE, huashengxie@gmail.com, IFTS-ZJU, 2013-05-03 22:02
% pdrf.m (Plasma Dispersion Relation - Fluid version), general dispersion
% relation solver for multi-fluid plasma, ver 1.0. Full-matrix method.
%
% B0=(0,0,B0), k=(kx,0,kz), vj0=(vj0x,vj0y,vj0z),
% dln(nj0)=(epsnjx,epsnjy,0)
%
% Ref: 
%  [Xie2014] H. S. Xie, PDRF: A general dispersion relation solver for 
%        magnetized multi-fluid plasma, Computer Physics Communications,
%        185, 670-675 (2014). http://dx.doi.org/10.1016/j.cpc.2013.10.012
%
% test run:
%   close all; clear; clc; 
%   [M,A,w1,w2,kk,ww1,ww2,betasz,vA,csz2,c2,rhos0,wcs,qs,ms,wps,B0]=pdrf_SI;
%
% Note: 
%   Although this solver has been verified under some basic benchmarks,
%   you'd better verify it before use it for more complicated problems.
%   See [Xie2014] for details.
% 
% 2016-04-14 18:56 ver 1.1, fix bugs for:
%        1. roundoff error of eig(), using vpa() sym format
%        2. P\neq0 term, corresponding matrix elements rho_s0 -> n_s0
% Ackn.: Nicholas Francken and Yana Maneva at the KU Leuven in Belgium
%        for the benchmarks report, which is helpful to fix these two bugs.
%
% URL: http://hsxie.me/codes/pdrf/
%


% D1 terminal plot lift; optional PNG byte capture is instrumentation.
set(0,'defaultfigurevisible','off');
if(method>=3)
 h=figure('units','pixels','Position',[50,50,1200,800]);
 set(gcf,'DefaultAxesFontSize',15);
endif;
if(method==2)
 ns=4*s+6;
        for is=1:ns
            clr=colormap(lines);
            clr=clr(floor(is/ns*length(clr)),:);
            subplot(121);
            plot(kk*tmpcwp,real(ww1(:,is))/tmpwcs1,'Color',clr,'LineWidth',2); 
            hold on; 
%             xlabel('k'); ylabel('\omega_r'); xlim([min(kk),max(kk)]);
%             title(['(a) \omega_r vs k, \theta=',...
%                 num2str(theta*180/pi),'^{\circ}']);
            subplot(122); 
            plot(kk*tmpcwp,imag(ww2(:,is))/tmpwcs1,'.','Color',clr,'LineWidth',2); 
            hold on; 
%             xlabel('k'); ylabel('\omega_i'); xlim([min(kk),max(kk)]);
%             title(['(b) \omega_i vs k, m_i/m_e=',num2str(ms(2)/ms(1))]);
        end
        betasz
        betasp

elseif(method==3)
 ns=2*s+1;
        for is=1:ns
            clr=colormap(lines);
            clr=clr(floor(is/ns*length(clr)),:);
            subplot(121);
            plot(tt,real(ww1(:,is)),'x','Color',clr,'LineWidth',2); 
            hold on; xlabel('\theta'); ylabel('\omega_r');
            title(['(c) \omega_r vs \theta, k=',num2str(k)]); 
            xlim([min(tt),max(tt)]);
            subplot(122); 
            plot(tt,imag(ww2(:,is)),'.','Color',clr,'LineWidth',2); 
            hold on; xlabel('\theta'); ylabel('\omega_i'); 
            xlim([min(tt),max(tt)]);
            title('(d) \omega_i vs \theta');
        end
        

elseif(method==4)
 ns=4*s+6;
        subplot(121);
        for is=1:ns
            surf(kkx,kkz,real(ww1(:,:,is))); hold on;
        end
        xlabel('k_x'); ylabel('k_z'); 
        zlabel('\omega_r');

        subplot(122);
        for is=1:ns
            surf(kkx,kkz,imag(ww2(:,:,is))); hold on;
        end
        xlabel('k_x'); ylabel('k_z'); 
        zlabel('\omega_i');  
        

endif;
plot_line_count=length(findall(0,'type','line'));
plot_surface_count=length(findall(0,'type','surface'));
png_bytes=zeros(0,1,'uint8');
if capture_png && method>=2 && method<=4;
scirel_prepare_plot(gcf);
 print(gcf,'-dpng','-S1200,800','fluid_terminal.png');
 fp=fopen('fluid_terminal.png','rb');png_bytes=fread(fp,Inf,'*uint8');fclose(fp);
endif;
