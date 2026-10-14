% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_es1d.m@887498b2f9820d0d942504b6a061b19be52b318f
if(J==8)
    % opt supplied by typed wrapper; source default 1 for J8
    if(opt==1)
        % Ronnmark1982, 8-pole for Z function, and Z'
        bzj(1)=-1.734012457471826E-2-4.630639291680322E-2i;
        bzj(2)=-7.399169923225014E-1+8.395179978099844E-1i;
        bzj(3)=5.840628642184073+9.536009057643667E-1i;
        bzj(4)=-5.583371525286853-1.120854319126599E1i;
        czj(1)=2.237687789201900-1.625940856173727i;
        czj(2)=1.465234126106004-1.789620129162444i;
        czj(3)=.8392539817232638-1.891995045765206i;
        czj(4)=.2739362226285564-1.941786875844713i;
    else % new calculation
        bzj(1)=  -0.0173401116032742 - 0.0463064419344598i;
        bzj(2)=  -0.739917851897683 + 0.839518298070637i;
        bzj(3)=  5.84063227513760 + 0.953602843950785i;
        bzj(4)=  -5.58337431170864 - 11.2085508179677i;
        czj(1)=   2.23768772215616 - 1.62594103256666i;
        czj(2)=   1.46523409042510 - 1.78962030806222i;
        czj(3)=   0.839253965702731 - 1.89199521968963i;
        czj(4)=   0.273936217871668 - 1.94178704551807i;
    end

    bzj(5:8)=conj(bzj(1:4));
    czj(5:8)=-conj(czj(1:4));
elseif(J==12) % D2 source-prescribed J12/I16, regenerated80/120 proof ddd41214
    table=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'jpole12-regenerated.json')));
    bzj=(table.bzj(:,1)+1i*table.bzj(:,2)).';
    czj=(table.czj(:,1)+1i*table.czj(:,2)).';

elseif(J==4)
    % opt supplied by typed wrapper; source default 2 for J4
    if(opt==1)
        % Martin1980, 4-pole
        bzj(1)=0.5468-0.0372i;
        bzj(2)=-1.0468+2.1018i;
        czj(1)=-1.2359-1.2150i;
        czj(2)=-0.3786-1.3509i;
    else % new calculation
        bzj(1)=0.546796859834032 + 0.037196505239277i;
        bzj(2)=-1.046796859834027 + 2.101852568038518i;
        czj(1)=1.23588765343592 - 1.21498213255731i;
        czj(2)=-0.378611612386277 - 1.350943585432730i;
    end
    
    bzj(3:4)=conj(bzj(1:2));
    czj(3:4)=-conj(czj(1:2));
elseif(J==3)
    % Martin1980, 3-pole
    bzj(1)=0.1822+0.5756i;
    bzj(2)=-1.3643;
    czj(1)=-0.9217-0.9091i;
    czj(2)=-1.0204i;
    
    bzj(3)=conj(bzj(1));
    czj(3)=-conj(czj(1));
    
elseif(J==2)
    % Huba2009, 2-pole
    bzj(1)=-(0.5+0.81i);
    czj(1)=0.51-0.81i;
    bzj(2)=conj(bzj(1));
    czj(2)=-conj(czj(1));   
    
else
    % Martin1979, 2-pole
    bzj(1)=-(0.5+1.2891i);
    czj(1)=0.5138-1.0324i;
    bzj(2)=conj(bzj(1));
    czj(2)=-conj(czj(1));
end
J=length(bzj)
sum(bzj)
sum(bzj.*czj)
sum(bzj.*czj.^2)
