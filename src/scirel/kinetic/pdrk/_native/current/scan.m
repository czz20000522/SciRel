
resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
cd(fullfile(workroot,'code','modules'));
source(fullfile(resource,'restore_undefined_poles.m'));
if exist('rng_seed','var');rand('state',rng_seed);randn('state',rng_seed);end;
icalp=0;Pola=[];wws2=[];run pdrk_kernel;
d0_serialized='';if exist('d0','var');d0_serialized=mat2str(d0,17);end;
