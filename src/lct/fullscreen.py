import ctypes

# Values of QUERY_USER_NOTIFICATION_STATE that mean "do not disturb": a fullscreen app is
# in front (a game, a fullscreen video), a Direct3D fullscreen app, or a presentation.
_BUSY, _D3D_FULL_SCREEN, _PRESENTATION = 2, 3, 4


def is_fullscreen_busy():
    """True while a fullscreen game, video or presentation is in front. Windows tracks this itself."""
    state = ctypes.c_int()
    try:
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
            return False
    except (AttributeError, OSError):
        return False
    return state.value in (_BUSY, _D3D_FULL_SCREEN, _PRESENTATION)
