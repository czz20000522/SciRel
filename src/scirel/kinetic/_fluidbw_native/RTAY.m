function RC=RTAY(Y,AL)
% D2 absorption of frozen RTAY. Same complete response contract; corrected
% harmonic evaluator replaces the source approximation and its selector gaps.
% No claim that the historical RTAY numerical branch was executed.
RC=fb_r_harmonic(Y,AL);
end
