"""Retained primitive selection preserves the bounded Boundary oracle."""
import numpy as np
from scirel.fieldline import Boundary, d_ds_arclength
import scirel.fieldline as fieldline


def test_boundary_source_interpolation_with_repaired_class_exports():
    p = Boundary(np.column_stack([np.linspace(0, 1, 6), np.linspace(0, 1, 6)]))
    np.testing.assert_allclose(p.interpolate([0, 1]), [[0, 1], [0, 1]], rtol=0, atol=4e-14)
    for symbol in ['FieldLine', 'HelperFieldLine', 'FieldLineSet', 'contour_points', 'helper_contour_points']:
        assert hasattr(fieldline, symbol)


def test_arclength_primitive_keeps_nonuniform_quadratic_contract():
    x = np.array([.2, .27, .5, .82, 1.4, 1.9])
    s = x - x[0]
    vertices = np.column_stack([x, np.zeros_like(x)])
    np.testing.assert_allclose(d_ds_arclength(vertices, 3*s*s - 2*s + .4), 6*s-2, rtol=0, atol=3e-13)
