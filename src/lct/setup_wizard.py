"""Guided setup: get Ollama installed and running, and a translation model downloaded."""
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from lct import translator

log = logging.getLogger(__name__)

OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
DEFAULT_MODEL = translator.PREFERRED_MODELS[0]
MODEL_GB = {"qwen3:8b": 5.2}  # shown in the download prompt
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ollama_paths():
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    exe = shutil.which("ollama") or str(local / "Programs" / "Ollama" / "ollama.exe")
    app = local / "Programs" / "Ollama" / "ollama app.exe"
    return (Path(exe) if Path(exe).exists() else None), (app if app.exists() else None)


def current_state():
    """('missing' | 'stopped' | 'no_model' | 'ready', installed model names)."""
    exe, _ = ollama_paths()
    try:
        models = translator.list_models()
    except translator.OllamaUnavailable:
        return ("stopped" if exe else "missing"), []
    return ("ready" if models else "no_model"), models


def start_ollama():
    exe, app = ollama_paths()
    if app:
        subprocess.Popen([str(app)], creationflags=NO_WINDOW)
    elif exe:
        subprocess.Popen([str(exe), "serve"], creationflags=NO_WINDOW | subprocess.DETACHED_PROCESS)


class Worker(QThread):
    progress = Signal(int, str)  # percent (-1 when unknown), detail
    done = Signal(bool, str)  # ok, error text

    def run(self):
        try:
            self.work()
            self.done.emit(True, "")
        except Exception as err:  # reported to the user in the dialog
            log.exception("setup step failed")
            self.done.emit(False, str(err))


class StateCheck(Worker):
    found = Signal(str, int)  # state, size of the Ollama download in MB (0 if not needed)

    def work(self):
        state, _ = current_state()
        mb = 0
        if state == "missing":
            try:
                req = urllib.request.Request(OLLAMA_URL, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    mb = int(resp.headers.get("Content-Length", 0)) // (1024 * 1024)
            except OSError:
                pass
        self.found.emit(state, mb)


class InstallOllama(Worker):
    def work(self):
        target = Path(tempfile.mkdtemp(prefix="lct-ollama-")) / "OllamaSetup.exe"
        with urllib.request.urlopen(OLLAMA_URL, timeout=30) as resp, open(target, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            got = 0
            while chunk := resp.read(256 * 1024):
                out.write(chunk)
                got += len(chunk)
                self.progress.emit(int(got * 100 / total) if total else -1, "download")
        self.progress.emit(-1, "install")
        subprocess.run([str(target), "/SP-", "/SILENT", "/NORESTART", "/SUPPRESSMSGBOXES"], check=True)
        self.progress.emit(-1, "start")
        if current_state()[0] == "missing":
            raise RuntimeError("Ollama was installed but could not be found.")
        wait_until_running()
        shutil.rmtree(target.parent, ignore_errors=True)


def wait_until_running(seconds=40):
    deadline = time.time() + seconds
    started = False
    while time.time() < deadline:
        try:
            translator.list_models()
            return
        except translator.OllamaUnavailable:
            if not started:
                start_ollama()
                started = True
            time.sleep(1)
    raise RuntimeError("Ollama did not start in time.")


class StartOllama(Worker):
    def work(self):
        wait_until_running()


class PullModel(Worker):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def work(self):
        layers = {}
        with translator._open("/api/pull", {"model": self.model, "stream": True}, timeout=60) as resp:
            for line in resp:
                if not line.strip():
                    continue
                msg = json.loads(line)
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                if msg.get("total"):
                    layers[msg.get("digest", msg.get("status"))] = (msg["total"], msg.get("completed", 0))
                total = sum(t for t, _ in layers.values())
                pct = int(sum(c for _, c in layers.values()) * 100 / total) if total else -1
                self.progress.emit(pct, msg.get("status", ""))


class SetupWizard(QDialog):
    """Checks what is missing, asks before every download, then does it with a progress bar."""

    finished_ok = Signal()

    def __init__(self, tr, model=DEFAULT_MODEL):
        super().__init__()
        self.tr, self.model = tr, model
        self.worker = None
        self._workers = set()
        self._after = None
        self.setWindowTitle(tr("wiz_title"))
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        self.bar = QProgressBar()
        self.bar.setTextVisible(True)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.primary = QPushButton()
        self.later = QPushButton(tr("wiz_btn_later"))
        buttons.addWidget(self.primary)
        buttons.addWidget(self.later)
        layout.addWidget(self.message)
        layout.addWidget(self.bar)
        layout.addLayout(buttons)
        self.later.clicked.connect(self.close)
        self.primary.clicked.connect(self._primary_clicked)
        self._action = None

    # --- flow ------------------------------------------------------------------------

    def begin(self):
        self._busy(self.tr("wiz_checking"))
        self._run(StateCheck())
        self.worker.found.connect(self._on_state)
        self.show()
        self.raise_()
        self.activateWindow()

    def _run(self, worker):
        self.worker = worker
        self._workers.add(worker)  # keeps the thread object alive until it reports done
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_done)
        worker.start()

    def _busy(self, text, percent=-1):
        self.message.setText(text)
        self.primary.hide()
        self.later.setText(self.tr("wiz_btn_later"))
        self.bar.show()
        self.bar.setRange(0, 100 if percent >= 0 else 0)
        self.bar.setValue(max(percent, 0))

    def _ask(self, text, button, action):
        self.message.setText(text)
        self.bar.hide()
        self.primary.setText(button)
        self.primary.show()
        self.later.setText(self.tr("wiz_btn_later"))
        self._action = action

    def _on_state(self, state, mb):
        if state == "missing":
            size = self.tr("size_mb", n=mb) if mb else ""
            self._ask(self.tr("wiz_need_ollama", size=size), self.tr("wiz_btn_install"), self._install)
        elif state == "stopped":
            self._start()
        elif state == "no_model":
            gb = MODEL_GB.get(self.model)
            size = self.tr("size_gb", n=gb) if gb else ""
            self._ask(self.tr("wiz_need_model", model=self.model, size=size),
                      self.tr("wiz_btn_model"), self._pull)
        else:
            self._finish()

    def _primary_clicked(self):
        if self._action:
            self._action()

    def _install(self):
        self._busy(self.tr("wiz_downloading"), 0)
        self._run(InstallOllama())
        self._after = self.begin_recheck

    def _start(self):
        self._busy(self.tr("wiz_starting"))
        self._run(StartOllama())
        self._after = self.begin_recheck

    def _pull(self):
        self._busy(self.tr("wiz_pulling", model=self.model), 0)
        self._run(PullModel(self.model))
        self._after = self.begin_recheck

    def begin_recheck(self):
        self._busy(self.tr("wiz_checking"))
        self._run(StateCheck())
        self.worker.found.connect(self._on_state)

    def _on_progress(self, percent, detail):
        if detail == "install":
            self.message.setText(self.tr("wiz_installing"))
        elif detail == "start":
            self.message.setText(self.tr("wiz_starting"))
        if percent >= 0:
            self.bar.setRange(0, 100)
            self.bar.setValue(percent)
        else:
            self.bar.setRange(0, 0)

    def _on_done(self, ok, error):
        worker = self.sender()
        worker.wait()
        self._workers.discard(worker)
        if worker is not self.worker:
            return
        if ok:
            if not isinstance(worker, StateCheck):  # a StateCheck reports through `found`
                self._after()
        else:
            self._ask(self.tr("wiz_error", err=error), self.tr("wiz_btn_retry"), self.begin_recheck)

    def _finish(self):
        self.message.setText(self.tr("wiz_done"))
        self.bar.hide()
        self.primary.hide()
        self.later.setText(self.tr("wiz_btn_close"))
        self.finished_ok.emit()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning() and not isinstance(self.worker, StateCheck):
            event.ignore()  # do not abandon a download or install halfway
            self.hide()
            return
        super().closeEvent(event)
