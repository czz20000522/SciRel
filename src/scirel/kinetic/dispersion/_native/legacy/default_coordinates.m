% Exact source loop sampling: Octave materialized range differs from iterated range.
es1d_grid=[];es3d_grid=[];em_grid=[];
for kj=0.4:-0.02:0.01
 es1d_grid=[es1d_grid,kj];
end
for kj=0.05:0.1:5
 es3d_grid=[es3d_grid,kj];
end
for kj=0.01:0.02:1
 em_grid=[em_grid,kj];
end
