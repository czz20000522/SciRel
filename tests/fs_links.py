"""Real filesystem link fixtures that do not require Windows symlink privileges.

Directory junctions exercise target redirection on Windows. The opaque file
reparse fixture exercises rejection of a file's reparse metadata before opening
it; it does not redirect to the supplied target. POSIX keeps real symlinks for
both boundaries. Neither fixture skips a failed setup or changes host policy.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


def directory_link(link: Path, target: Path) -> Path:
    """Create a real directory junction on Windows, or a POSIX symlink."""
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
            timeout=10,
        )
        assert link.is_junction()
    else:
        link.symlink_to(target, target_is_directory=True)
        assert link.is_symlink()
    assert link.resolve() == target.resolve()
    return link


def file_link_or_reparse(link: Path, target: Path) -> Path:
    """Create a POSIX file symlink or an opaque Windows file reparse point.

    Windows uses a test-only non-Microsoft tag and GUID, with no filter driver
    or redirect target. Its bytes start as an exact copy of ``target``, but a
    normal open cannot follow the opaque reparse point. Tests must therefore
    assert explicit metadata rejection, not accept a subsequent read error.
    """
    if os.name != "nt":
        link.symlink_to(target)
        assert link.is_symlink()
        return link

    import ctypes
    from ctypes import wintypes
    import struct
    import uuid

    with link.open("xb") as stream:
        stream.write(target.read_bytes())
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.DeviceIoControl.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    kernel.DeviceIoControl.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # OPEN_EXISTING + FILE_FLAG_OPEN_REPARSE_POINT, with write access and all
    # sharing modes. Only this newly created test file can be tagged.
    handle = kernel.CreateFileW(str(link), 0x40000000, 7, None, 3, 0x00200000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        data = (
            struct.pack(
                "<IHH16s", 0x42, 4, 0, uuid.UUID("58b7ef31-4074-4d72-83e2-9f4b9b219dda").bytes_le
            )
            + b"test"
        )
        buffer = ctypes.create_string_buffer(data)
        returned = wintypes.DWORD()
        if not kernel.DeviceIoControl(
            handle, 0x000900A4, buffer, len(data), None, 0, ctypes.byref(returned), None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)
    info = link.lstat()
    assert info.st_file_attributes & 0x400
    assert info.st_reparse_tag == 0x42
    assert not link.is_symlink() and not link.is_junction()
    return link
