"""A global hotkey through the Windows API. Qt has no cross-application shortcut of its own."""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter

WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000
HOTKEY_ID = 0xB001

# Offered in the settings. Combinations that common apps already use (Ctrl+Shift+T and
# friends) are left out on purpose, a global hotkey would take them away from those apps.
HOTKEYS = {
    "Ctrl+Alt+T": (MOD_CONTROL | MOD_ALT, 0x54),
    "Ctrl+Alt+Y": (MOD_CONTROL | MOD_ALT, 0x59),
    "Ctrl+Alt+Space": (MOD_CONTROL | MOD_ALT, 0x20),
    "Ctrl+Shift+Space": (MOD_CONTROL | MOD_SHIFT, 0x20),
}


class HotkeyListener(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.registered = False

    def register(self, name):
        """Returns False when another program already owns that combination."""
        self.unregister()
        modifiers, key = HOTKEYS.get(name, HOTKEYS["Ctrl+Alt+T"])
        self.registered = bool(ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, modifiers | MOD_NOREPEAT, key))
        return self.registered

    def unregister(self):
        if self.registered:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.callback()
        return False, 0
