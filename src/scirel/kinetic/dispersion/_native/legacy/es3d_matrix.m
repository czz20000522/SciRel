% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_es3d.m@887498b2f9820d0d942504b6a061b19be52b318f
SNJ=S*(2*N+1)*J;
    k=sqrt(kz^2+kx^2);
    
    bs=kx*rhocs;
    bs2=bs.^2;
    snj=0;
    aSNJ=1;
    for s=1:S % species 
        aSNJ=aSNJ+(kDs(s)^2/k^2);
        for n=-N:N % Bessel function
%             Gamn=exp(-bs2(s))*besseli(n,bs2(s)); % large k_perp will NaN
            Gamn=besseli(n,bs2(s),1); % 2014-10-13 12:51

            for j=1:J  % poles of Z(zeta)
                snj=snj+1;
                tmp=n*wcs(s)+czj(j)*kz*vtzs(s);
                csnj(snj)=kz*vs0(s)+tmp;
                bsnj(snj)=(kDs(s)^2/k^2)*Gamn*bzj(j)*(tmp-...
                    (1-Tzs(s)/Tps(s))*n*wcs(s));
                aSNJ=aSNJ+(kDs(s)^2/k^2)*Gamn*(bzj(j));
            end
        end
    end

% D2: ordinary M omitted; consumer uses rational Harris descriptor with aSNJ.
