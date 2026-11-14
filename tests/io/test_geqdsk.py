"""Standard EFIT G-EQDSK reader against hand-written records.

The records follow L. L. Lao, "G EQDSK FORMAT" (1997): first record
``(6a8, 3i4)``; then ``5e16.9`` records for the four scalar lines, FPOL, PRES,
FFPRIM, PPRIME, PSIRZ (R index fastest), QPSI; ``2i5`` for NBBBS and LIMITR;
then the boundary and limiter (R, Z) pairs.  No library writer is used.
"""

import numpy as np
import pytest

from scirel.io import EQDSKFormatError, read_geqdsk

NW, NH = 3, 2
SCALARS = [
    [2.0, 3.0, 1.5, 0.25, -0.1],  # rdim zdim rcentr rleft zmid
    [1.2, -0.05, -0.75, 0.5, -2.5],  # rmaxis zmaxis simag sibry bcentr
    [-1.5e6, -0.75, 0.0, 1.2, 0.0],  # current simag dummy rmaxis dummy
    [-0.05, 0.0, 0.5, 0.0, 0.0],  # zmaxis dummy sibry dummy dummy
]
PROFILES = {
    "fpol": [-3.0, -3.1, -3.2],
    "pres": [1.0e5, 5.0e4, 0.0],
    "ffprim": [0.1, -0.2, 0.3],
    "pprime": [-4.0e4, -2.0e4, -1.0e4],
}
# psi(R_i, Z_j): distinct digits make a transposed or reversed grid visible.
PSI_RZ = np.array([[11.0, 21.0, 31.0], [12.0, 22.0, 32.0]])  # [j, i]
QPSI = [1.05, -2.0, 4.5]
BOUNDARY = [[1.0, -0.5], [1.4, 0.0], [1.0, 0.5]]
LIMITER = [[0.3, -1.4], [2.2, 1.4]]


def records(values):
    """Five 16-character Fortran E fields per line, as 5e16.9 writes them."""
    flat = np.ravel(values)
    return ["".join(f"{v:16.9E}" for v in flat[i : i + 5]) for i in range(0, flat.size, 5)]


def text(*, trailing=""):
    lines = ["EFIT    11/03/26    #000001  0000ms".ljust(48) + f"   0{NW:4d}{NH:4d}"]
    for row in SCALARS:
        lines += records(row)
    for name in ("fpol", "pres", "ffprim", "pprime"):
        lines += records(PROFILES[name])
    lines += records(PSI_RZ.ravel())  # C order of [j, i] is i fastest
    lines += records(QPSI)
    lines.append(f"{len(BOUNDARY):5d}{len(LIMITER):5d}")
    lines += records(BOUNDARY)
    lines += records(LIMITER)
    return "\n".join(lines) + "\n" + trailing


@pytest.fixture
def path(tmp_path):
    target = tmp_path / "g000001.00000"
    target.write_text(text())
    return target


def test_header_scalars_follow_the_specified_positions(path):
    g = read_geqdsk(path)
    assert (g["nw"], g["nh"]) == (NW, NH)
    assert g["description"].startswith("EFIT")
    expected = {
        "rdim": 2.0, "zdim": 3.0, "rcentr": 1.5, "rleft": 0.25, "zmid": -0.1,
        "rmaxis": 1.2, "zmaxis": -0.05, "simag": -0.75, "sibry": 0.5,
        "bcentr": -2.5, "current": -1.5e6,
    }  # fmt: skip
    assert {key: g[key] for key in expected} == expected


def test_profiles_grid_and_flux_map_keep_their_order(path):
    g = read_geqdsk(path)
    for name, values in PROFILES.items():
        np.testing.assert_array_equal(g[name], values)
    np.testing.assert_array_equal(g["qpsi"], QPSI)
    np.testing.assert_array_equal(g["psirz"], PSI_RZ)
    # R from RLEFT to RLEFT+RDIM; Z centred on ZMID with height ZDIM.
    np.testing.assert_allclose(g["r"], [0.25, 1.25, 2.25])
    np.testing.assert_allclose(g["z"], [-1.6, 1.4])
    np.testing.assert_allclose(g["psi"], [-0.75, -0.125, 0.5])
    assert g["psirz"][1, 2] == 32.0  # R index 2, Z index 1


def test_boundary_and_limiter_are_separate_pair_lists(path):
    g = read_geqdsk(path)
    assert (g["nbbbs"], g["limitr"]) == (3, 2)
    np.testing.assert_array_equal(np.column_stack([g["rbbbs"], g["zbbbs"]]), BOUNDARY)
    np.testing.assert_array_equal(np.column_stack([g["rlim"], g["zlim"]]), LIMITER)


def test_fields_that_run_together_and_free_format_read_the_same(tmp_path, path):
    fixed = read_geqdsk(path)
    assert "E+00-" in path.read_text()  # a minus sign fills the field gap
    # Fortran D exponents, all numbers on one line separated by single spaces.
    head, body = text().split("\n", 1)
    loose = tmp_path / "free"
    loose.write_text(head + "\n" + " ".join(body.replace("E", "D").split()) + "\n")
    free = read_geqdsk(loose)
    for key, value in fixed.items():
        np.testing.assert_array_equal(free[key], value)


def test_trailing_records_need_strict_false(tmp_path):
    target = tmp_path / "extra"
    target.write_text(text(trailing="    1\n 1.000000000E+00\n"))
    with pytest.raises(EQDSKFormatError, match="strict=False"):
        read_geqdsk(target)
    assert read_geqdsk(target, strict=False)["limitr"] == 2


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda t: t[: t.rindex("\n", 0, len(t) - 1)] + "\n", "truncated limiter"),
        (lambda t: t.replace("    3    2", "  3.5    2"), "NBBBS"),
        (
            lambda t: t.replace(
                " 5.000000000E-01-2.500000000E+00", "-7.500000000E-01-2.500000000E+00", 1
            ),
            "differ",
        ),
        (lambda t: t.split("\n", 1)[0][:48] + "\n" + t.split("\n", 1)[1], "NW and NH"),
        (
            lambda t: t.replace(
                " 2.000000000E+00 3.000000000E+00", " 0.000000000E+00 3.000000000E+00", 1
            ),
            "positive",
        ),
    ],
)
def test_malformed_files_are_rejected(tmp_path, edit, message):
    target = tmp_path / "bad"
    target.write_text(edit(text()))
    with pytest.raises(EQDSKFormatError, match=message):
        read_geqdsk(target)


def test_extended_dialect_reader_still_rejects_a_standard_file(path):
    from scirel.io import read_eqdsk

    with pytest.raises(EQDSKFormatError):
        read_eqdsk(path)


def contour_text(nbbbs, limitr):
    """Replace only the count record and its coordinate records."""
    prefix = text().split("    3    2\n", 1)[0]
    boundary = np.column_stack((np.arange(nbbbs) * 0.25, -np.arange(nbbbs) * 0.5))
    limiter = np.column_stack((np.arange(limitr) * 0.5, -np.arange(limitr) * 0.25))
    lines = [f"{nbbbs:5d}{limitr:5d}", *records(boundary), *records(limiter)]
    return prefix + "\n".join(lines) + "\n", boundary, limiter


@pytest.mark.parametrize(
    "nbbbs, limitr",
    [(10000, 10000), (10000, 2), (3, 10000), (0, 10000), (10000, 0), (0, 0), (0, 2), (3, 0)],
)
def test_count_record_uses_two_five_character_fields(tmp_path, nbbbs, limitr):
    content, boundary, limiter = contour_text(nbbbs, limitr)
    target = tmp_path / "counts"
    target.write_text(content)
    g = read_geqdsk(target)
    assert type(g["nbbbs"]) is int and type(g["limitr"]) is int
    assert (g["nbbbs"], g["limitr"]) == (nbbbs, limitr)
    for key, expected in (
        ("rbbbs", boundary[:, 0]), ("zbbbs", boundary[:, 1]),
        ("rlim", limiter[:, 0]), ("zlim", limiter[:, 1]),
    ):  # fmt: skip
        assert type(g[key]) is np.ndarray
        assert g[key].dtype == expected.dtype
        assert g[key].shape == expected.shape
        assert g[key].tobytes() == expected.tobytes()


def test_free_format_large_count_is_not_guessed_from_its_digits(tmp_path):
    head, body = text().replace("    3    2", "1000010000 0", 1).split("\n", 1)
    target = tmp_path / "free-large-count"
    target.write_text(head + "\n" + " ".join(body.split()) + "\n")
    with pytest.raises(EQDSKFormatError, match="truncated boundary: expected 2000020000 values"):
        read_geqdsk(target)


@pytest.mark.parametrize("exponent", ["E", "e", "D", "d"])
@pytest.mark.parametrize("free", [False, True])
def test_valid_exponents_and_signed_adjacency_preserve_every_value(tmp_path, path, exponent, free):
    expected = read_geqdsk(path)
    head, body = text().split("\n", 1)
    body = body.replace("E", exponent)
    if free:
        body = " \t".join(body.split()) + "\n"
    target = tmp_path / "exponents"
    target.write_text(head + "\n" + body)
    actual = read_geqdsk(target)
    assert type(actual) is type(expected) is dict
    assert list(actual) == list(expected)
    for key, value in expected.items():
        assert type(actual[key]) is type(value)
        if isinstance(value, np.ndarray):
            assert actual[key].dtype == value.dtype
            assert actual[key].shape == value.shape
            assert actual[key].tobytes() == value.tobytes()
        else:
            assert actual[key] == value


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda t: t.replace("\n", "\nBROKEN\n", 1), id="standalone-scalar-prefix"),
        pytest.param(lambda t: t.replace("E+00", "E+00BROKEN", 1), id="scalar-suffix"),
        pytest.param(lambda t: t.replace("E+00", "E", 1), id="incomplete-E"),
        pytest.param(lambda t: t.replace("E+00", "E+", 1), id="incomplete-E-plus"),
        pytest.param(lambda t: t.replace("E+00", "D-", 1), id="incomplete-D-minus"),
        pytest.param(lambda t: t.replace("E+00", "E++00", 1), id="double-exponent-sign"),
        pytest.param(
            lambda t: t.replace("-3.000000000E+00", "BROKEN -3.000000000E+00", 1), id="profile"
        ),
        pytest.param(
            lambda t: t.replace("1.100000000E+01", "1.100000000E+01 BROKEN", 1), id="psirz"
        ),
        pytest.param(
            lambda t: t.replace("1.050000000E+00", "1.050000000E+00 BROKEN", 1), id="qpsi"
        ),
        pytest.param(lambda t: t.replace("    3    2\n", "    3    2BROKEN\n", 1), id="counts"),
        pytest.param(
            lambda t: t.replace("-5.000000000E-01", "-5.000000000E-01 BROKEN", 1), id="boundary"
        ),
        pytest.param(lambda t: t.rstrip() + " BROKEN\n", id="last-limiter-record"),
        pytest.param(
            lambda t: t.replace("2.000000000E+00", "2.000000000E+00.5", 1), id="unsigned-adjacency"
        ),
    ],
)
def test_standard_records_reject_unconsumed_characters(tmp_path, strict, edit):
    target = tmp_path / "corrupt"
    target.write_text(edit(text()))
    with pytest.raises(EQDSKFormatError):
        read_geqdsk(target, strict=strict)


@pytest.mark.parametrize("counts", ["   -1    2", "    3   -1", "  3.5    2", "    3  2.5"])
def test_invalid_contour_counts_are_rejected(tmp_path, counts):
    target = tmp_path / "invalid-counts"
    target.write_text(text().replace("    3    2", counts, 1))
    with pytest.raises(EQDSKFormatError, match="NBBBS|LIMITR"):
        read_geqdsk(target)


@pytest.mark.parametrize("trailing", ["BROKEN\n", "1.000000000E+\n", "1 2 3\n"])
@pytest.mark.parametrize("empty", [False, True])
def test_only_appended_records_may_be_ignored(tmp_path, trailing, empty):
    content = contour_text(0, 0)[0] if empty else text()
    target = tmp_path / "appended"
    target.write_text(content)
    expected = read_geqdsk(target)
    target.write_text(content + trailing)
    with pytest.raises(EQDSKFormatError, match="strict=False"):
        read_geqdsk(target)
    actual = read_geqdsk(target, strict=False)
    assert list(actual) == list(expected)
    for key, value in expected.items():
        np.testing.assert_array_equal(actual[key], value)
