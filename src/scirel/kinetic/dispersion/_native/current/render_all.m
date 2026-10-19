resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
cd(fullfile(workroot,'code','modules'));
run pdrk_plot_all;
figure_png=[];figure_native=[];
files=dir(fullfile(savepath,'*.png'));if ~isempty(files);fid=fopen(fullfile(savepath,files(end).name),'rb');figure_png=fread(fid,Inf,'*uint8');fclose(fid);end;
files=dir(fullfile(savepath,'*.fig'));if ~isempty(files);fid=fopen(fullfile(savepath,files(end).name),'rb');figure_native=fread(fid,Inf,'*uint8');fclose(fid);end;
