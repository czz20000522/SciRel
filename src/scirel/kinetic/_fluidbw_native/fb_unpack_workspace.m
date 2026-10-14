function fb_unpack_workspace(state,names)
% Explicit named transfer where controls coexist with caller scientific state.
if nargin<2, names=fieldnames(state); end
for i=1:numel(names)
 if isfield(state,names{i}), assignin('caller',names{i},state.(names{i})); end
end
end
