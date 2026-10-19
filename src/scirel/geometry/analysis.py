"""Small analysis helpers exposed by the geometry domain.

The domain keeps these names together because callers historically imported
field-line derivatives and the Green-function helper from this module.  The
implementations remain owned by their focused modules.
"""

from ..electromagnetism.greens import get_gpsi
from .fieldline import d_ds_arclength
from .numerics import NumericalContractError, diff_12_central

__all__ = ["get_gpsi", "NumericalContractError", "d_ds_arclength", "diff_12_central"]
