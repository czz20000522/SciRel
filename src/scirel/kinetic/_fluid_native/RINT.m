function RC=RINT(Y,AL)
% D2 absorption of frozen RINT. Same complete response contract; corrected
% harmonic evaluator replaces the source approximation and its selector gaps.
% No claim that the historical RINT numerical branch was executed.
RC=fb_r_harmonic(Y,AL);
end
