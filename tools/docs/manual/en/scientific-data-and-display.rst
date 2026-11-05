Scientific data exchange and display boundaries: an extended EQDSK record
=========================================================================

This chapter answers two questions: **how does an extended EQDSK text file become a Python mapping, and when a write or read fails, can the old state and the old file be preserved?** It also explains why this is not a plotting tutorial: the public entry points in this chapter deal only with text, fields and arrays — not with axes, units, color maps, contours or graphics objects.

The extended dialect has three entry points: ``read_eqdsk``, ``write_eqdsk`` and the mutable mapping wrapper ``EQDSK``. They operate on the extended dialect declared by this project, not on standard EFIT gEQDSK, and they do not assign COCOS, units or physical meaning. Standard EFIT G-EQDSK files are read with ``read_geqdsk``, which returns the specification-named arrays and grids and likewise infers no COCOS convention. The so-called "display boundary" is exactly which display decisions the data contract can and cannot support; the code below does not produce any figures.

What a minimal record looks like
--------------------------------

The fixed structure of this dialect is: a 48-character title, four 4-character integers (``cursign, nnr, nnz, nnv``), four 5-value scalar records, five profiles of length ``nnv``, a C-order ``(nnz, nnr)`` psi grid, a q profile, and fixed-width limiter/vessel coordinate pairs. The mapping below satisfies exactly these sizes.

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "minimal.eqdsk"
       write_eqdsk(mapping, path)
       lines = path.read_text().splitlines()
       print("first line:", repr(lines[0]))
       print("line lengths:", [len(line) for line in lines])
       got = read_eqdsk(path)
       print("title:", repr(got["title"]))
       print("dims:", got["cursign"], got["nnr"], got["nnz"], got["nnv"])
       print("psi:", got["psi"].tolist())
       print("R row:", got["R"][0].tolist())
       print("Z col:", got["Z"][:, 0].tolist())
       print("q_flux:", got["q_flux"].tolist())

Actual output:

.. code-block:: text

   first line: 'MINIMAL EXTENDED EQDSK                            -1   3   2   3'
   line lengths: [64, 80, 80, 80, 80, 48, 48, 48, 48, 80, 16, 48, 10, 80, 16]
   title: 'MINIMAL EXTENDED EQDSK                          '
   dims: -1 3 2 3
   psi: [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]
   R row: [0.0, 1.0, 2.0]
   Z col: [-1.0, 1.0]
   q_flux: [0.8, 0.9, 1.0]

The first line is exactly 64 characters: a 48-character title plus four 4-character integers. Lines two through five are the four scalar records, 80 characters each, because each line holds 5 fields of 16 characters. The four profiles are 48 characters each (3 values), and the q profile is also 48; psi has 6 values, so it fills one 80-character line first and leaves a 16-character line; the count record is 10 characters; the limiter/vessel coordinates hold 6 values in total, again 80 plus 16. The ``psi`` read back has shape ``(nnz, nnr) = (2, 3)``, not ``(3, 2)``.

The ``title`` read back carries trailing spaces because the dialect pads the title to 48 characters; this is not whitespace added by the parser. The first row of ``R`` is ``[0, 1, 2]`` and the first column of ``Z`` is ``[-1, 1]``: these two axes are not stored as independent arrays in the file — they are reconstructed at read time from ``rbox``, ``zbox`` and the grid dimensions.

What this section does not establish: these 15 lines of text are not a complete equilibrium solution; ``psi``, ``q_flux`` and the coordinates are just numbers moved according to the dialect; there are no units, COCOS or magnetic-axis semantics; and a correct read-back shape does not prove that the physical content is correct.

Fixed width, field order and strict mode
----------------------------------------

The most direct check after writing and reading back is field-by-field equality. The code below checks psi, the limiter coordinates and the q profile, then appends a record to the end of the file to compare strict and non-strict modes.

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import EQDSKFormatError, read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "roundtrip.eqdsk"
       write_eqdsk(mapping, path)
       got = read_eqdsk(path)
       print("psi equal:", np.array_equal(got["psi"], mapping["psi"]))
       print("lim equal:", np.array_equal(got["lim_pairs"], mapping["lim_pairs"]))
       print("q equal:", np.array_equal(got["q_flux"], mapping["q_flux"]))
       original = path.read_text()
       path.write_text(original + "TRAILING\n")
       try:
           read_eqdsk(path)
       except EQDSKFormatError as error:
           print(type(error).__name__, error)
       relaxed = read_eqdsk(path, strict=False)
       print("relaxed psi:", relaxed["psi"].tolist())

Actual output:

.. code-block:: text

   psi equal: True
   lim equal: True
   q equal: True
   EQDSKFormatError unexpected trailing records after coordinates: 1
   relaxed psi: [[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]

The three ``True`` values show that these fields are still bit-for-bit equal after passing through fixed-width text; they are not approximate floating-point comparisons. Strict mode reports ``EQDSKFormatError`` as soon as it finds an extra record after the declared section; ``strict=False`` allows trailing records but still requires every declared profile, grid and coordinate value to be present. In other words, non-strict mode relaxes only "extra trailing data", not "missing fields" or the fixed-width coordinate format.

What this section does not establish: text round-trip equality does not imply physical fidelity; writing uses ``16.9E`` fields, which can represent only a limited numeric range; strict/non-strict only changes the trailing-data policy and does not change field order, sizes or the origin convention; and it does not provide EFIT magnetic-axis scalars or COCOS interpretation.

Do not destroy old state when something fails
---------------------------------------------

Read failures and write failures are two different state problems. The ``EQDSK`` wrapper parses into a local result first and only then clears and updates itself; ``write_eqdsk`` completes structural validation before opening the target file, so a validation failure does not truncate the old file. The code below creates one truncated read and one write with an unrepresentable origin.

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import EQDSK, EQDSKFormatError, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "state.eqdsk"
       write_eqdsk(mapping, path)
       state = EQDSK(path)
       old_psi = state["psi"].copy()
       print("before:", repr(state["title"]), old_psi.sum())
       lines = path.read_text().splitlines()
       path.write_text("\n".join(lines[:-1]) + "\n")
       try:
           state.read_eqdsk(path)
       except EQDSKFormatError as error:
           print("read error:", error)
       print("after:", repr(state["title"]), state["psi"].sum(),
             np.array_equal(state["psi"], old_psi))
       write_eqdsk(mapping, path)
       original = path.read_text()
       bad = dict(mapping)
       bad["R"], bad["Z"] = np.meshgrid(
           np.linspace(1.0, 3.0, 3), np.linspace(-1.0, 1.0, 2)
       )
       try:
           write_eqdsk(bad, path)
       except EQDSKFormatError as error:
           print("write error:", error)
       print("unchanged:", path.read_text() == original)

Actual output:

.. code-block:: text

   before: 'MINIMAL EXTENDED EQDSK                          ' 15.0
   read error: truncated limiter/vessel coordinates: expected 6 values
   after: 'MINIMAL EXTENDED EQDSK                          ' 15.0 True
   write error: R/Z grid is not representable: extended dialect fixes R origin at 0 and Z at +/-zbox/2
   unchanged: True

After the read failure, the title and ``psi`` of ``state`` are still the old values and the sum of ``psi`` is still ``15.0``; the wrapper did not clear itself before parsing. The write failure is not a disk error: the caller's ``R/Z`` grid starts at ``R=1``, whereas the dialect fixes the ``R`` origin at 0 and reconstructs ``Z`` from ``-zbox/2`` to ``+zbox/2``. That origin cannot be represented, so the write is rejected before the target file is opened and the old file stays byte-for-byte unchanged.

What this section does not establish: this guarantees "a validation failure does not truncate" and "a read failure keeps the old mapping", not atomic writes under arbitrary I/O failure; filesystem errors still propagate directly; it is also not a cross-process transaction or backup mechanism. To preserve an old file, the caller must still manage versions and backups.

Display boundaries: arrays, coordinates and what is not in the contract
-----------------------------------------------------------------------

Finally, look at the data read back as "something to display". The code below prints only array structure and coordinate ranges; it does not draw anything. The point is to show which information needed for display is fixed by the dialect and which is not in the contract at all.

.. code-block:: python

   from pathlib import Path
   from tempfile import TemporaryDirectory
   import numpy as np
   from scirel.io import read_eqdsk, write_eqdsk

   mapping = dict(
       title="MINIMAL EXTENDED EQDSK", cursign=-1, nnr=3, nnz=2, nnv=3,
       rbox=2.0, zbox=2.0, psi_lim=-0.2, Ip=-4.0,
       tor_flux=np.array([1.0, 2.0, 3.0]),
       p_flux=np.array([0.1, 0.2, 0.3]),
       rbphi_flux=np.array([-1.0, 0.0, 1.0]),
       pprime_flux=np.array([0.5, 0.6, 0.7]),
       q_flux=np.array([0.8, 0.9, 1.0]),
       psi=np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]),
       nlim_pairs=2, nves_pairs=1,
       lim_pairs=np.array([[0.0, -1.0], [2.0, 1.0]]),
       ves_pairs=np.array([[0.0, 0.0]]),
   )
   with TemporaryDirectory() as directory:
       path = Path(directory) / "display.eqdsk"
       write_eqdsk(mapping, path)
       got = read_eqdsk(path)
       print("psi shape:", got["psi"].shape)
       print("R range:", got["R"].min(), got["R"].max())
       print("Z range:", got["Z"].min(), got["Z"].max())
       expected_R, _ = np.meshgrid(
           np.linspace(0.0, 2.0, 3), np.linspace(-1.0, 1.0, 2)
       )
       print("R reconstructed:", np.array_equal(got["R"], expected_R))
       print("psi:")
       print(got["psi"])

Actual output:

.. code-block:: text

   psi shape: (2, 3)
   R range: 0.0 2.0
   Z range: -1.0 1.0
   R reconstructed: True
   psi:
   [[0. 1. 2.]
    [3. 4. 5.]]

``psi`` is a two-dimensional ``(nnz, nnr)`` array; ``R`` spans ``0`` to ``2`` and ``Z`` spans ``-1`` to ``1``, and ``R`` is bit-for-bit identical to a mesh built from ``linspace(0, rbox, nnr)``. This information is enough for the caller to decide how to plot, but the contract provides no units, COCOS, axis labels, contour levels, color maps or graphics objects. Scalars such as ``cursign``, ``psi_lim`` and ``Ip`` also carry no physical semantics.

If the caller shifts the figure origin elsewhere, or treats ``R`` as a coordinate stored with an arbitrary starting point, that conflicts with the dialect's fixed-origin convention; the writer detects exactly this unrepresentable case in advance through the ``R/Z`` grid or ``r_origin/z_origin``. Display should follow the same origin, otherwise the array is unchanged but the physical position in the figure has moved.

What this section does not establish: this chapter is not a plotting tutorial and the current asset set contains no plotting functions; the arrays read back are not "figures ready for publication"; without units/COCOS you must not add SI labels to the axes; this is not a compatibility claim for EFIT gEQDSK, GENRAY or any standard equilibrium format; and the text exchange boundary does not validate the physical correctness of an equilibrium solve.

Which entry point to use
------------------------

- Parse a file into a dictionary once: :doc:`../reference/generated/scirel.io.read-eqdsk`.
- Write an already validated mapping to text once: :doc:`../reference/generated/scirel.io.write-eqdsk`.
- Keep a mutable mapping across multiple reads and writes while ensuring a failed read does not destroy the old state: :doc:`../reference/generated/scirel.io.eqdsk-class`.
- Catch ``EQDSKFormatError`` for parsing or validation failures and ``KeyError`` when a writer mapping omits a required key; handle filesystem errors as ordinary I/O exceptions.

The boundary of this chapter is structural exchange: it guarantees field order, sizes, fixed-width representation, the origin convention and failure state, but not standard EFIT compatibility, unit/COCOS assignment, contour selection, plotting or a physical equilibrium. When that information is needed, establish it explicitly on the caller's side and record the dialect and origin convention used; full signatures, parameters and failure behavior are on the API reference pages above.
