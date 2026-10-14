% D1 source_fidelity: old_version/pdrk_old_version_with_bugs_fixed/pdrk_em3d.m@887498b2f9820d0d942504b6a061b19be52b318f
if(J==8)
  % Ronnmark1982, 8-pole for Z function, and Z'
  bzj(1)=-1.734012457471826E-2-4.630639291680322E-2i;
  bzj(2)=-7.399169923225014E-1+8.395179978099844E-1i;
  bzj(3)=5.840628642184073+9.536009057643667E-1i;
  bzj(4)=-5.583371525286853-1.120854319126599E1i;
  czj(1)=2.237687789201900-1.625940856173727i;
  czj(2)=1.465234126106004-1.789620129162444i;
  czj(3)=.8392539817232638-1.891995045765206i;
  czj(4)=.2739362226285564-1.941786875844713i;
  
  bzj(5:8)=conj(bzj(1:4));
  czj(5:8)=-conj(czj(1:4));
elseif(J==12) % D2 source-prescribed J12/I16, regenerated80/120 proof ddd41214
    table=jsondecode(fileread(fullfile(fileparts(mfilename('fullpath')),'jpole12-regenerated.json')));
    bzj=(table.bzj(:,1)+1i*table.bzj(:,2)).';
    czj=(table.czj(:,1)+1i*table.czj(:,2)).';

elseif(J==4) % Martin1980
  bzj(1)=0.546796859834032 + 0.037196505239277i;
  bzj(2)=-1.046796859834027 + 2.101852568038518i;
  czj(1)=1.23588765343592 - 1.21498213255731i;
  czj(2)=-0.378611612386277 - 1.350943585432730i;
  bzj(3:4)=conj(bzj(1:2));
  czj(3:4)=-conj(czj(1:2));
end
% J=length(bzj);
% sum(bzj) % should be -1
% sum(bzj.*czj) % should be 0
% sum(bzj.*czj.^2) % should be -1/2
