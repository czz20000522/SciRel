resource=fileparts(mfilename('fullpath'));
addpath(fullfile(resource,'code','modules'));
[normalized_fields,UE,UB]=pdrk_normalize_field_mode(fields,epsilon0,mu0);
