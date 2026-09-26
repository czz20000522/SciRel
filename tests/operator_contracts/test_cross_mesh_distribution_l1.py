"""Bounded historical replay of the r62 cross-grid distribution interpolation
against the saved KN1DPy implementation, when present.

The saved operator bundle sits in the re-review archive ``KN1DPy-631d0bf1``:
KN1DPy's strict D1 qualification has been withdrawn, so this replay is
bounded historical development evidence about the arithmetic, not
qualified-L1 provenance and not expert approval.  Skipped unless
``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root; the saved
implementation file is pinned by SHA-256.

Scope: the saved formal operator has no cache or w_new branch (it recomputes
the weight matrix every call, exactly like the stateless SciRel port).  The
original KN1DPy runtime's weight cache lifecycle lives in the source runtime,
not in the saved formal operator, so no cache-state replay is possible here.
What this replay proves: the stateless port matches the saved formal operator
bit for bit on the declared domain and agrees on rejection behavior.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import interp_distribution_across_mesh

SOURCE_INTERP_SHA256 = "c93f491369b36e237c35c10528a82af9f33de2db730f9a3a8054dace6dca5a43"


def _source_operator():
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip(
            "SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active"
        )
    source = Path(root) / "operators" / "跨网格分布插值" / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == SOURCE_INTERP_SHA256, (
        f"saved operator bytes drifted from the compared arm: {source}"
    )
    spec = importlib.util.spec_from_file_location("kn1dpy_r62_interp", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cases():
    return [
        (
            np.linspace(0.5, 2.0, 4), np.linspace(-1.5, 1.5, 6),
            np.linspace(0.0, 1.0, 5),
            np.linspace(0.4, 1.8, 5), np.linspace(-1.2, 1.2, 7),
            np.linspace(0.1, 0.9, 4),
            2.0, 1.5,
        ),
        (
            np.linspace(0.5, 2.0, 6), np.linspace(-2.0, 2.0, 8),
            np.linspace(0.0, 2.0, 8),
            np.linspace(0.3, 1.5, 4), np.linspace(-1.0, 1.0, 5),
            np.linspace(0.2, 1.8, 6),
            1.0, 2.0,
        ),
    ]


def _dist(vr, vx, nx):
    vr2 = vr[:, None] ** 2 + vx[None, :] ** 2
    return np.exp(-vr2)[:, :, None] * np.ones((vr.size, vx.size, nx))


def test_the_saved_distribution_interpolation_is_reproduced_bit_for_bit():
    source = _source_operator()
    for vr_a, vx_a, x_a, vr_b, vx_b, x_b, tn_a, tn_b in _cases():
        fa = _dist(vr_a, vx_a, x_a.size)
        for correct in (0, 1):
            saved = source.interp_distribution_across_mesh(
                fa, vr_a, vx_a, x_a, tn_a, vr_b, vx_b, x_b, tn_b, correct
            )
            graph = interp_distribution_across_mesh(
                fa, vr_a, vx_a, x_a, tn_a, vr_b, vx_b, x_b, tn_b, correct
            )
            np.testing.assert_array_equal(graph, saved)


def test_the_saved_operator_determinism_matches_the_stateless_port():
    """The saved formal operator has no cache branch, so repeated calls
    re-execute the same code path.  This test asserts the port matches the
    saved operator on repeated calls, confirming determinism of both arms
    (the original source's w_new cache lifecycle is out of scope for this
    replay -- see module docstring)."""
    source = _source_operator()
    vr_a, vx_a, x_a, vr_b, vx_b, x_b = _cases()[0][:6]
    tn_a, tn_b = _cases()[0][6], _cases()[0][7]
    fa = _dist(vr_a, vx_a, x_a.size)
    saved_1 = source.interp_distribution_across_mesh(
        fa, vr_a, vx_a, x_a, tn_a, vr_b, vx_b, x_b, tn_b, correct=1
    )
    saved_2 = source.interp_distribution_across_mesh(
        fa, vr_a, vx_a, x_a, tn_a, vr_b, vx_b, x_b, tn_b, correct=1
    )
    np.testing.assert_array_equal(saved_1, saved_2)
    port = interp_distribution_across_mesh(
        fa, vr_a, vx_a, x_a, tn_a, vr_b, vx_b, x_b, tn_b, correct=1
    )
    np.testing.assert_array_equal(port, saved_1)


def test_the_saved_rejection_behavior_agrees_exactly():
    source = _source_operator()
    vr_a = np.linspace(0.5, 2.0, 4)
    vx_a = np.linspace(-1.5, 1.5, 6)
    x_a = np.linspace(0.0, 1.0, 5)
    vr_b = np.linspace(0.4, 1.8, 5)
    vx_b = np.linspace(-1.2, 1.2, 7)
    x_b = np.linspace(0.1, 0.9, 4)
    fa = _dist(vr_a, vx_a, x_a.size)
    with pytest.raises(ValueError):
        source.interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 0.0, vr_b, vx_b, x_b, 1.5
        )
    with pytest.raises(ValueError):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 0.0, vr_b, vx_b, x_b, 1.5
        )
    with pytest.raises(ValueError):
        source.interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, np.array([5.0, 6.0]), 1.5
        )
    with pytest.raises(ValueError):
        interp_distribution_across_mesh(
            fa, vr_a, vx_a, x_a, 2.0, vr_b, vx_b, np.array([5.0, 6.0]), 1.5
        )
