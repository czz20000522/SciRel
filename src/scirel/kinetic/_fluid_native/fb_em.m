function result=fb_em(jcase,J,N,xx,plot_outputs,jplt)
% Ordered native TaskGraph state+poles -> matrices -> roots -> optional source IO.
if nargin<1, jcase=2; end
if nargin<2, J=8; end
if nargin<3, N=6; end
if nargin<5, plot_outputs=false; end
if nargin<6, jplt=2; end
state=fb_em_parameters(jcase); poles=fb_em_poles(J);
if nargin<4, result=fb_em_sweep(state,poles,N); else, result=fb_em_sweep(state,poles,N,xx); end
if plot_outputs, fb_em_plot(result,jplt); end
end
