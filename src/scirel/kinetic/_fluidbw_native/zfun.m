% D2: erfcx fixes Inf*0 at large positive imaginary arguments.
% 21-08-31 17:32
% Plasma dispersion function Z(zeta)
function Zeta=zfun(z)
    %  rewrite from faddeeva.m
    %   w(z) = exp(-z^2) * erfc(-j*z)
    N=64;
    w = zeros(size(z)); % initialize output
%     Zeta = 0.*w;

    % for purely imaginary-valued inputs, use erf as is if z is real
    idx = real(z)==0; %
    w(idx) = erfcx(imag(z(idx)));

    if all(idx)
        Zeta=1i*sqrt(pi).*w; % 21-09-01 09:14
        return;
    end
    idx = ~idx;

    %%%%%
    % for complex-valued inputs

    % make sure all points are in the upper half-plane (Im>0)
    idx1 = idx & imag(z)<0;
    z(idx1) = conj(z(idx1));

    M = 2*N;
    M2 = 2*M;
    k = (-M+1:1:M-1)'; % M2 = no. of sampling points
    L = sqrt(N/sqrt(2)); % Optimal choice of L

    theta = k*pi/M;
    t = L*tan(theta/2); % Variables theta and t
    f = exp(-t.^2).*(L^2+t.^2);
    f = [0; f]; % Function to be transformed
    a = real(fft(fftshift(f)))/M2; % Coefficients of transform
    a = flipud(a(2:N+1)); % Reorder coefficients

    Z = (L+1i*z(idx))./(L-1i*z(idx));
    p = polyval(a,Z); % Polynomial evaluation.
    w(idx) = 2*p./(L-1i*z(idx)).^2 + (1/sqrt(pi))./(L-1i*z(idx)); % w(z)

    % convert upper half-plane to lower half-plane if necesary
    w(idx1) = conj(2*exp(-z(idx1).^2) - w(idx1));

    Zeta=1i*sqrt(pi).*w; % zfun=1i*sqrt(pi)*faddeeva(z);
end