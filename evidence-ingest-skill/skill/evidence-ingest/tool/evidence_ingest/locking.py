"""Cross-platform file immutability for the evidence vault.

Strategy (best available, in order):
  * macOS/BSD: ``chflags UF_IMMUTABLE`` (uchg) via ``os.chflags``.
  * Windows: ``FILE_ATTRIBUTE_READONLY`` via ctypes ``SetFileAttributesW``.
  * Fallback everywhere: ``chmod`` read-only bits.

Locking is defense-in-depth, not the authority — byte authority is the
manifest + custody chain; the lock just makes accidental mutation loud.
``merge`` uses unlock -> append -> re-lock inside try/finally so a crash
never leaves the corpus unlocked silently (re-lock happens in finally).
"""
from __future__ import annotations

import ctypes
import os
import stat
import sys
from pathlib import Path

_IS_WINDOWS = sys.platform == "win32"
_HAS_CHFLAGS = hasattr(os, "chflags")

FILE_ATTRIBUTE_READONLY = 0x01
FILE_ATTRIBUTE_NORMAL = 0x80


def _win_set_readonly(path: Path, readonly: bool) -> bool:
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    attrs = kernel32.GetFileAttributesW(str(path))
    if attrs == 0xFFFFFFFF:
        return False
    if readonly:
        new = attrs | FILE_ATTRIBUTE_READONLY
    else:
        new = attrs & ~FILE_ATTRIBUTE_READONLY
        if new == 0:
            new = FILE_ATTRIBUTE_NORMAL
    return bool(kernel32.SetFileAttributesW(str(path), new))


def lock_file(path: Path) -> str:
    """Make a file immutable as strongly as the platform allows.

    Returns the mechanism used ('chflags', 'win-readonly', 'chmod').
    """
    path = Path(path)
    if _HAS_CHFLAGS:
        os.chflags(path, stat.UF_IMMUTABLE)  # type: ignore[attr-defined]
        return "chflags"
    if _IS_WINDOWS and _win_set_readonly(path, True):
        return "win-readonly"
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return "chmod"


def unlock_file(path: Path) -> str:
    path = Path(path)
    if _HAS_CHFLAGS:
        os.chflags(path, 0)  # type: ignore[attr-defined]
        return "chflags"
    if _IS_WINDOWS and _win_set_readonly(path, False):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        return "win-readonly"
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    return "chmod"


def lock_tree(root: Path) -> int:
    """Lock every file under root; returns count. Directories left traversable."""
    n = 0
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and not p.is_symlink():
            lock_file(p)
            n += 1
    return n


def unlock_tree(root: Path) -> int:
    n = 0
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and not p.is_symlink():
            unlock_file(p)
            n += 1
    return n
