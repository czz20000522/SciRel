"""Kinetic-dispersion test oracles and internal workflow entry points.

These modules are test helpers, not package data or public API. Keeping them
inside a regular package under ``tests/kinetic`` makes their imports stable:
``tests`` is on ``sys.path`` (see ``pyproject.toml``), so
``kinetic.dispersion._dispersion_workflows`` resolves without manipulating
``sys.path`` from individual test modules.
"""
