function y=fb_bonk_scaled(q,kn,reference)
% Real two-dimensional, dimensionless independent root search. Reference is
% fixed per attempt, so changing residual scale cannot create false roots.
f=fDR((q(1)+1i*q(2))*kn)/reference;
y=[real(f);imag(f)];
end
