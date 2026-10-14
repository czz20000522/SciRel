% 21-08-31 17:34
function y=Gamman(n,x)
% D2: explicitly expand elementwise shapes; besseli itself does not broadcast.
    n=bsxfun(@plus,n,zeros(size(x)));
    x=bsxfun(@plus,x,zeros(size(n)));
%     y=besseli(n,x).*exp(-x);
    % y=besseli(n,x,1);
    y=besseli(n,x,1).* exp(-x + abs(real(x))); % 25-02-07 16:20
    % y=GamnLpole(n,x);
end
