import json
from pathlib import Path

import numpy as np

from scirel.kinetic.atomic_slab_transport import solve_atomic_slab_transport


def test_atomic_slab_composition_runs_fixed_public_case():
    path = Path(
        r"E:\SciRel-lab\_shared\outbound\portfolio-20261027\challenge-agent-20261029\cases\06-录屏-有限速度格原子氘束输运\题面\inputs.json"
    )
    if not path.exists():
        return
    result = solve_atomic_slab_transport(json.loads(path.read_text(encoding="utf-8")))
    assert result["distribution"].ndim == 3
    assert result["generation_count"] > 1
    assert result["generation_count"] <= 50
    assert result["generation_stop_reason"] in {"truncate", "max_generations"}
    assert result["density_m3"].shape == (50,)
    assert np.isfinite(result["density_m3"]).all()
