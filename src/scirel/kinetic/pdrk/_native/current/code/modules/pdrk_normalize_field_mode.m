function [field, UE, UB] = pdrk_normalize_field_mode(field, epsilon0, mu0)
% SciRel D2 successor of frozen D0 887498b pdrk_kernel.m:97-102.
% The old divisor is not a Hermitian norm; Ex division excludes valid Ex=0.
% Normalize E only (E and B have different units), then scale/rotate B alike.
  if ~isnumeric(field) || numel(field) ~= 6 || any(~isfinite(field(:)))
    error('scirel:fieldDomain', 'Six finite complex electromagnetic components required');
  end
  if ~isscalar(epsilon0) || ~isscalar(mu0) || ~isreal(epsilon0) || ~isreal(mu0) || ...
      ~isfinite(epsilon0) || ~isfinite(mu0) || epsilon0 <= 0 || mu0 <= 0
    error('scirel:fieldDomain', 'Positive finite SI epsilon0 and mu0 required');
  end
  field = field(:);
  scale = max([abs(real(field(1:3))); abs(imag(field(1:3)))]);
  if scale == 0
    error('scirel:zeroElectricMode', 'Electric normalization is undefined for a zero electric mode');
  end
  field = field / scale;
  field = field / norm(field(1:3));
  % Rotation may exchange two equal magnitudes by one rounding unit.
  % Recheck the actual normalized representation before fixing its gauge.
  for phase_step=1:4
    [~, pivot] = max(abs(field(1:3))); % first component wins an exact tie
    field = field * (conj(field(pivot)) / abs(field(pivot)));
    field(pivot) = abs(field(pivot)); % exact real pivot, rounding only
    [~, represented_pivot] = max(abs(field(1:3)));
    if represented_pivot == pivot; break; end
  end
  if abs(imag(field(represented_pivot))) > 64*eps || real(field(represented_pivot)) < 0
    error('scirel:fieldRange', 'Phase pivot is unstable in the native representation');
  end
  UE = epsilon0 * sum(abs(field(1:3)).^2) / 2;
  UB = sum(abs(field(4:6)).^2) / (2 * mu0);
  if any(~isfinite(field)) || ~isfinite(UE) || ~isfinite(UB)
    error('scirel:fieldRange', 'Normalized fields or SI energies are not representable');
  end
end
