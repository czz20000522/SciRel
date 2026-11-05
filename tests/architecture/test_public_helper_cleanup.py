"""Public helper names have one owner or no no-op implementation."""


def test_redundant_public_helper_names_are_removed():
    import scirel.electromagnetism as electromagnetism
    import scirel.geometry as geometry
    from scirel.geometry.fieldline import FieldLine, HelperFieldLine

    assert "get_gpsi" not in geometry.__all__
    assert not hasattr(geometry, "get_gpsi")
    assert "get_gpsi" in electromagnetism.__all__
    assert not hasattr(FieldLine, "reorder_verts")
    assert not hasattr(HelperFieldLine, "reorder_verts")
