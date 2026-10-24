<p align="center"><img src="assets/logo.png" alt="Local Clipboard Translator logo" width="160"></p>

# Local Clipboard Translator

A tiny pixel character walks along your taskbar. Copy any text and it answers with a speech bubble containing the translation. Everything runs on your own machine: no cloud, no API keys, no subscription. The only time you go online is to download the model once.

Languages: Turkish, German and English. You pick any two of them and text copied in either language is translated into the other.

> Status: work in progress, MVP under construction.

## How it works

1. A global clipboard listener (`QClipboard.dataChanged`, no polling) notices new text.
2. A background worker asks a local LLM, served by [Ollama](https://ollama.com), which language the text is in.
3. If the text is in one of your two languages, the same model translates it into the other one and streams the result into the bubble. Anything else gets a short "not supported" note in that language.
4. The bubble fades out by itself, or closes when you click it. Long texts (over 200 characters) are translated piece by piece and scroll upwards like end credits while the rest is still being translated.

Copied text is capped at 3000 characters. Entries flagged by password managers are ignored.

## Requirements

- Windows 10 or 11
- [Ollama](https://ollama.com/download) installed and running
- A model. The default is `gemma2:9b` (`ollama pull gemma2:9b`, about 5.4 GB). It translated German to Turkish better than `qwen3:8b` in my tests. You can install any other Ollama model and pick it in the settings. With "Automatic" selected the app uses the best model it finds installed.

You do not have to prepare any of this by hand. On first launch the setup wizard checks for Ollama and a model and, after asking, downloads and installs whatever is missing. It can be reopened from the tray menu or the settings.

## Using it

- **When it translates** (settings): every copy, only when you copy the same text twice, or when you press a global hotkey after copying. The hotkey mode is handy if you copy a lot of code or file paths.
- **Fullscreen apps:** while a game, a fullscreen video or a presentation is in front, translating pauses. The character says goodbye in your Windows language (Turkish, German or English, otherwise English) and walks off screen. It walks back in when you leave fullscreen.
- **Pause:** "Pause translating" in the tray menu stops translating but the character keeps strolling.
- **History:** the tray menu keeps the last 20 translations. Click one to see it in the bubble again. The history only lives in memory and is gone when you quit.
- **Warm start:** the model is loaded in the background when the app starts, so the first translation is as fast as the rest.

## GPU or CPU

The settings let you choose where the model runs:

- **GPU**: fastest (1 to 3 seconds per translation on an RTX 5070 Laptop), but the model occupies graphics memory while loaded, which can hurt games.
- **CPU**: slower (5 to 15 seconds), leaves the graphics card alone.

The settings also show where the model is actually running, and how long it stays in memory after the last translation.

## Run from source

```
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\python -m lct
```

The app lives in the system tray. Click the tray icon to open the settings: language pair, character, size, bubble behaviour, model, start with Windows.

## Build the installer

```
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

This runs PyInstaller (`dist\LocalClipboardTranslator\`) and, if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, produces `dist\LocalClipboardTranslator-Setup.exe`. The installer needs no admin rights, can add the app to Windows startup and leaves nothing in the taskbar: after launch it sits in the tray.

## Project layout

```
src/lct/           the application
assets/characters/ one transparent sprite strip per character
assets/source/     the original sprite sheet
tools/             sprite slicer and a small translation test script
```

## Credits

Character sprites come from the free CC0 sheet `TL_Creatures` (public domain, no attribution required, credited here anyway).

## License

MIT, see [LICENSE](LICENSE).
