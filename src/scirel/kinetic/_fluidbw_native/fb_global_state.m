function state = fb_global_state(action, incoming)
% Explicit state carrier for fD/fDR native globals. No numerical conversion.
% get: snapshot exactly; set: assign all fields (missing fields become []).
% The original direct functions remain callable for persistent global use.
  global S c2 wcs wps2 rhocs w kz vts;
  names = {'S','c2','wcs','wps2','rhocs','w','kz','vts'};
  if strcmp(action,'set')
    for i=1:numel(names)
      if isfield(incoming,names{i})
        eval([names{i},' = incoming.(names{i});']);
      else
        eval([names{i},' = [];']);
      end
    end
  elseif ~strcmp(action,'get')
    error('fluidbw:stateAction','action must be get or set');
  end
  state = struct('S',S,'c2',c2,'wcs',wcs,'wps2',wps2,'rhocs',rhocs,'w',w,'kz',kz,'vts',vts);
end
