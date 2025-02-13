from tkinter import scrolledtext
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import sys
import yt_dlp
import os
import subprocess
import openai

# Configura correctamente tu clave de API
client = openai.OpenAI(api_key=" MI CLAVE API")

class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, url, path, platform):
        super().__init__()
        self.url = url
        self.path = path
        self.platform = platform

    def run(self):
        try:
            if self.platform == 'youtube':
                options = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(self.path, "%(title)s.%(ext)s"),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320k'
                    }],
                    'progress_hooks': [self.yt_hook],
                    'noplaylist': True
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([self.url])

            elif self.platform == 'spotify':
                command = ["spotdl", "download", self.url, "--output", self.path]
                result = subprocess.run(command, capture_output=True, text=True)

                if result.returncode != 0:
                    raise Exception(result.stderr)

            self.finished_signal.emit("Descarga completada")
        except Exception as e:
            self.finished_signal.emit(f"Error: {str(e)}")

    def yt_hook(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 1)
            progress = int((downloaded / total) * 100)
            self.progress_signal.emit(progress)

class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Descargador de Música y ChatGPT")
        self.setFixedSize(600, 450)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        title_label = QLabel("Bienvenido a Downloader & ChatGPT", self)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.input_entry = QTextEdit(self)
        self.input_entry.setPlaceholderText("Escribe tu consulta o ingresa un enlace para descargar...")
        layout.addWidget(self.input_entry)

        action_button = QPushButton("Enviar/Descargar", self)
        action_button.clicked.connect(self.procesar_input)
        layout.addWidget(action_button)

        path_button = QPushButton("Seleccionar Ruta", self)
        path_button.clicked.connect(self.seleccionar_ruta)
        layout.addWidget(path_button)

        self.path_entry = QLabel("Ruta: No seleccionada", self)
        layout.addWidget(self.path_entry)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def detectar_plataforma(self, texto):
        if "youtube.com" in texto or "youtu.be" in texto:
            return 'youtube'
        elif "spotify.com" in texto:
            return 'spotify'
        return None

    def procesar_input(self):
        texto = self.input_entry.toPlainText().strip()
        if not texto:
            self.show_message("Advertencia", "Por favor, ingresa un mensaje o enlace.", error=True)
            return

        plataforma = self.detectar_plataforma(texto)
        if plataforma:
            self.iniciar_descarga(texto, plataforma)
        else:
            self.usar_chatgpt(texto)

    def iniciar_descarga(self, url, plataforma):
        path = self.path_entry.text().replace("Ruta: ", "").strip()
        if path == "No seleccionada":
            self.show_message("Advertencia", "Selecciona una ruta de descarga.", error=True)
            return

        self.download_thread = DownloadThread(url, path, plataforma)
        self.download_thread.progress_signal.connect(self.progress_bar.setValue)
        self.download_thread.finished_signal.connect(self.show_download_message)
        self.download_thread.start()

    def usar_chatgpt(self, prompt):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            self.show_message("ChatGPT", response.choices[0].message.content)
        except Exception as e:
            self.show_message("Error", f"Error al comunicarse con ChatGPT: {str(e)}", error=True)

    def seleccionar_ruta(self):
        ruta = QFileDialog.getExistingDirectory(self, "Selecciona una ruta")
        if ruta:
            self.path_entry.setText(f"Ruta: {ruta}")

    def show_download_message(self, message):
        self.show_message("Estado de Descarga", message)
        self.progress_bar.setValue(0)

    def show_message(self, title, message, error=False):
        if error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec())

