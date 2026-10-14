set(0,'defaultfigurevisible','off');
resource=fileparts(mfilename('fullpath'));copyfile(fullfile(resource,'code'),fullfile(pwd,'code'));
if ~strcmp(setup_name,'default');for name={'pdrk.in','pdrk_setup.m','pdrk_wpdat.m'};copyfile(fullfile(resource,'fixtures',setup_name,name{1}),fullfile(pwd,'code','input',name{1}));end;end;
cd(fullfile(pwd,'code'));
if exist('rng_seed','var');rand('state',rng_seed);randn('state',rng_seed);if ~isempty(getenv('SCIREL_NATIVE_EVIDENCE_DIR'));startup_rand_state=rand('state');startup_randn_state=randn('state');startup_evidence_root=getenv('SCIREL_NATIVE_EVIDENCE_DIR');if ~exist(startup_evidence_root,'dir');mkdir(startup_evidence_root);end;save('-mat7-binary',fullfile(startup_evidence_root,['startup-rng-',num2str(getpid),'.mat']),'rng_seed','startup_rand_state','startup_randn_state');end;end;
try;run('pdrk_main.m');program_error='';program_completed=true;catch err;program_error=err.message;program_completed=false;end;
program_output_directory='';if exist('savepath','var');program_output_directory=canonicalize_file_name(fullfile(pwd,'modules',savepath));end;
mat_bytes=[];all_png=[];select_png=[];pola_png=[];all_fig=[];select_fig=[];pola_fig=[];
for pair={'out_pdrk*.mat','mat_bytes';'*_all.png','all_png';'*_select.png','select_png';'*_pola.png','pola_png';'*_all.fig','all_fig';'*_select.fig','select_fig';'*_pola.fig','pola_fig'}';
files=dir(fullfile(program_output_directory,pair{1}));if ~isempty(files);fid=fopen(fullfile(program_output_directory,files(end).name),'rb');value=fread(fid,Inf,'*uint8');fclose(fid);eval([pair{2},'=value;']);end;end;

source_port_names={'ww','wws','wws2','Pola','par','wg','wg0','kk','kxx','kzz','tt','wwp','M','d','cwp','wcs1','vtzs','qs','ms','Tzs','Tps','wps2','rsab','lmdTab','rhocsab','kDs','bzj','czj','S','NN','npa','npb','nw','nw0','sp','sp0','icalp','iout','iem','ipa','ipb','pa','pb','wpdat','rex','rey','rez','figstr','k','kx','kz','theta','epsilon0','mu0','c2'};native_defined_ports=jsonencode(intersect(who,source_port_names));for port=source_port_names;if ~exist(port{1},'var');eval([port{1},'=[];']);end;end;
