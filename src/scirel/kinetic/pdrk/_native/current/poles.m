resource=fileparts(mfilename('fullpath'));copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));cd(fullfile(pwd,'code','modules'));
run pdrk_poles;
