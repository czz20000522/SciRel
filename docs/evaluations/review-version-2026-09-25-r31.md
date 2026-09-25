# SciRel clean-install evidence successor r31

Status: development review pending, not expert-approved, trusted, or publicly released. The qualified L1 delivery root remains empty. There is no trusted baseline, so the first expert review still covers all 68 public assets; r30 is only a development comparison.

## Change and review scope

No scientific implementation, public signature, exact asset document, catalog record, or wheel changed from r30. This successor binds stronger installation evidence for the same `0.1.0.dev16` development wheel. It does not extend the physical applicability or source-project coverage of any asset. The earlier r30 snapshot remains unchanged.

The prior runtime check used a venv with system site-packages and therefore reused host NumPy/SciPy. This check instead created a Python 3.14.3 Windows venv with `include-system-site-packages = false`, installed SciRel, NumPy, SciPy, pytest and pytest's dependencies from a local wheelhouse using `--no-index`, and confirmed SciRel, NumPy and SciPy all import from that venv's `site-packages`. The exact wheel and dependency hashes, commands, selected tests and output are in the frozen test evidence.

The isolated wheel ran 626 selected scientific and composition tests successfully; 43 source-dependent tests skipped because no qualified L1 root was configured. All 68 exact documents passed installed-runtime signature and executable-example validation. The three source-free user acceptance tasks passed, with 82 installed SciRel Python files matching the wheel. The tests and document inputs were read from this repository, but the runtime SciRel package and scientific dependencies were not imported from the source tree or host packages.

This proves an offline installation using the local wheelhouse for this Python/Windows environment; the dependency wheels themselves are not part of the frozen review snapshot. It does not prove other Python versions or platforms, complete source reproduction, license clearance, expert scientific approval, trusted promotion, or public release. The first review set remains all 68 assets; this evidence-only successor does not confer a scientific review exemption.
