function result=fb_bonk(jcase,xx,plot_outputs)
% Ordered native TaskGraph parameters -> independent root sweep -> optional source IO.
if nargin<1, jcase=1; end
if nargin<3, plot_outputs=false; end
state=fb_bonk_parameters(jcase);
if nargin<2, result=fb_bonk_sweep(state); else, result=fb_bonk_sweep(state,xx); end
if plot_outputs, fb_bonk_plot(result); end
end
