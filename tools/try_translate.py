"""Run sample texts through the translation pipeline and compare models, without any GUI.

    python tools/try_translate.py qwen3:8b gemma2:9b

Each model is unloaded first and warmed up, so the times are for a warm model. Needs Ollama running.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QCoreApplication  # noqa: E402

from lct.strings import Translator  # noqa: E402
from lct.translator import TranslationJob, running_models, unload_all  # noqa: E402

SAMPLES = [
    ("de", "Ich habe leider keine Zeit, aber wir können morgen telefonieren."),
    ("de", "Das ist nicht mein Bier."),
    ("de", "Die Kündigungsfrist beträgt drei Monate zum Quartalsende, sofern nichts anderes vereinbart wurde."),
    ("de", "Bitte starten Sie den Router neu und warten Sie, bis alle Lämpchen dauerhaft leuchten."),
    ("de", "Der Server antwortet nicht mehr. Haben Sie die Firewall-Regeln kürzlich geändert?"),
    ("de", "Haus"),
    ("tr", "Yarın toplantıya geç kalacağım, lütfen beni bekleme."),
    ("tr", "Gözümün nuru, bu iş başımıza dert olacak gibi görünüyor."),
    ("tr", "Sözleşmenin feshi için en az otuz gün önceden yazılı bildirimde bulunulması gerekmektedir."),
    ("tr", "Bağlantı zaman aşımına uğradı, lütfen ağ ayarlarını kontrol edip tekrar deneyin."),
    ("tr", "güzel"),
    ("de", "Die Bundesregierung hat am Mittwoch ein neues Gesetz beschlossen. Es soll im nächsten Jahr in Kraft "
           "treten. Kritiker bemängeln, dass die Regelung zu viele Ausnahmen enthält. " * 2),
]


def translate(model, text):
    out = []
    job = TranslationJob(text, "tr", "de", model, Translator("en"), "gpu", 10)
    job.text_delta.connect(out.append)
    job.notice.connect(lambda m: out.append("NOTICE: " + m))
    start = time.time()
    job.run()  # in this thread, so no event loop is needed
    return time.time() - start, "".join(out).strip()


def main():
    app = QCoreApplication([])  # noqa: F841
    models = sys.argv[1:] or [""]
    results = {}
    for model in models:
        unload_all()
        translate(model, "Hallo")  # warm-up
        print(f"== {model or 'auto'}  loaded: {running_models()}")
        results[model] = [translate(model, text) for _, text in SAMPLES]
    for i, (lang, text) in enumerate(SAMPLES):
        print(f"\n[{lang}] {text[:90]}")
        for model in models:
            secs, out = results[model][i]
            print(f"  {model or 'auto':>10} {secs:5.1f}s | {out[:160]}")


if __name__ == "__main__":
    main()
