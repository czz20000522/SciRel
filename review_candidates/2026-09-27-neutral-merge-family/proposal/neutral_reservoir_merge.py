"""FIDASIM local neutral-reservoir merge (source ``merge_reservoirs``).

Source: the saved package ``中性库合并`` (source anchor
``src/fidasim.f90:10343-10392`` ``merge_reservoirs(res1,res2)`` with the
inline ``update_reservoir`` fill/replace/skip semantics at
:10394-10430): one explicit local merge of two reservoir states.
Empty target/empty source, both-nonfull ordered append, the
full/nonfull orientation swap with append, and the both-full
per-slot source selection by the seen-record probability are replayed
in source order.  Every random number the merge could consume -- the
lazy-init uniform pair, the appended-replacement slot indices and
uniform pairs, and the both-full per-slot source-selection uniforms --
is an explicit caller input; no RNG is drawn internally.

Source quirks preserved verbatim (pinned by regressions, not repaired):

- Lazy target initialization consumes the uniform pair as
  ``W = exp(log(u0)/k)`` and ``i = k + floor(log(u1)/log(1-W)) + 1``
  with ``n`` set to 1, only when ``target_n <= 0``.
- Replacement updates multiply ``W`` first and then draw the next
  replacement horizon from the *updated* ``W``.
- The both-full probability is computed in float32,
  ``p = float32(n1)/float32(n1+n2)``, and a source slot is selected
  only when ``uniform > p`` (strict comparison).
- After any nonempty merge the source state output is the merged
  target state broadcast back (``res2 = res1``), not the pre-merge
  source state; the source-empty branch returns the target untouched.
- The appended-record walk writes the slot ``target_n - 1`` while
  ``target_n <= k`` and otherwise consults the replacement horizon.

Registered hardenings against the saved arm (each with a discriminating
regression): reservoir metadata and capacity accept genuine integers
including ``np.integer`` (the saved arm's ``type(...) is int`` rejected
``np.int64``) but reject bools, ``np.bool_`` and whole-number floats;
``W`` and the replacement slot indices must be genuine finite
numbers/integers without bool coercion (the saved arm's ``isinstance``
accepted ``W=True`` and its ``astype(int)`` silently truncated
whole-number float indices).  The reservoir-sampling half composes with
the density half through the task graph
``scirel.fusion.neutral-population-state-merge``; MPI owners, HDF5
writers and the neutral-bank lifecycle stay outside this relation.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

__all__ = ["merge_neutral_reservoirs"]

_BRANCHES = (
    "source_empty",
    "both_nonfull",
    "target_nonfull_source_full",
    "target_full_source_nonfull",
    "both_full",
)


def _finite_array(value, *, ndim: int, name: str) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.dtype == np.bool_ or (
        array.dtype == np.object_
        and any(isinstance(item, (bool, np.bool_)) for item in array.flat)
    ):
        # A bool dtype array and a mixed object array such as [True, 1.0]
        # would both be silently numerified by astype(float) (registered
        # hardening: the saved arm accepted the coercion).
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        array = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with ndim={ndim}")
    return array


def _open_uniform_pair(value, *, name: str) -> np.ndarray:
    array = _finite_array(value, ndim=1, name=name)
    if array.shape != (2,) or np.any(array <= 0.0) or np.any(array >= 1.0):
        raise ValueError(f"{name} must have shape (2) and values in (0,1)")
    return array


def _genuine_integer(value, *, name: str, nonnegative: bool) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be a genuine integer (registered hardening)")
    result = int(value)
    if nonnegative and result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _state_arrays(weights, velocities, *, reservoir_size: int, name: str):
    weight_array = _finite_array(weights, ndim=1, name=f"{name}_slot_weights")
    velocity_array = _finite_array(velocities, ndim=2, name=f"{name}_slot_velocities_cm_s")
    if weight_array.shape != (reservoir_size,) or velocity_array.shape != (reservoir_size, 3):
        raise ValueError(f"{name} slot arrays must have shapes ({reservoir_size},) and ({reservoir_size},3)")
    if np.any(weight_array < 0.0):
        raise ValueError(f"{name}_slot_weights must be nonnegative")
    return weight_array.copy(), velocity_array.copy()


def _metadata(n, i, W, *, name: str):
    seen = _genuine_integer(n, name=f"{name}_n", nonnegative=True)
    horizon = _genuine_integer(i, name=f"{name}_i", nonnegative=True)
    if isinstance(W, (bool, np.bool_)) or not isinstance(W, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name}_W must be a finite nonnegative number (registered hardening)")
    weight = float(W)
    if not math.isfinite(weight) or weight < 0.0:
        raise ValueError(f"{name}_W must be finite and nonnegative")
    return seen, horizon, weight


def _integer_indices(value, *, reservoir_size: int, name: str) -> np.ndarray:
    if isinstance(value, (str, bytes, Mapping)):
        raise ValueError(f"{name} must be a sequence of genuine integers (registered hardening)")
    try:
        entries = list(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a sequence of genuine integers (registered hardening)") from exc
    for entry in entries:
        if isinstance(entry, (bool, np.bool_)) or not isinstance(entry, (int, np.integer)):
            raise ValueError(f"{name} must contain genuine integers (registered hardening)")
    indices = np.asarray([int(entry) for entry in entries], dtype=np.int64)
    if np.any(indices < 0) or np.any(indices >= reservoir_size):
        raise ValueError(f"{name} contains an out-of-range 0-based slot")
    return indices


def merge_neutral_reservoirs(
    *,
    target_n,
    target_i,
    target_W,
    target_slot_weights,
    target_slot_velocities_cm_s,
    source_n,
    source_i,
    source_W,
    source_slot_weights,
    source_slot_velocities_cm_s,
    target_initialization_uniforms,
    transfer_replacement_indices,
    transfer_replacement_uniforms,
    full_full_uniforms,
    reservoir_size=50,
):
    """Replay one source-shaped ``merge_reservoirs`` call."""

    reservoir_size = _genuine_integer(reservoir_size, name="reservoir_size", nonnegative=False)
    if reservoir_size < 1:
        raise ValueError("reservoir_size must be a positive integer")
    target_n, target_i, target_W = _metadata(target_n, target_i, target_W, name="target")
    source_n, source_i, source_W = _metadata(source_n, source_i, source_W, name="source")
    target_weights, target_velocities = _state_arrays(
        target_slot_weights, target_slot_velocities_cm_s, reservoir_size=reservoir_size, name="target"
    )
    source_weights, source_velocities = _state_arrays(
        source_slot_weights, source_slot_velocities_cm_s, reservoir_size=reservoir_size, name="source"
    )
    init_uniforms = _open_uniform_pair(target_initialization_uniforms, name="target_initialization_uniforms")
    transfer_indices = _integer_indices(
        transfer_replacement_indices, reservoir_size=reservoir_size, name="transfer_replacement_indices"
    )
    transfer_uniforms = _finite_array(
        transfer_replacement_uniforms, ndim=2, name="transfer_replacement_uniforms"
    )
    if transfer_uniforms.shape != (transfer_indices.size, 2):
        raise ValueError("transfer_replacement_uniforms must match transfer_replacement_indices")
    if np.any(transfer_uniforms <= 0.0) or np.any(transfer_uniforms >= 1.0):
        raise ValueError("transfer_replacement_uniforms must contain values in (0,1)")
    merge_uniforms = _finite_array(full_full_uniforms, ndim=1, name="full_full_uniforms")
    if np.any(merge_uniforms < 0.0) or np.any(merge_uniforms >= 1.0):
        raise ValueError("full_full_uniforms must contain values in [0,1)")

    # Source NeutralParticle defaults are already part of the explicit input
    # slot arrays; no unobserved slot state is synthesized here.
    if target_n <= 0:
        target_n = 1
        target_W = math.exp(math.log(float(init_uniforms[0])) / reservoir_size)
        target_i = reservoir_size + math.floor(
            math.log(float(init_uniforms[1])) / math.log(1.0 - target_W)
        ) + 1

    transfer_cursor = 0
    transfer_actions: list[str] = []
    transfer_slots: list[int] = []

    def update_target(velocity: np.ndarray, weight: float) -> None:
        nonlocal target_n, target_i, target_W, transfer_cursor
        if target_n <= reservoir_size:
            slot = target_n - 1
            target_weights[slot] = float(weight)
            target_velocities[slot] = velocity
            transfer_actions.append("fill")
            transfer_slots.append(slot)
        elif target_n == target_i:
            if transfer_cursor >= transfer_indices.size:
                raise ValueError("transfer replacement records are insufficient")
            slot = int(transfer_indices[transfer_cursor])
            a, b = transfer_uniforms[transfer_cursor]
            target_weights[slot] = float(weight)
            target_velocities[slot] = velocity
            target_W *= math.exp(math.log(float(a)) / reservoir_size)
            target_i += math.floor(math.log(float(b)) / math.log(1.0 - target_W)) + 1
            transfer_cursor += 1
            transfer_actions.append("replace")
            transfer_slots.append(slot)
        else:
            transfer_actions.append("skip")
            transfer_slots.append(-1)
        target_n += 1

    if source_n <= 0:
        if merge_uniforms.size != 0 or transfer_cursor != transfer_indices.size:
            raise ValueError("source-empty merge cannot consume merge records")
        branch = "source_empty"
        target_after = (target_n, target_i, target_W, target_weights, target_velocities)
        source_after = (source_n, source_i, source_W, source_weights, source_velocities)
        probability = None
    else:
        if target_n <= reservoir_size and source_n <= reservoir_size:
            branch = "both_nonfull"
            for slot in range(source_n):
                update_target(source_velocities[slot], source_weights[slot])
        else:
            swapped = False
            if target_n <= reservoir_size:
                swapped = True
                target_n, source_n = source_n, target_n
                target_i, source_i = source_i, target_i
                target_W, source_W = source_W, target_W
                target_weights, source_weights = source_weights, target_weights
                target_velocities, source_velocities = source_velocities, target_velocities
            if source_n <= reservoir_size:
                branch = "target_nonfull_source_full" if swapped else "target_full_source_nonfull"
                for slot in range(source_n):
                    update_target(source_velocities[slot], source_weights[slot])
            else:
                branch = "both_full"
                if merge_uniforms.shape != (reservoir_size,):
                    raise ValueError("full_full_uniforms must contain exactly k values")
                probability = float(np.float32(target_n) / np.float32(target_n + source_n))
                for slot, uniform in enumerate(merge_uniforms):
                    if float(uniform) > probability:
                        target_weights[slot] = source_weights[slot]
                        target_velocities[slot] = source_velocities[slot]
        if branch != "both_full":
            probability = None
        if transfer_cursor != transfer_indices.size:
            raise ValueError("transfer replacement records contain unused entries")
        if merge_uniforms.size != (reservoir_size if branch == "both_full" else 0):
            raise ValueError("full_full_uniforms are only valid for the both_full branch")
        target_after = (target_n, target_i, target_W, target_weights, target_velocities)
        source_after = (target_n, target_i, target_W, target_weights.copy(), target_velocities.copy())

    return {
        "target_n": int(target_after[0]),
        "target_i": int(target_after[1]),
        "target_W": float(target_after[2]),
        "target_slot_weights": target_after[3].copy(),
        "target_slot_velocities_cm_s": target_after[4].copy(),
        "source_n": int(source_after[0]),
        "source_i": int(source_after[1]),
        "source_W": float(source_after[2]),
        "source_slot_weights": source_after[3].copy(),
        "source_slot_velocities_cm_s": source_after[4].copy(),
        "branch": branch,
        "transfer_actions": transfer_actions,
        "transfer_updated_slots": np.asarray(transfer_slots, dtype=np.int64),
        "transfer_replacement_count": int(transfer_cursor),
        "full_full_probability": probability,
    }
