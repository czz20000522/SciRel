"""Bounded D2 structural oracles for the equilibrium extended dialect."""

import importlib

import numpy as np
import pytest

io = importlib.import_module("scirel.io.eqdsk")


def sample():
    return dict(
        title="the equilibrium convention bounded fixture",
        cursign=-1,
        nnr=3,
        nnz=2,
        nnv=4,
        rbox=2.0,
        zbox=3.0,
        psi_lim=-0.2,
        Ip=-4.0,
        tor_flux=np.arange(4.0),
        p_flux=-np.arange(4.0),
        rbphi_flux=np.linspace(-2, 1, 4),
        pprime_flux=np.ones(4),
        q_flux=np.zeros(4),
        psi=np.arange(6.0).reshape(2, 3),
        nlim_pairs=2,
        nves_pairs=1,
        lim_pairs=np.array([[0.1, -0.2], [0.3, 0.4]]),
        ves_pairs=np.array([[0.5, -0.6]]),
        header_scalars=np.arange(20.0).reshape(4, 5),
    )


def test_roundtrip_and_preserved_scalars(tmp_path):
    d = sample()
    p = tmp_path / "fixture.eqdsk"
    io.write_eqdsk(d, p)
    got = io.read_eqdsk(p)
    for key in (
        "tor_flux",
        "p_flux",
        "rbphi_flux",
        "pprime_flux",
        "q_flux",
        "psi",
        "lim_pairs",
        "ves_pairs",
    ):
        np.testing.assert_allclose(got[key], d[key], rtol=1e-9, atol=1e-10)
    header = d["header_scalars"].copy()
    header[0, :2] = [d["rbox"], d["zbox"]]
    header[1, 3], header[2, 0] = d["psi_lim"], d["Ip"]
    np.testing.assert_array_equal(got["header_scalars"], header)
    np.testing.assert_array_equal(got["R"][0], [0, 1, 2])
    np.testing.assert_array_equal(got["Z"][:, 0], [-1.5, 1.5])


@pytest.mark.parametrize("key", ["nnr", "nnz", "nnv", "cursign", "nlim_pairs", "nves_pairs"])
@pytest.mark.parametrize("bad", [1.5, True, np.inf, "2"])
def test_integer_contract_does_not_coerce(tmp_path, key, bad):
    d = sample()
    d[key] = bad
    p = tmp_path / "existing.eqdsk"
    p.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError):
        io.write_eqdsk(d, p)
    assert p.read_text() == "keep original"


@pytest.mark.parametrize(
    "key,bad", [("nnr", 10000), ("cursign", -1000), ("nlim_pairs", 100000), ("title", "bad\ntitle")]
)
def test_header_width_and_record_injection(tmp_path, key, bad):
    d = sample()
    d[key] = bad
    with pytest.raises(io.EQDSKFormatError):
        io.write_eqdsk(d, tmp_path / "bad.eqdsk")


@pytest.mark.parametrize(
    "key,value,width",
    [
        ("nnr", 10000, 4),
        ("nnz", 10000, 4),
        ("nnv", 10000, 4),
        ("cursign", 10000, 4),
        ("cursign", -1000, 4),
        ("nlim_pairs", 100000, 5),
        ("nves_pairs", 100000, 5),
    ],
)
def test_integer_field_width_rejected_before_write(tmp_path, key, value, width):
    d = sample()
    d[key] = value
    destination = tmp_path / "existing.eqdsk"
    destination.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError, match="not representable"):
        io.write_eqdsk(d, destination)
    assert destination.read_text() == "keep original"
    with pytest.raises(io.EQDSKFormatError, match="not representable"):
        io._fixed_integer(value, key, width)


@pytest.mark.parametrize(
    "key,value,width",
    [
        ("nnr", 9999, 4),
        ("nnz", 9999, 4),
        ("nnv", 9999, 4),
        ("cursign", 9999, 4),
        ("cursign", -999, 4),
        ("nlim_pairs", 99999, 5),
        ("nves_pairs", 99999, 5),
    ],
)
def test_integer_field_width_boundary_is_accepted(key, value, width):
    assert io._fixed_integer(value, key, width) == value


@pytest.mark.parametrize("value", [1e100, 1e-100])
def test_positive_three_digit_exponent_uses_sixteen_character_fields(tmp_path, value):
    d = sample()
    d["rbox"] = value
    d["header_scalars"] = d["header_scalars"].copy()
    d["header_scalars"][0, 0] = value
    destination = tmp_path / "extreme.eqdsk"
    io.write_eqdsk(d, destination)
    lines = destination.read_text().splitlines()
    assert len(lines[1]) == 80
    assert lines[1][:16] == f"{value:16.9E}"
    got = io.read_eqdsk(destination)
    assert got["rbox"] == value


def test_strict_false_only_permits_trailing_records(tmp_path):
    destination = tmp_path / "fixture.eqdsk"
    io.write_eqdsk(sample(), destination)
    destination.write_text(destination.read_text() + "trailing compatibility record\n")
    io.read_eqdsk(destination, strict=False)
    with pytest.raises(io.EQDSKFormatError):
        io.read_eqdsk(destination, strict=True)


@pytest.mark.parametrize("key", ["tor_flux", "psi", "lim_pairs", "header_scalars"])
def test_complex_values_rejected_before_write(tmp_path, key):
    d = sample()
    value = np.asarray(d[key])
    d[key] = value.astype(complex) + 1j
    destination = tmp_path / "existing.eqdsk"
    destination.write_text("keep original")
    with pytest.raises((io.EQDSKFormatError, TypeError, ValueError)):
        io.write_eqdsk(d, destination)
    assert destination.read_text() == "keep original"


def test_zero_boundary_roundtrip(tmp_path):
    d = sample()
    d.update(nlim_pairs=0, nves_pairs=0, lim_pairs=np.empty((0, 2)), ves_pairs=np.empty((0, 2)))
    p = tmp_path / "zero.eqdsk"
    io.write_eqdsk(d, p)
    got = io.read_eqdsk(p)
    assert got["lim_pairs"].shape == got["ves_pairs"].shape == (0, 2)


@pytest.mark.parametrize("r0,z0", [(1.0, 0.0), (0.37, -0.22), (0.0, 0.43)])
def test_unrepresentable_grid_origin_is_rejected_before_write(tmp_path, r0, z0):
    d = sample()
    d["R"], d["Z"] = np.meshgrid(
        np.linspace(r0, r0 + d["rbox"], d["nnr"]),
        np.linspace(z0 - d["zbox"] / 2, z0 + d["zbox"] / 2, d["nnz"]),
    )
    destination = tmp_path / "existing.eqdsk"
    destination.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError, match="R/Z grid is not representable"):
        io.write_eqdsk(d, destination)
    assert destination.read_text() == "keep original"


def test_reconstructed_grid_is_accepted_and_reserved_scalars_survive(tmp_path):
    d = sample()
    d["header_scalars"] = d["header_scalars"].copy()
    d["header_scalars"][0, 2] = 17.25
    d["header_scalars"][3, 4] = -91.5
    d["R"], d["Z"] = np.meshgrid(
        np.linspace(0.0, d["rbox"], d["nnr"]), np.linspace(-d["zbox"] / 2, d["zbox"] / 2, d["nnz"])
    )
    destination = tmp_path / "representable.eqdsk"
    io.write_eqdsk(d, destination)
    got = io.read_eqdsk(destination)
    assert got["header_scalars"][0, 2] == 17.25
    assert got["header_scalars"][3, 4] == -91.5
    np.testing.assert_array_equal(got["R"], d["R"])
    np.testing.assert_array_equal(got["Z"], d["Z"])


@pytest.mark.parametrize("key,value", [("r_origin", 1.0), ("z_origin", 0.25)])
def test_explicit_unrepresentable_origin_metadata_is_rejected(tmp_path, key, value):
    d = sample()
    d[key] = value
    destination = tmp_path / "existing.eqdsk"
    destination.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError, match="not representable"):
        io.write_eqdsk(d, destination)
    assert destination.read_text() == "keep original"


@pytest.mark.parametrize("key", ["psi", "tor_flux", "lim_pairs", "header_scalars", "rbox"])
def test_nonfinite_rejected_before_write(tmp_path, key):
    d = sample()
    d[key] = np.full_like(d[key], np.nan, dtype=float)
    p = tmp_path / "existing.eqdsk"
    p.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError):
        io.write_eqdsk(d, p)
    assert p.read_text() == "keep original"


def test_unrepresentable_fixed_width_float(tmp_path):
    d = sample()
    d["lim_pairs"][0, 0] = -1e-100
    with pytest.raises(io.EQDSKFormatError):
        io.write_eqdsk(d, tmp_path / "bad.eqdsk")


def test_malformed_header_extra_fields_rejected(tmp_path):
    p = tmp_path / "bad.eqdsk"
    io.write_eqdsk(sample(), p)
    lines = p.read_text().splitlines()
    lines[0] += "   9"
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(io.EQDSKFormatError):
        io.read_eqdsk(p)


@pytest.mark.parametrize(
    "separator", ["\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
)
def test_title_line_separators_are_rejected_before_open(tmp_path, separator):
    d = sample()
    d["title"] = f"a{separator}b"
    destination = tmp_path / "existing.eqdsk"
    destination.write_text("keep original")
    with pytest.raises(io.EQDSKFormatError, match="line separators"):
        io.write_eqdsk(d, destination)
    assert destination.read_text() == "keep original"


def test_header_fallback_rejects_extra_integer_without_discarding_it(tmp_path):
    destination = tmp_path / "extra.eqdsk"
    io.write_eqdsk(sample(), destination)
    lines = destination.read_text().splitlines()
    lines[0] = "x" * 48 + "9 -1 3 2 4".ljust(16)
    destination.write_text("\n".join(lines) + "\n")
    with pytest.raises(io.EQDSKFormatError, match="exactly four integer fields"):
        io.read_eqdsk(destination)


def test_truncation_trailing_and_wrapper_state(tmp_path):
    p = tmp_path / "fixture.eqdsk"
    io.write_eqdsk(sample(), p)
    original = p.read_text()
    wrapper = io.EQDSK(p)
    old_psi = wrapper["psi"].copy()
    p.write_text("\n".join(original.splitlines()[:-1]) + "\n")
    for strict in (True, False):
        with pytest.raises(io.EQDSKFormatError):
            io.read_eqdsk(p, strict=strict)
    with pytest.raises(io.EQDSKFormatError):
        wrapper.read_eqdsk(p)
    np.testing.assert_array_equal(wrapper["psi"], old_psi)
    p.write_text(original + "trailing\n")
    with pytest.raises(io.EQDSKFormatError):
        io.read_eqdsk(p)
    np.testing.assert_array_equal(io.read_eqdsk(p, strict=False)["psi"], old_psi)


def test_reader_nonfinite_rejected(tmp_path):
    p = tmp_path / "fixture.eqdsk"
    io.write_eqdsk(sample(), p)
    lines = p.read_text().splitlines()
    lines[1] = "".join(f"{v:16}" for v in ("nan", "3", "2", "3", "4"))
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(io.EQDSKFormatError):
        io.read_eqdsk(p)


def test_adjacent_full_width_boundary_counts_roundtrip(tmp_path):
    d = sample()
    d.update(
        nlim_pairs=99999,
        nves_pairs=99999,
        lim_pairs=np.zeros((99999, 2)),
        ves_pairs=np.zeros((99999, 2)),
    )
    p = tmp_path / "boundary-counts.eqdsk"
    io.write_eqdsk(d, p)
    assert next(line for line in p.read_text().splitlines() if line == "9999999999")
    got = io.read_eqdsk(p)
    assert got["nlim_pairs"] == got["nves_pairs"] == 99999
    assert got["lim_pairs"].shape == got["ves_pairs"].shape == (99999, 2)
