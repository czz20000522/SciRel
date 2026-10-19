% 18-10-06 07:05 Hua-sheng XIE, huashengxie@gmail.com, FRI-ENN, China
% Ackn.: Richard Denton (Dartmouth), Xin Tao (USTC), Jin-song Zhao (PMO), 
% etc ...
% Use this file to output the results.

% iout=2;
% npl1=4;
npl1=npl;
if(iout==2)
  % calculate the polarizations for wws
  sp=1; nw=1;
  Pola=zeros(npa,npb,npl,20);
  wws2=wws;
  icalp=1; % tell kernel.m which can calculate polarization now
  for jpl=1:npl1
    % in eigs(), use wws(jpa,jpb,jpl) as intitial guess for each (pa,pb)
    run ../modules/pdrk_kernel; % to update
  end
end

