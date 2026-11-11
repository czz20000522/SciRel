"""scirel.ApplicabilityWarning marks results returned outside a declared range (issue #156)."""

import warnings

import pytest

import scirel


def test_exported_from_the_root_namespace_as_a_user_warning():
    # Exported as an attribute, not in ``__all__``: the root list stays domain-only so that
    # ``from scirel import *`` keeps yielding modules, which the architecture tests pin.
    assert "ApplicabilityWarning" not in scirel.__all__
    assert "ApplicabilityWarning" in dir(scirel)
    # Defined in the root module: importing it must load no submodule, and the class has to
    # survive the vendored copy that carries only __init__.py (both pinned by the lazy-namespace
    # tests). "scirel" itself is the module name here.
    assert scirel.ApplicabilityWarning.__module__ == "scirel"
    assert issubclass(scirel.ApplicabilityWarning, UserWarning)
    # A UserWarning, not a RuntimeWarning: the result is defined, just outside the declared range.
    assert not issubclass(scirel.ApplicabilityWarning, RuntimeWarning)


def test_explicit_import_from_the_root_namespace_succeeds():
    from scirel import ApplicabilityWarning

    assert ApplicabilityWarning is scirel.ApplicabilityWarning


def test_simplefilter_error_turns_the_warning_into_an_exception():
    """The acceptance shape: an out-of-range call fails when callers require validated input."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", scirel.ApplicabilityWarning)
        with pytest.raises(scirel.ApplicabilityWarning):
            warnings.warn(
                "a relation returned a value outside its declared range",
                scirel.ApplicabilityWarning,
                stacklevel=2,
            )


def test_other_warning_classes_are_not_caught_by_that_filter():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.simplefilter("error", scirel.ApplicabilityWarning)
        warnings.warn("an unrelated runtime warning", RuntimeWarning, stacklevel=2)
    assert len(caught) == 1 and issubclass(caught[0].category, RuntimeWarning)
