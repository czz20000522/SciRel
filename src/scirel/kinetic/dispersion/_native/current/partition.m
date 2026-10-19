rsab=zeros(2,numel(alphas));for s=1:numel(alphas);
if(alphas(s)==1);rsab(1,s)=1;rsab(2,s)=0;else;rsab(1,s)=(1-alphas(s)*Deltas(s))/(1-alphas(s));rsab(2,s)=alphas(s)*(Deltas(s)-1)/(1-alphas(s));end;end;
