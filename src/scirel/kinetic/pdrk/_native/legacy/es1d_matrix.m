% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_es1d.m@887498b2f9820d0d942504b6a061b19be52b318f
    SJ=S*J;

    sj=0;
    M=zeros(SJ,SJ);
    for s=1:S
        for j=1:J;
            sj=sj+1;
            csj(sj)=k*(czj(j)*vts(s)+vs0(s));
            bsj(sj)=vts(s)*bzj(j)*czj(j)*(kDs(s)^2/k);
        end
    end

    for sj=1:SJ
        M(sj,:)=-bsj(sj);
        M(sj,sj)=-bsj(sj)+csj(sj);
    end
