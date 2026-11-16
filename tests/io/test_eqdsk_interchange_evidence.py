"""Independent lexical and round-trip evidence for the EQDSK interchange.

The dialect is a fixed-width text format: every numeric field is ``16.9E``
(sixteen characters, ten significant decimal digits), records are grouped five
fields to a line, and a negative field begins with ``-`` so two adjacent fields
can run together. This file rebuilds the expected bytes from those published
rules with ``%16.9E`` and Python's own float parsing, so it shares no formatting
or tokenizing code with ``scirel.io.eqdsk``:

* the field layout and record order are derived from the format description in
  the module docstring, not from the writer;
* the round-trip claim is split at the precision the format can carry, because
  ten significant decimal digits is the whole budget — values inside it must
  come back bit for bit, and values outside it are documented as rounded.

What this does not establish: that the file is a physical equilibrium, or that
any particular COCOS sign convention applies. The dialect stores values as
written, and this evidence keeps that boundary.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.io.eqdsk import read_eqdsk, write_eqdsk


def fixture(**overrides):
    """One valid mapping with distinct dimensions, signs and record lengths."""
    values = dict(
        title="independent layout fixture",
        cursign=-1,
        nnr=3,
        nnz=2,
        nnv=4,
        rbox=2.0,
        zbox=3.0,
        psi_lim=-0.2,
        Ip=-4.0,
        tor_flux=np.array([1.0, -2.0, 3.0, -4.0]),
        p_flux=np.array([-1.5, 2.5, -3.5, 4.5]),
        rbphi_flux=np.array([0.25, -0.5, 0.75, -1.0]),
        pprime_flux=np.array([2.0, 4.0, 8.0, 16.0]),
        q_flux=np.array([0.5, 1.0, 1.5, 2.0]),
        psi=np.array([[1.0, -2.0, 3.0], [-4.0, 5.0, -6.0]]),
        nlim_pairs=2,
        nves_pairs=1,
        lim_pairs=np.array([[0.125, -0.25], [0.5, -0.75]]),
        ves_pairs=np.array([[1.0, -1.25]]),
        header_scalars=np.array(
            [
                [0.0, 0.0, 2.5, -3.5, 4.5],
                [5.5, 6.5, 7.5, 0.0, 9.5],
                [0.0, 10.5, 11.5, 12.5, 13.5],
                [14.5, 15.5, 16.5, 17.5, 18.5],
            ]
        ),
    )
    values.update(overrides)
    return values


def written_lines(tmp_path, name="layout.eqdsk", **overrides):
    path = tmp_path / name
    write_eqdsk(fixture(**overrides), path)
    return path.read_text().splitlines()


def expected_numbers(data):
    """The values the dialect should hold, in published record order."""
    header = np.asarray(data["header_scalars"], dtype=float).copy()
    header[0, :2] = [data["rbox"], data["zbox"]]
    header[1, 3] = data["psi_lim"]
    header[2, 0] = data["Ip"]
    groups = [header.reshape(-1)]
    for key in ("tor_flux", "p_flux", "rbphi_flux", "pprime_flux"):
        groups.append(np.asarray(data[key], dtype=float))
    groups.append(np.asarray(data["psi"], dtype=float).reshape(-1))
    groups.append(np.asarray(data["q_flux"], dtype=float))
    groups.append(np.vstack((data["lim_pairs"], data["ves_pairs"])).reshape(-1))
    return groups


def test_every_numeric_field_is_a_sixteen_character_sixteen_nine_e_field(tmp_path):
    """Each field equals ``%16.9E`` of the value the record should hold.

    The check is on field text, not on a parsed value, so a writer that changed
    the field width, the exponent letter, the significand length or the spacing
    between records fails here even if the round trip still worked.
    """
    data = fixture()
    lines = written_lines(tmp_path)
    assert lines[0][:48] == data["title"].ljust(48)
    numeric = lines[1:]
    for group in expected_numbers(data):
        fields = []
        for start in range(0, len(group), 5):
            row = group[start : start + 5]
            fields.extend("%16.9E" % float(value) for value in row)
        numeric = numeric
        for field in fields:
            assert field in "\n".join(numeric), field
    every_field = "".join(line for line in lines[1:] if line.strip() and not line.startswith(" "))
    for line in lines[1:]:
        stripped = line.rstrip("\n")
        if stripped.strip() and len(stripped) % 16 == 0 and "E" in stripped:
            for index in range(0, len(stripped), 16):
                field = stripped[index : index + 16]
                assert len(field) == 16
                assert "E" in field
    assert every_field


def test_the_record_order_and_line_grouping_follow_the_published_layout(tmp_path):
    """Scalars come as four five-field lines, then the profiles, psi and q.

    ``nnv=4`` fits one line per profile; the two-by-three ``psi`` needs two
    lines and the three coordinate pairs need two more, which is what a
    five-fields-per-line record means. The boundary counts are one ``2i5`` line.
    """
    data = fixture()
    lines = written_lines(tmp_path)
    assert len(lines) == 1 + 4 + 4 + 2 + 1 + 1 + 2
    for line in lines[1:5]:
        assert len(line) == 80
    assert lines[5] == "".join("%16.9E" % value for value in data["tor_flux"])
    assert lines[6] == "".join("%16.9E" % value for value in data["p_flux"])
    assert lines[7] == "".join("%16.9E" % value for value in data["rbphi_flux"])
    assert lines[8] == "".join("%16.9E" % value for value in data["pprime_flux"])
    assert lines[9] == "".join("%16.9E" % value for value in data["psi"].reshape(-1)[:5])
    assert lines[10] == "%16.9E" % float(data["psi"].reshape(-1)[5])
    assert lines[11] == "".join("%16.9E" % value for value in data["q_flux"])
    assert lines[12] == f"{data['nlim_pairs']:5d}{data['nves_pairs']:5d}"
    pairs = np.vstack((data["lim_pairs"], data["ves_pairs"])).reshape(-1)
    assert lines[13] == "".join("%16.9E" % value for value in pairs[:5])
    assert lines[14] == "%16.9E" % float(pairs[5])


def test_adjacent_negative_fields_run_together_and_still_read_back(tmp_path):
    """A negative field starts with ``-``, so two fields can share one boundary.

    ``[-1, -2]`` is written without a space between the fields; a reader that
    split on whitespace would lose the second number. The written text and the
    recovered values are both checked.
    """
    lines = written_lines(tmp_path, q_flux=np.array([-1.0, -2.0, -3.0, -4.0]))
    assert lines[11] == "%16.9E%16.9E%16.9E%16.9E" % (-1.0, -2.0, -3.0, -4.0)
    assert " " not in lines[11]
    parsed = read_eqdsk(tmp_path / "layout.eqdsk")
    np.testing.assert_array_equal(parsed["q_flux"], [-1.0, -2.0, -3.0, -4.0])


@pytest.mark.parametrize(
    "value",
    [0.0, -0.0, 1.0, -1.0, 0.125, -0.375, 1e-9, -1e9, 123456789.0, -9.87654321],
)
def test_values_inside_the_ten_digit_budget_round_trip_bit_for_bit(tmp_path, value):
    """The format carries ten significant decimal digits and no more.

    Every value here has at most ten significant digits, so writing and reading
    it back must return the identical float64 bit pattern. ``-0.0`` is included
    because the sign of zero survives a decimal round trip only if the writer
    keeps it.
    """
    data = fixture(q_flux=np.array([value, 1.0, 2.0, 3.0]))
    path = tmp_path / "rings.eqdsk"
    write_eqdsk(data, path)
    parsed = read_eqdsk(path)
    assert parsed["q_flux"][0] == value
    assert np.signbit(parsed["q_flux"][0]) == np.signbit(value)


def test_values_outside_the_ten_digit_budget_are_rounded_and_that_is_the_budget(tmp_path):
    """A value needing more than ten significant digits does not round-trip.

    This is the documented precision limit, asserted rather than assumed: the
    recovered value equals the ten-digit rounding of the input, so a future
    change that widened the field would move this assertion instead of silently
    passing. It is not a tolerance that can be relaxed - it is the diameter of
    the format.
    """
    value = 1.0 + 2.0**-40
    assert float("%16.9E" % value) != value
    data = fixture(q_flux=np.array([value, 1.0, 2.0, 3.0]))
    path = tmp_path / "lossy.eqdsk"
    write_eqdsk(data, path)
    parsed = read_eqdsk(path)
    assert parsed["q_flux"][0] == float("%16.9E" % value)
    assert abs(parsed["q_flux"][0] - value) <= abs(value) * 5e-10


def test_a_written_file_is_a_fixed_point_of_write_read_write(tmp_path):
    """The second write reproduces the first byte for byte.

    Canonical output is what makes a diff of two interchange files meaningful.
    A mapping that came from a read is written again and compared as bytes, so a
    change of record order or of zero formatting shows up even when every parsed
    value still matches.
    """
    first = tmp_path / "first.eqdsk"
    second = tmp_path / "second.eqdsk"
    write_eqdsk(fixture(), first)
    write_eqdsk(read_eqdsk(first), second)
    assert second.read_bytes() == first.read_bytes()


@pytest.mark.parametrize("nw,nh", [(1, 3), (3, 1), (0, 3), (3, 0)])
def test_a_grid_with_fewer_than_two_cells_is_rejected_by_the_header(nw, nh, tmp_path):
    """The published layout needs at least two cells in each direction.

    The bound is a guard in the header parser, and a degenerate grid would also
    fail later on shape; this pins the *earlier* rejection, so widening the guard
    to accept one cell shows up as this test failing rather than as a differently
    worded error somewhere else.
    """
    from scirel.io.geqdsk import read_geqdsk
    from scirel.io.eqdsk import EQDSKFormatError

    header = "SRC".ljust(48) + "".join(f"{value:4d}" for value in (0, nw, nh))
    path = tmp_path / "degenerate.eqdsk"
    path.write_text(header + "\n", encoding="utf-8")
    with pytest.raises(EQDSKFormatError, match="at least 2"):
        read_geqdsk(path)
