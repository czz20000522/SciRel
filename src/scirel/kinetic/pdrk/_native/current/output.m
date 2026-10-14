
resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
% D2 typed binary64 predecessor eigenvalues own the diagnostic carrier.
if exist('d','var');d0=d;end;
cd(fullfile(workroot,'code','modules'));
source(fullfile(resource,'restore_undefined_poles.m'));
if exist('rng_seed','var');rand('state',rng_seed);randn('state',rng_seed);end;
V=[];D=[];dEB=[];UE=[];UB=[];try;run pdrk_output;output_completed=true;output_error='';output_error_identifier='';catch native_source_error;output_completed=false;output_error=native_source_error.message;output_error_identifier=native_source_error.identifier;end;
figure_png=[];figure_native=[];
files=dir(fullfile(savepath,'*.png'));if ~isempty(files);fid=fopen(fullfile(savepath,files(end).name),'rb');figure_png=fread(fid,Inf,'*uint8');fclose(fid);end;
files=dir(fullfile(savepath,'*.fig'));if ~isempty(files);fid=fopen(fullfile(savepath,files(end).name),'rb');figure_native=fread(fid,Inf,'*uint8');fclose(fid);end;
workspace_mat=[];files=dir(fullfile(savepath,'out_pdrk*.mat'));if ~isempty(files);fid=fopen(fullfile(savepath,files(end).name),'rb');workspace_mat=fread(fid,Inf,'*uint8');fclose(fid);end;
d0_serialized='';if exist('d0','var');d0_serialized=mat2str(d0,17);end;
