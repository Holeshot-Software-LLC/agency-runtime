"""Handle-bound Windows directory rename for ownership-proven retirement."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path


class WindowsHandleRenameError(OSError):
    """An exact open Windows directory handle could not be renamed safely."""


def _directory_metadata(path: Path) -> os.stat_result:
    metadata = os.lstat(path)
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if attributes & reparse or not stat.S_ISDIR(metadata.st_mode):
        raise WindowsHandleRenameError("rename source must be a real directory")
    return metadata


def rename_directory_handle_bound(  # noqa: C901 - one handle must own validate/rename/rollback
    source: Path,
    destination: Path,
    *,
    expected_device: int,
    expected_inode: int,
    expected_destination_device: int,
    expected_destination_inode: int,
    validate: Callable[[], None],
    is_windows: bool | None = None,
) -> None:
    """Rename the exact opened source identity after validation under its handle."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        raise WindowsHandleRenameError("handle-bound rename is only available on Windows")
    try:
        import ctypes
        from ctypes import wintypes

        from agency_runtime.core.windows_private_directory import (
            _close_windows_handle,
            _windows_directory_handle_identity,
            open_windows_directory_guard,
        )

        before = _directory_metadata(source)
        if (
            int(before.st_dev) != expected_device
            or int(getattr(before, "st_ino", 0) or 0) != expected_inode
            or expected_inode <= 0
        ):
            raise WindowsHandleRenameError("rename source identity changed before handle open")
        try:
            os.lstat(destination)
        except FileNotFoundError:
            pass
        else:
            raise WindowsHandleRenameError("rename destination already exists")
        destination_parent = _directory_metadata(destination.parent)
        if int(destination_parent.st_dev) != expected_device:
            raise WindowsHandleRenameError("rename destination is on a different volume")
        if (
            int(destination_parent.st_dev) != expected_destination_device
            or int(getattr(destination_parent, "st_ino", 0) or 0) != expected_destination_inode
            or expected_destination_inode <= 0
        ):
            raise WindowsHandleRenameError(
                "rename destination parent identity changed before handle open"
            )
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(source),
            0x00010000 | 0x00000080 | 0x00100000,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in (None, invalid_handle):
            raise ctypes.WinError(ctypes.get_last_error())
        handle_value = int(handle)
        source_parent_guard = open_windows_directory_guard(source.parent, is_windows=True)
        destination_parent_guard = open_windows_directory_guard(
            destination.parent,
            is_windows=True,
        )
        if source_parent_guard is None or destination_parent_guard is None:
            _close_windows_handle(handle_value)
            if source_parent_guard is not None:
                source_parent_guard.close()
            if destination_parent_guard is not None:
                destination_parent_guard.close()
            raise WindowsHandleRenameError("rename parent identity is unavailable")
        if (
            destination_parent_guard.device != expected_destination_device
            or destination_parent_guard.inode != expected_destination_inode
        ):
            _close_windows_handle(handle_value)
            source_parent_guard.close()
            destination_parent_guard.close()
            raise WindowsHandleRenameError("opened rename destination parent identity changed")
        renamed = False
        try:
            if _windows_directory_handle_identity(handle_value) != expected_inode:
                raise WindowsHandleRenameError(
                    "opened rename source identity is not the plan target"
                )
            current = _directory_metadata(source)
            if (
                int(current.st_dev) != expected_device
                or int(getattr(current, "st_ino", 0) or 0) != expected_inode
            ):
                raise WindowsHandleRenameError("rename source path changed after handle open")

            validate()
            current = _directory_metadata(source)
            if (
                int(current.st_dev) != expected_device
                or int(getattr(current, "st_ino", 0) or 0) != expected_inode
                or _windows_directory_handle_identity(handle_value) != expected_inode
            ):
                raise WindowsHandleRenameError("rename source changed during final validation")

            class FileRenameInfo(ctypes.Structure):
                _fields_ = [
                    ("replace_if_exists", wintypes.BOOL),
                    ("root_directory", wintypes.HANDLE),
                    ("file_name_length", wintypes.DWORD),
                    ("file_name", wintypes.WCHAR * 1),
                ]

            def rename_open_handle(target: Path) -> None:
                parent_guard = (
                    source_parent_guard
                    if target.parent == source.parent
                    else destination_parent_guard
                    if target.parent == destination.parent
                    else None
                )
                if parent_guard is None or not parent_guard.is_current():
                    raise WindowsHandleRenameError("rename destination parent identity changed")
                # Use the absolute path form documented for FILE_RENAME_INFO.
                # The open parent guard (which denies FILE_SHARE_DELETE) keeps
                # that pathname bound to the parent identity validated above;
                # RootDirectory is therefore deliberately NULL.
                encoded = str(target).encode("utf-16-le")
                payload_size = max(
                    ctypes.sizeof(FileRenameInfo),
                    FileRenameInfo.file_name.offset + len(encoded) + ctypes.sizeof(wintypes.WCHAR),
                )
                payload = ctypes.create_string_buffer(payload_size)
                info = ctypes.cast(payload, ctypes.POINTER(FileRenameInfo)).contents
                info.replace_if_exists = False
                info.root_directory = None
                info.file_name_length = len(encoded)
                ctypes.memmove(
                    ctypes.addressof(payload) + FileRenameInfo.file_name.offset,
                    encoded,
                    len(encoded),
                )
                set_information = kernel32.SetFileInformationByHandle
                set_information.argtypes = [
                    wintypes.HANDLE,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                ]
                set_information.restype = wintypes.BOOL
                if not set_information(handle_value, 3, payload, payload_size):
                    raise ctypes.WinError(ctypes.get_last_error())

            rename_open_handle(destination)
            renamed = True
            moved = _directory_metadata(destination)
            if (
                source.exists()
                or int(moved.st_dev) != expected_device
                or int(getattr(moved, "st_ino", 0) or 0) != expected_inode
                or _windows_directory_handle_identity(handle_value) != expected_inode
            ):
                if not source.exists():
                    rename_open_handle(source)
                    renamed = False
                raise WindowsHandleRenameError("handle-bound rename postcondition failed")
        except BaseException:
            if renamed and destination.exists() and not source.exists():
                try:
                    # The original handle still names the same object, so rollback is
                    # identity-bound rather than a second pathname lookup.
                    if not source_parent_guard.is_current():
                        raise WindowsHandleRenameError("rename rollback parent identity changed")
                    encoded = str(source).encode("utf-16-le")

                    class RollbackRenameInfo(ctypes.Structure):
                        _fields_ = [
                            ("replace_if_exists", wintypes.BOOL),
                            ("root_directory", wintypes.HANDLE),
                            ("file_name_length", wintypes.DWORD),
                            ("file_name", wintypes.WCHAR * 1),
                        ]

                    size = max(
                        ctypes.sizeof(RollbackRenameInfo),
                        RollbackRenameInfo.file_name.offset
                        + len(encoded)
                        + ctypes.sizeof(wintypes.WCHAR),
                    )
                    payload = ctypes.create_string_buffer(size)
                    info = ctypes.cast(payload, ctypes.POINTER(RollbackRenameInfo)).contents
                    info.replace_if_exists = False
                    info.root_directory = None
                    info.file_name_length = len(encoded)
                    ctypes.memmove(
                        ctypes.addressof(payload) + RollbackRenameInfo.file_name.offset,
                        encoded,
                        len(encoded),
                    )
                    setter = kernel32.SetFileInformationByHandle
                    setter(handle_value, 3, payload, size)
                except (AttributeError, OSError, TypeError, ValueError):
                    pass
            raise
        finally:
            _close_windows_handle(handle_value)
            source_parent_guard.close()
            destination_parent_guard.close()
    except WindowsHandleRenameError:
        raise
    except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
        raise WindowsHandleRenameError("handle-bound Windows directory rename failed") from exc


__all__ = ["WindowsHandleRenameError", "rename_directory_handle_bound"]
