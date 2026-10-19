function [Z,Q]=fb_z_stable(z)
% Q=1+z Z(z), evaluated without subtracting nearly equal numbers for real z.
Z=zfun(z); Q=1+z.*Z;
large=abs(z)>12;
for k=find(large(:)).'
  zz=z(k); term=-1/(2*zz^2); q=term;
  for m=1:100
    next=term*(2*m+1)/(2*zz^2);
    if abs(next)>=abs(term), break; end
    q=q+next; term=next;
    if abs(term)<eps*abs(q), break; end
  end
  Q(k)=q+1i*sqrt(pi)*zz*exp(-zz^2);
end
end
