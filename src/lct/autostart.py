import sys
from pathlib import Path

APP_VALUE = "LocalClipboardTranslator"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command():
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    pythonw = exe.with_name("pythonw.exe")
    return f'"{pythonw if pythonw.exists() else exe}" -m lct'


def is_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_VALUE)
        return True
    except (ImportError, OSError):
        return False


def set_enabled(enabled):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_VALUE, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, APP_VALUE)
                except FileNotFoundError:
                    pass
    except (ImportError, OSError):
        pass
