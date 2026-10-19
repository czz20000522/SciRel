
resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
cd(fullfile(workroot,'code','modules'));
Pola=[];wws2=[];run pdrk_eigensolve;
d0_serialized='';if exist('d0','var');d0_serialized=mat2str(d0,17);end;
