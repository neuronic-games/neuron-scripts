# user_folders.py
# OS-specific lookup of well-known user folders (currently just Documents).
# Neuronic 2026
#
# Uses each OS's actual mechanism for finding the folder rather than
# assuming a fixed path, so it's still correct if the user has relocated
# it (e.g. Windows "Known Folder Move" to OneDrive, custom XDG user dirs).

import os
import sys
import subprocess

_IS_WIN = sys.platform == 'win32'
_IS_MAC = sys.platform == 'darwin'


def get_documents_folder():
    """Return the current user's Documents folder."""
    if _IS_WIN:
        path = _windows_documents_folder()
        if path:
            return path
    elif not _IS_MAC:
        path = _linux_documents_folder()
        if path:
            return path
    # macOS has no redirection mechanism, so ~/Documents is always correct.
    # Also used as the fallback if the OS-specific lookup above failed.
    return os.path.expanduser('~/Documents')


def _windows_documents_folder():
    # Ask the shell directly (SHGetKnownFolderPath / FOLDERID_Documents)
    # instead of assuming "<home>\Documents" - the shell is the source of
    # truth if the folder has been moved or redirected.
    try:
        import ctypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        # FOLDERID_Documents = {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
        FOLDERID_Documents = GUID(
            0xFDD39AD0, 0x238F, 0x46AF,
            (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
        )

        path_ptr = ctypes.c_wchar_p()
        hresult = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(FOLDERID_Documents), 0, 0, ctypes.byref(path_ptr)
        )
        if hresult == 0 and path_ptr.value:
            path = path_ptr.value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except Exception:
        pass
    return None


def _linux_documents_folder():
    # xdg-user-dir respects the user's actual configured XDG dirs
    # (~/.config/user-dirs.dirs), including renamed/localized folders.
    try:
        result = subprocess.run(
            ['xdg-user-dir', 'DOCUMENTS'],
            capture_output=True, text=True, timeout=2,
        )
        path = result.stdout.strip()
        if path:
            return path
    except Exception:
        pass
    return None
