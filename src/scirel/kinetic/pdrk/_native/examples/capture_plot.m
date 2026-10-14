% D1 artifact/payload observation only, after original plot commands finish.
h=gcf;
savefig(h,'terminal.fig');
fp=fopen('terminal.fig','rb');figure_native=fread(fp,Inf,'*uint8');fclose(fp);
scirel_prepare_plot(h);
print(h,'-dpng','-S1200,800','terminal.png');
fp=fopen('terminal.png','rb');figure_png=fread(fp,Inf,'*uint8');fclose(fp);
line_x=[];line_y=[];line_offsets=1;line_axes=[];line_width=[];line_markers=char([]);axes_limits=[];
plot_axes=findall(h,'type','axes');axes_positions=[];kept_axes=[];
for ia=1:length(plot_axes)
 if ~strcmp(get(plot_axes(ia),'tag'),'legend')
  kept_axes=[kept_axes;plot_axes(ia)];axes_positions=[axes_positions;get(plot_axes(ia),'position')];
 endif;
end;
[unused,order]=sortrows(axes_positions,[1,2]);kept_axes=kept_axes(order);
for ia=1:length(kept_axes)
 ax=kept_axes(ia);axes_limits=[axes_limits;get(ax,'xlim'),get(ax,'ylim')];
 lines_here=findall(ax,'type','line');
 for il=1:length(lines_here)
  lx=get(lines_here(il),'xdata');ly=get(lines_here(il),'ydata');
  line_x=[line_x,lx(:).'];line_y=[line_y,ly(:).'];line_offsets=[line_offsets,length(line_x)+1];
  line_axes=[line_axes,ia];line_width=[line_width,get(lines_here(il),'linewidth')];
  line_markers=char(line_markers,get(lines_here(il),'marker'));
 end;
end;
legend_labels=char([]);legend_handles=findall(h,'tag','legend');
for il=1:length(legend_handles)
 labels=get(legend_handles(il),'string');
 if iscell(labels);legend_labels=char(legend_labels,char(labels));else;legend_labels=char(legend_labels,labels);endif;
end;
