resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
cd(fullfile(workroot,'code','modules'));
wwn=ww/wcs1;pas=[];run pdrk_select_compute;
