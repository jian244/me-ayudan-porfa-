from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar, QComboBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import sys
import yt_dlp
import os
import subprocess
import openai

# Configura correctamente tu clave de API
openai.api_key = "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"

class DownloadThread(QThread):
    # Señales para actualizar la barra de progreso y mostrar mensaje de finalización
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, url, path, platform, file_format):
        super().__init__()
        self.url = url
        self.path = path
        self.platform = platform
        self.file_format = file_format  # Guardamos el formato de archivo seleccionado

    def run(self):
        """Maneja la descarga según la plataforma seleccionada (YouTube o Spotify)."""
        try:
            # Extraemos el nombre del archivo basado en el título del video (para youtube)
            if self.platform == 'youtube':
                options = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(self.path, "%(title)s.%(ext)s"),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': self.file_format,  # Usamos el formato elegido por el usuario
                        'preferredquality': '320k'
                    }],
                    'progress_hooks': [self.yt_hook],
                    'noplaylist': True
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    info_dict = ydl.extract_info(self.url, download=False)
                    filename = ydl.prepare_filename(info_dict)
                    filename = filename.replace(info_dict['ext'], self.file_format)  # Usamos el formato de salida

                    if os.path.exists(filename):
                        self.finished_signal.emit(f"El archivo '{filename}' ya existe. No se descargará nuevamente.")
                        return
                    
                    ydl.download([self.url])

            elif self.platform == 'spotify':
                # Usamos el comando spotdl para descargar música de Spotify
                command = ["spotdl", "download", self.url, "--output", self.path]
                result = subprocess.run(command, capture_output=True, text=True)

                # Revisamos si el archivo ya existe en el directorio de destino
                filename = os.path.join(self.path, self.url.split('/')[-1] + ".mp3")  # Aquí podrías personalizar el nombre
                if os.path.exists(filename):
                    self.finished_signal.emit(f"El archivo '{filename}' ya existe. No se descargará nuevamente.")
                    return

                if result.returncode != 0:
                    raise Exception(result.stderr)

            # Emitimos mensaje cuando se complete la descarga
            self.finished_signal.emit("Descarga completada")
        except Exception as e:
            self.finished_signal.emit(f"Error: {str(e)}")

    def yt_hook(self, d):
        """Actualiza la barra de progreso según el estado de la descarga de YouTube."""
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 1)
            progress = int((downloaded / total) * 100)
            self.progress_signal.emit(progress)


class DownloaderApp(QWidget):
    def __init__(self):
        """Inicializa la interfaz gráfica de usuario."""
        super().__init__()
        self.setWindowTitle("Descargador de Música y ChatGPT")
        self.setFixedSize(600, 450)
        self.initUI()

    def initUI(self):
        """Configura los elementos de la interfaz gráfica."""
        layout = QVBoxLayout()
        
        # Etiqueta de bienvenida
        title_label = QLabel("Bienvenido a Downloader & ChatGPT", self)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Campo de entrada para el enlace o consulta
        self.input_entry = QTextEdit(self)
        self.input_entry.setPlaceholderText("Escribe tu consulta o ingresa un enlace para descargar...")
        layout.addWidget(self.input_entry)

        # Botón para enviar o iniciar la descarga
        action_button = QPushButton("Enviar/Descargar", self)
        action_button.clicked.connect(self.procesar_input)
        layout.addWidget(action_button)

        # Botón para seleccionar la ruta de descarga
        path_button = QPushButton("Seleccionar Ruta", self)
        path_button.clicked.connect(self.seleccionar_ruta)
        layout.addWidget(path_button)

        # Etiqueta que muestra la ruta seleccionada
        self.path_entry = QLabel("Ruta: No seleccionada", self)
        layout.addWidget(self.path_entry)

        # Selector de tipo de archivo de salida
        self.file_format_combo = QComboBox(self)
        self.file_format_combo.addItems(["mp3", "flac", "wav"])  # Agregamos opciones de formato
        layout.addWidget(self.file_format_combo)

        # Barra de progreso para la descarga
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def detectar_plataforma(self, texto):
        """Detecta la plataforma de donde proviene el enlace (YouTube o Spotify)."""
        if "youtube.com" in texto or "youtu.be" in texto:
            return 'youtube'
        elif "spotify.com" in texto:
            return 'spotify'
        return None

    def procesar_input(self):
        """Procesa las entradas de texto, manejando cada línea como una consulta o enlace independiente."""
        texto = self.input_entry.toPlainText().strip()
        if not texto:
            self.show_message("Advertencia", "Por favor, ingresa uno o más mensajes o enlaces.", error=True)
            return

        # Dividimos el texto por líneas
        lineas = texto.split("\n")
        
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue  # Si la línea está vacía, la saltamos

            plataforma = self.detectar_plataforma(linea)
            if plataforma:
                self.iniciar_descarga(linea, plataforma)  # Iniciar la descarga para esta línea
            else:
                self.usar_chatgpt(linea)  # Enviar la consulta a ChatGPT para esta línea

    def iniciar_descarga(self, url, plataforma):
        """Inicia el proceso de descarga según la plataforma seleccionada."""
        path = self.path_entry.text().replace("Ruta: ", "").strip()
        if path == "No seleccionada":
            self.show_message("Advertencia", "Selecciona una ruta de descarga.", error=True)
            return

        # Obtenemos el formato de archivo seleccionado
        file_format = self.file_format_combo.currentText()

        # Iniciamos el hilo de descarga con los parámetros correspondientes
        self.download_thread = DownloadThread(url, path, plataforma, file_format)
        self.download_thread.progress_signal.connect(self.progress_bar.setValue)
        self.download_thread.finished_signal.connect(self.show_download_message)
        self.download_thread.start()

    def usar_chatgpt(self, prompt):
        """Envía una consulta a ChatGPT y muestra la respuesta en un cuadro de mensaje."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Asegúrate de usar el modelo correcto
                messages=[{"role": "user", "content": prompt}]  # Consulta del usuario
            )
            message = response['choices'][0]['message']['content']  # Accede correctamente a la respuesta
            self.show_message("ChatGPT", message)
    
        except Exception as e:
            self.show_message("Error", f"Error al comunicarse con ChatGPT: {str(e)}", error=True)

    def seleccionar_ruta(self):
        """Permite al usuario seleccionar la ruta de descarga en el sistema de archivos."""
        ruta = QFileDialog.getExistingDirectory(self, "Selecciona una ruta")
        if ruta:
            self.path_entry.setText(f"Ruta: {ruta}")

    def show_download_message(self, message):
        """Muestra el mensaje de estado de la descarga y restablece la barra de progreso."""
        self.show_message("Estado de Descarga", message)
        self.progress_bar.setValue(0)

    def show_message(self, title, message, error=False):
        """Muestra un cuadro de mensaje con la información o el error correspondiente."""
        if error:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec())


