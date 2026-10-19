function result=fb_materials(state,family,jplt)
set(0,'defaultfigurevisible','off');
if strcmp(family,'bonk'), result=fb_bonk_plot(state);
elseif strcmp(family,'em'), result=fb_em_plot(state,jplt);
else, error('fluidbw:family','unknown family'); end

end
