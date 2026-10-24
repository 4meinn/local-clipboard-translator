"""Run a handful of sample texts through the translation pipeline without any GUI.

    python tools/try_translate.py [model]

Useful for comparing models: pass e.g. qwen3:8b or gemma2:9b. Needs Ollama running.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QCoreApplication  # noqa: E402

from lct.strings import Translator  # noqa: E402
from lct.translator import TranslationJob  # noqa: E402

SAMPLES = [
    "Ich habe leider keine Zeit, aber wir können morgen telefonieren.",
    "Yarın toplantıya geç kalacağım, lütfen beni bekleme.",
    "Haus",
    "Das ist nicht mein Bier.",
    "Hola, ¿cómo estás? Espero que todo vaya bien.",
    "The meeting was moved to Friday afternoon.",
    "Die Bundesregierung hat am Mittwoch ein neues Gesetz beschlossen. "
    "Es soll im nächsten Jahr in Kraft treten. " * 3,
]


def main():
    app = QCoreApplication([])  # noqa: F841
    model = sys.argv[1] if len(sys.argv) > 1 else ""
    tr = Translator("en")
    for text in SAMPLES:
        out = []
        job = TranslationJob(text, "tr", "de", model, tr)
        job.started_translation.connect(lambda long: out.append(f"[long={long}] "))
        job.text_delta.connect(out.append)
        job.notice.connect(lambda m: out.append("NOTICE: " + m))
        start = time.time()
        job.run()  # in this thread, so no event loop is needed
        print(f"{time.time() - start:5.1f}s | {text[:50]!r}\n        -> {''.join(out)}\n")


if __name__ == "__main__":
    main()
