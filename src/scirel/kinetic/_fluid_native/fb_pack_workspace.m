function state = fb_pack_workspace()
% Capture the source operator caller workspace as an explicit struct port.
vars=evalin('caller','whos'); state=struct();
for i=1:numel(vars)
  name=vars(i).name;
  if ~any(strcmp(name,{'ans','state','poles','prior','cleanup','xx_input'})), state.(name)=evalin('caller',name); end
end
end
