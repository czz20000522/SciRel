"""The seven collision-fit leaves require numeric real energy inputs."""

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
    evaluate_atomic_hydrogen_elastic_cross_section,
    evaluate_hydrogen_h2_elastic_cross_section,
    evaluate_hydrogen_proton_elastic_cross_section,
    evaluate_hydrogen2_hydrogen2_elastic_cross_section,
    evaluate_hydrogen2_proton_elastic_cross_section,
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
)


@pytest.mark.parametrize("evaluate", [
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
    evaluate_atomic_hydrogen_elastic_cross_section,
    evaluate_hydrogen_h2_elastic_cross_section,
    evaluate_hydrogen_proton_elastic_cross_section,
    evaluate_hydrogen2_proton_elastic_cross_section,
    evaluate_hydrogen2_hydrogen2_elastic_cross_section,
])
@pytest.mark.parametrize("energy", [
    [1.0, "2.0"],
    [True, 1.0],
    np.array([1.0 + 2.0j]),
])
def test_nonreal_energy_is_rejected(evaluate, energy):
    with pytest.raises(ValueError, match="energy_ev"):
        evaluate(energy)
