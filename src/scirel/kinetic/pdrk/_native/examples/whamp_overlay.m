set(0,'defaultfigurevisible','off');
if ~isempty(predecessor_figure);
 fp=fopen('predecessor.fig','wb');fwrite(fp,uint8(predecessor_figure),'uint8');fclose(fp);
 h=openfig(fullfile(pwd(),'predecessor.fig'),'new','invisible');figure(h);
else;h=figure('visible','off');endif;
source(fullfile(fileparts(mfilename('fullpath')),'whamp_dat.m'));
source(fullfile(fileparts(mfilename('fullpath')),'capture_plot.m'));
