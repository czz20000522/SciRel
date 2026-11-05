"""Small analysis helpers exposed by the geometry domain.

The domain keeps these names together because callers historically imported
field-line derivatives from this module. The implementations remain owned by
their focused modules; the Green-function helper has one public owner in
``scirel.electromagnetism``.
"""

from .fieldline import d_ds_arclength
from .numerics import NumericalContractError, diff_12_central

__all__ = ["NumericalContractError", "d_ds_arclength", "diff_12_central"]
