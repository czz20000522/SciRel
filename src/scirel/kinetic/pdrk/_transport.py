"""Private D1 transport draft; contains no PDRK science or source resources.

Wrappers own a fixed action registry. Callers supply MAT-compatible named state,
never native code. Each invocation has a fresh process, workspace, and temp HOME.
Container mounts/network policy, native fidelity and admissible ports belong to
the integrating wrapper and its frozen source contract.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Any
import hashlib
import json
import os
import re
import subprocess
import tempfile
import shutil
import uuid
import time

import numpy as np

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_RESERVED = "scirel_transport_"


@dataclass(frozen=True)
class NativeAction:
    """Trusted wrapper declaration, not a user-supplied execution request.

    Paths must resolve below the explicit bundled resource root. Output names
    are a closed allowlist: no workspace dump, graphics, or function handles.
    Inputs are intentionally variable names/state arrays, not native expressions.
    """

    script: str
    outputs: tuple[str, ...]
    input_names: tuple[str, ...]
    support_dirs: tuple[str, ...] = ()
    stdin: str | None = None


@dataclass(frozen=True)
class NativeReceipt:
    action: str
    command: tuple[str, ...]
    returncode: int | None
    elapsed_seconds: float
    stdout: str
    stderr: str
    timed_out: bool
    script_sha256: str
    input_sha256: str
    output_sha256: str | None
    error: str | None


@dataclass(frozen=True)
class NativeResult:
    state: Mapping[str, Any]
    receipt: NativeReceipt


class NativeExecutionError(RuntimeError):
    def __init__(self, receipt: NativeReceipt):
        self.receipt = receipt
        super().__init__(receipt.error or "native execution failed")


def _name(value: str) -> str:
    if not _NAME.fullmatch(value) or value.startswith(_RESERVED):
        raise ValueError(f"unsupported or reserved state name: {value!r}")
    return value


def _literal(value: Path | str) -> str:
    # MATLAB/Octave string literal escaping; no shell invocation is involved.
    return "'" + str(value).replace("'", "''") + "'"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state_value(value: Any) -> Any:
    # Sparse state validation is part of transport invocation, not module
    # discovery.  Keep this private helper's SciPy dependency local so the
    # PDRK transport facade can be inspected without initializing SciPy.
    from scipy import sparse

    if sparse.issparse(value):
        if value.dtype.kind not in "biufc":
            raise TypeError("sparse state requires numeric/logical dtype")
        return value
    array = np.asarray(value)
    # Objects and structs need a separate explicit contract.
    if array.dtype.kind not in "biufcUS":
        raise TypeError(f"state requires numeric/logical/string arrays, got {array.dtype}")
    if array.dtype.kind == "S":
        array = array.astype("U")
    return array


class NativeTransport:
    def __init__(self, resource_root: Path, actions: Mapping[str, NativeAction],
                 *, executable: str = "octave", timeout_seconds: float = 120):
        self.resource_root = Path(resource_root).resolve(strict=True)
        if not self.resource_root.is_dir():
            raise ValueError("native resource root must be a directory")
        if timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self._actions = MappingProxyType(dict(actions))
        for key, action in self._actions.items():
            _name(key)
            self._resource(action.script, directory=False)
            for directory in action.support_dirs:
                self._resource(directory, directory=True)
            if len(set(action.outputs)) != len(action.outputs):
                raise ValueError("duplicate output name")
            if len(set(action.input_names)) != len(action.input_names):
                raise ValueError("duplicate input name")
            for name in (*action.outputs, *action.input_names):
                _name(name)

    def _resource(self, relative: str, *, directory: bool) -> Path:
        path = (self.resource_root / relative).resolve(strict=True)
        if not path.is_relative_to(self.resource_root):
            raise ValueError("native resource escapes bundled root")
        if not (path.is_dir() if directory else path.is_file()):
            raise ValueError("native resource has wrong type")
        return path

    def invoke(self, action_name: str, state: Mapping[str, Any]) -> NativeResult:
        # An unknown action and invalid state fail before any process starts.
        action = self._actions[action_name]
        if set(state) != set(action.input_names):
            raise ValueError("state names must exactly match the wrapper action's input_names")
        inputs = {_name(k): _state_value(v) for k, v in state.items()}
        script = self._resource(action.script, directory=False)
        with tempfile.TemporaryDirectory(prefix="scirel-native-") as temporary:
            working = Path(temporary)
            in_mat, out_mat = working / "input.mat", working / "output.mat"
            driver = working / "driver.m"
            from scipy.io import savemat

            savemat(in_mat, inputs, oned_as="row")
            input_digest = _digest(in_mat)
            script_digest = _digest(script)
            paths = [self.resource_root, *(self._resource(p, directory=True)
                                          for p in action.support_dirs)]
            driver.write_text(self._driver(script, paths, in_mat, out_mat, action.outputs),
                              encoding="utf-8")
            command = (self.executable, "--no-gui", "--quiet", "--no-init-file",
                       "--no-site-file", str(driver))
            env = dict(os.environ)
            env.update(HOME=str(working), OCTAVE_HISTFILE=os.devnull, OCTAVE_PATH="")
            started = time.monotonic()
            code, stdout, stderr, timed_out, error = None, "", "", False, None
            try:
                completed = subprocess.run(command, cwd=working, env=env, capture_output=True,
                                           text=True, input=action.stdin, timeout=self.timeout_seconds, check=False)
                code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
                if code != 0:
                    error = f"native action exited with status {code}"
                elif not out_mat.is_file():
                    error = "native action exited successfully without its output MAT"
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = self._text(exc.stdout)
                stderr = self._text(exc.stderr)
                error = f"native action exceeded {self.timeout_seconds} seconds"
            except OSError as exc:
                error = f"native process could not start: {type(exc).__name__}: {exc}"
            output_digest = _digest(out_mat) if out_mat.is_file() else None
            result: dict[str, Any] = {}
            if error is None:
                try:
                    from scipy.io import loadmat

                    loaded = loadmat(out_mat, squeeze_me=False, chars_as_strings=True,
                                     mat_dtype=False)
                    if set(k for k in loaded if not k.startswith("__")) != set(action.outputs):
                        raise ValueError("native output ports do not match declared outputs")
                    result = {name: _state_value(loaded[name]) for name in action.outputs}
                except Exception as exc:
                    error = f"native output decode failed: {type(exc).__name__}: {exc}"
            receipt = NativeReceipt(action_name, command, code, time.monotonic() - started,
                                    stdout, stderr, timed_out, script_digest, input_digest,
                                    output_digest, error)
            evidence_root = os.environ.get('SCIREL_NATIVE_EVIDENCE_DIR')
            if evidence_root:
                evidence = Path(evidence_root) / (action_name+'-'+uuid.uuid4().hex)
                evidence.mkdir(parents=True,exist_ok=False)
                shutil.copy2(in_mat,evidence/'input.mat')
                shutil.copy2(driver,evidence/'driver.m')
                if out_mat.is_file():shutil.copy2(out_mat,evidence/'output.mat')
                (evidence/'stdout.txt').write_text(stdout,encoding='utf-8')
                (evidence/'stderr.txt').write_text(stderr,encoding='utf-8')
                (evidence/'receipt.json').write_text(json.dumps(asdict(receipt),indent=2)+'\n')
            if error is not None:
                raise NativeExecutionError(receipt)
            return NativeResult(MappingProxyType(result), receipt)

    @staticmethod
    def _text(value: bytes | str | None) -> str:
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""

    @staticmethod
    def _driver(script: Path, paths: list[Path], in_mat: Path, out_mat: Path,
                outputs: tuple[str, ...]) -> str:
        lines = ["more off;", "try"]
        lines.extend(f"  addpath({_literal(path)});" for path in paths)
        # source executes in this workspace without run() changing into resources.
        lines += [f"  load({_literal(in_mat)});", f"  source({_literal(script)});"]
        # Bookkeeping begins after native execution, so source-local clears do
        # not destroy transport control state. Exact names/paths are literals.
        lines += ["  scirel_transport_state = struct();"]
        for name in outputs:
            lines += [
                f"  if ~exist('{name}', 'var')",
                f"    error('SciRel:MissingOutput', 'missing declared output {name}');",
                "  endif",
                f"  if ~(isnumeric({name}) || islogical({name}) || ischar({name}))",
                f"    error('SciRel:OutputType', 'unsupported declared output {name}');",
                "  endif",
                f"  scirel_transport_state.{name} = {name};",
            ]
        lines += [f"  save('-mat7-binary', {_literal(out_mat)}, '-struct', 'scirel_transport_state');",
                  "catch scirel_transport_error",
                  "  fprintf(2, 'SCIREL_NATIVE_FAILURE [%s] %s\\n', scirel_transport_error.identifier, scirel_transport_error.message);",
                  "  for scirel_transport_frame = scirel_transport_error.stack(:)'",
                  "    fprintf(2, '  %s:%d\\n', scirel_transport_frame.file, scirel_transport_frame.line);",
                  "  endfor", "  exit(1);", "end_try_catch", "exit(0);", ""]
        return "\n".join(lines)


def write_receipt(path: Path, receipt: NativeReceipt) -> None:
    """Caller-controlled evidence persistence after temporary files disappear."""
    Path(path).write_text(json.dumps(asdict(receipt), ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
