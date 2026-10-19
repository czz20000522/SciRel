resource=fileparts(mfilename('fullpath'));
copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
workroot=pwd; savepath=[fullfile(workroot,'output'),filesep];mkdir(savepath);
if strcmp(setup_name,'default');setup=fullfile(workroot,'code','input','pdrk_setup.m');else;setup=fullfile(resource,'fixtures',setup_name,'pdrk_setup.m');end;
source(setup);
control_names={'iem','N','J','sp','wg0','B0','ipa','ipb','iloga','ilogb','pa1','pa2','dpa','pb1','pb2','dpb','iout'};
for ic=1:numel(control_names);v=control_values(ic);if ~isnan(v);if imag(v)==0;v=real(v);end;eval([control_names{ic},'=v;']);end;end;
if ~isempty(par_override);par=par_override;end;
savepath=[fullfile(workroot,'output'),filesep];
if isempty(deck);if strcmp(setup_name,'default');deckpath=fullfile(workroot,'code','input','pdrk.in');else;copyfile(fullfile(resource,'fixtures',setup_name,'pdrk.in'),fullfile(workroot,'code','input','pdrk.in'));end;else;fid=fopen(fullfile(workroot,'code','input','pdrk.in'),'w');fprintf(fid,'q m n Tpara Tperp alpha Delta vd\n');fclose(fid);dlmwrite(fullfile(workroot,'code','input','pdrk.in'),deck,'-append','delimiter',' ','precision',17);end;
SNJ3=[];wg=[];ipbtmp=[];
cd(fullfile(workroot,'code','modules'));run pdrk_initialize;

undefined_pole_fields={};if ~exist('bzj','var');undefined_pole_fields{end+1}='bzj';bzj=[];end;if ~exist('czj','var');undefined_pole_fields{end+1}='czj';czj=[];end;undefined_pole_fields=jsonencode(undefined_pole_fields);
