# Third-party notices

Local Clipboard Translator itself is released under the MIT License (see `LICENSE`).
It makes use of the third-party components listed below. Each is the property of its
respective authors and is governed by its own license.

## Bundled in the installer

### Qt for Python (PySide6) and Qt 6
- Used as the GUI framework; the Qt libraries are distributed inside the Windows installer.
- License: GNU Lesser General Public License v3 (LGPLv3).
- https://doc.qt.io/qtforpython/
- Qt licensing: https://www.qt.io/licensing

### PyInstaller
- Used to package the application into a Windows executable. Its bootloader is linked into the distributed executable.
- License: GNU General Public License v2 or later, with a bootloader exception that permits packaging and distributing proprietary applications.
- https://pyinstaller.org/en/stable/license.html

## Build and installer tooling (not distributed with the app)

### Inno Setup
- Used only to build the installer. Inno Setup itself is not part of the installed application.
- https://jrsoftware.org/isinfo.php

## Downloaded separately by the user (not bundled)

### Ollama
- The local model runtime. The application connects to a local Ollama instance; it does not bundle Ollama. Ollama is installed by the user (optionally through the in-app setup wizard, which downloads it from ollama.com).
- https://ollama.com
- https://github.com/ollama/ollama/blob/main/LICENSE

### Gemma 2 (default model)
- The default language model, downloaded through Ollama. It is not bundled with the application.
- Governed by the Gemma Terms of Use: https://ai.google.dev/gemma/terms

## Assets

### Character sprites: "Various Creatures"
- Author: GrafxKid
- Source: https://opengameart.org/content/various-creatures
- License: Creative Commons CC0 1.0 (public domain dedication). Attribution is not legally required; the author is credited here as requested ("Credit me as GrafxKid").
