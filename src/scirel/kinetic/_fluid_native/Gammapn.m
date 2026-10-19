% 21-08-31 17:35
function y=Gammapn(n,x)
% D2: conform order and argument arrays before the unchanged neighbor identity.
    n=bsxfun(@plus,n,zeros(size(x)));
    x=bsxfun(@plus,x,zeros(size(n)));
%     y=((besseli(n-1,x)+besseli(n+1,x))*0.5-besseli(n,x)).*exp(-x);
    % y=((besseli(n-1,x,1)+besseli(n+1,x,1))/2-besseli(n,x,1));
    y=((besseli(n-1,x,1)+besseli(n+1,x,1))/2-besseli(n,x,1)).* exp(-x + abs(real(x))); % 25-02-07 16:20
    % y=(0.5*GamnLpole(n+1,x)+0.5*GamnLpole(n-1,x)-GamnLpole(n,x));
end
