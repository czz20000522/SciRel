resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
cd(fullfile(workroot,'code','modules'));
source(fullfile(resource,'restore_undefined_poles.m'));
run pdrk_em3d_matrix;
