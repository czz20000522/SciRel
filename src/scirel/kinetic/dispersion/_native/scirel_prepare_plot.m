function scirel_prepare_plot(h)
% Fixed pixel canvas avoids headless normalized-screen size and font clipping.
% Numeric data, axes, curve ordering and the native figure format stay intact.
  set(h,'units','pixels','position',[50,50,1200,800]);
  set(h,'paperunits','inches','papersize',[12,8],'paperposition',[0,0,12,8]);
  set(h,'paperorientation','landscape','paperpositionmode','manual');
  for ax=findall(h,'type','axes')'
    set(ax,'fontsize',7);
    set(get(ax,'xlabel'),'fontsize',8);set(get(ax,'ylabel'),'fontsize',8);
    set(get(ax,'zlabel'),'fontsize',8);set(get(ax,'title'),'fontsize',6);
  end
end
