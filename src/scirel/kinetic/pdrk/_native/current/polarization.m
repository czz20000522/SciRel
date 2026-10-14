
resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
% D2 typed binary64 predecessor eigenvalues own the diagnostic carrier.
if exist('d','var');d0=d;end;
cd(fullfile(workroot,'code','modules'));
source(fullfile(resource,'restore_undefined_poles.m'));
if exist('rng_seed','var');rand('state',rng_seed);randn('state',rng_seed);end;
V=[];D=[];dEB=[];UE=[];UB=[];Pola=[];wws2=[];icalp=0;run pdrk_polarization;
d0_serialized='';if exist('d0','var');d0_serialized=mat2str(d0,17);end;
