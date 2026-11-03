"""WHAM coil geometry with device-library constructor defaults."""

from scirel.electromagnetism import Device, RectangularCoil


class WHAM(Device):
    """Ordered current-set container with matrix-valued field responses.

    Raises
    ------
    FloatingPointError
        Child Green-kernel FloatingPointError propagates.
    TypeError
        Supplying constructor arguments raises TypeError. Child source
        ValueError and active-filament singularity failures propagate from
        construction or later field evaluation.
    ValueError
        Supplying constructor arguments raises TypeError. Child source
        ValueError and active-filament singularity failures propagate from
        construction or later field evaluation.

    See Also
    --------
    scirel.field.solve_multi_coil_vacuum_field : Build coils from a task's own geometry and currents.

    Examples
    --------
    >>> from scirel.configurations import WHAM
    >>> d=WHAM()
    >>> assert [c.npts for c in d.current_sets]==[32,32,10,10]
    """

    def __init__(self):
        super().__init__()
        self.hts1 = RectangularCoil(0.25, 0.942, nr=8, nz=4, dr=0.0475, dz=0.0275)
        self.hts2 = RectangularCoil(0.25, -0.942, nr=8, nz=4, dr=0.0475, dz=0.0275)
        self.cc1 = RectangularCoil(1.005, 0.205, nr=2, nz=5, dr=0.025, dz=0.024)
        self.cc2 = RectangularCoil(1.005, -0.205, nr=2, nz=5, dr=0.025, dz=0.024)


__all__ = ["WHAM"]
