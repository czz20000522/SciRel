% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/cal_jpole_bjcj.m@887498b2f9820d0d942504b6a061b19be52b318f
xa=-5; xb=5; dx=(xb-xa)/100; 
ya=-3; yb=5; dy=(yb-ya)/100; 
[x,y]=ndgrid(xa:dx:xb,ya:dy:yb);
z=x+1i*y;
