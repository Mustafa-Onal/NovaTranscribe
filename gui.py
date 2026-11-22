import sys
import traceback
from pathlib import Path
from PySide6.QtCore import QFile, QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from ollama_client import generate_reply
from transcriber import transcribe_audio


class PipelineWorker(QThread):
    status_changed = Signal(str)
    finished_text = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, audio_path: str, language: str = "tr", parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.language = language

    def run(self):
        try:
            self.status_changed.emit(f"Ses metne çevriliyor ({self.language})...")
            transcript = transcribe_audio(self.audio_path, language=self.language)

            self.status_changed.emit("Ollama yanıt üretiyor...")
            reply = generate_reply(transcript, language=self.language)

            formatted = f"--- TRANSKRİPT ---\n{transcript}\n\n--- YANIT ---\n{reply}"
            self.finished_text.emit(formatted)
            self.status_changed.emit("Tamamlandı.")
        except Exception as exc:
            traceback.print_exc()
            self.error_occurred.emit(f"{type(exc).__name__}: {exc}")


class NovaTranscribeApp:
    def __init__(self, ui_path: Path):
        loader = QUiLoader()
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"UI dosyası açılamadı: {ui_path}")

        self.window: QWidget = loader.load(ui_file)
        ui_file.close()

        if self.window is None:
            raise RuntimeError("QUiLoader pencereyi oluşturamadı.")

        self.file_input = self.window.findChild(QLineEdit, "file_input")
        self.browse_btn = self.window.findChild(QPushButton, "browse_btn")
        self.combo_box = self.window.findChild(QComboBox, "comboBox")
        self.run_btn = self.window.findChild(QPushButton, "run_btn")
        self.play_btn = self.window.findChild(QPushButton, "play_btn")
        self.output_box = self.window.findChild(QTextEdit, "output_box")
        self.status_label = self.window.findChild(QLabel, "status_label")

        self.selected_audio_path = ""

        if self.combo_box and self.combo_box.count() == 0:
            self.combo_box.addItems(["tr", "en"])

        self.worker: PipelineWorker | None = None
        self._connect_signals()

    def _connect_signals(self):
        if self.browse_btn:
            self.browse_btn.clicked.connect(self._select_file)
        if self.run_btn:
            self.run_btn.clicked.connect(self._start_pipeline)
        if self.play_btn:
            self.play_btn.clicked.connect(self._speak_output)

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Ses Dosyası Seç",
            "",
            "Ses Dosyaları (*.wav *.mp3 *.m4a *.ogg *.flac);;Tüm Dosyalar (*)",
        )
        if path:
            self.selected_audio_path = path
            if self.file_input:
                self.file_input.setText(path)
            self._set_status(f"Seçildi: {Path(path).name}")

    def _start_pipeline(self):
        typed = self.file_input.text().strip() if self.file_input else ""
        audio_path = typed or self.selected_audio_path

        if not audio_path:
            self._set_status("Önce bir ses dosyası seçin.")
            return

        language = self.combo_box.currentText().strip() if self.combo_box else "tr"

        if self.run_btn:
            self.run_btn.setEnabled(False)

        self.worker = PipelineWorker(audio_path, language)
        self.worker.status_changed.connect(self._set_status)
        self.worker.finished_text.connect(self._on_finished)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        if self.run_btn:
            self.run_btn.setEnabled(True)

    def _on_finished(self, text: str):
        if self.output_box:
            self.output_box.setPlainText(text)

    def _on_error(self, message: str):
        self._set_status(f"Hata: {message}")
        if self.run_btn:
            self.run_btn.setEnabled(True)

    def _speak_output(self):
        text = self.output_box.toPlainText().strip() if self.output_box else ""
        if not text:
            self._set_status("Seslendirilecek metin yok.")
            return
        self._set_status("Seslendirme hazır (speaker.py bağlanacak).")

    def _set_status(self, message: str):
        if self.status_label:
            self.status_label.setText(message)

    def show(self):
        self.window.show()


def main():
    app = QApplication(sys.argv)
    ui_file = Path(__file__).resolve().parent / "nova_ui.ui"
    controller = NovaTranscribeApp(ui_file)
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()