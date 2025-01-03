import os
import sys
import time
import threading
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QLineEdit, QCheckBox, QPlainTextEdit, QVBoxLayout, QMessageBox
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QObject
)

LOG_PATH = r"C:\Program Files (x86)\Steam\logs\content_log.txt"

KEYWORDS = ["finished update"]

class LogMonitorWorker(QObject):
    log_signal = Signal(str)
    found_signal = Signal()
    stopped_signal = Signal()

    def __init__(self, keywords, poll_interval=3, parent=None):
        super().__init__(parent)
        self.keywords = [kw.lower() for kw in keywords]
        self.poll_interval = poll_interval
        self._running = False

    def start_monitoring(self):
        if not os.path.exists(LOG_PATH):
            self.log_signal.emit(f"[ERROR] Log file not found: {LOG_PATH}")
            self.stopped_signal.emit()
            return

        self._running = True
        self.log_signal.emit("Starting log monitoring...")

        try:
            with open(LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, 2)
                while self._running:
                    line = f.readline()
                    if not line:
                        time.sleep(self.poll_interval)
                        continue

                    lower_line = line.lower()
                    for kw in self.keywords:
                        if kw in lower_line:
                            self.log_signal.emit(f"Found keyword: '{kw}' in line:\n{line.strip()}")
                            self.found_signal.emit()
                            self._running = False
                            break

                    if not self._running:
                        break

        except Exception as e:
            self.log_signal.emit(f"[ERROR] Exception in monitoring: {e}")

        self.stopped_signal.emit()

    def stop(self):
        self._running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UAC Steam Downloader Scheduler")
        self.setGeometry(300, 200, 650, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.title_label = QLabel("UAC Steam Downloader Monitor")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.r, self.g, self.b = 255, 0, 0
        self.color_step = 1

        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.animate_title_color)
        self.color_timer.start(2)

        self.app_id_edit = QLineEdit()
        self.app_id_edit.setPlaceholderText("Enter Steam AppID (e.g. 632810)")
        self.app_id_edit.setText("632810")
        layout.addWidget(self.app_id_edit)

        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("Enter time to start download (HH:MM) - 24h format")
        layout.addWidget(self.time_edit)

        schedule_btn = QPushButton("Schedule Download")
        schedule_btn.clicked.connect(self.schedule_download)
        layout.addWidget(schedule_btn)

        self.start_monitor_btn = QPushButton("Start Monitoring for Keywords")
        self.start_monitor_btn.clicked.connect(self.start_monitoring)
        layout.addWidget(self.start_monitor_btn)

        self.stop_monitor_btn = QPushButton("Stop Monitoring")
        self.stop_monitor_btn.clicked.connect(self.stop_monitoring)
        self.stop_monitor_btn.setEnabled(False)
        layout.addWidget(self.stop_monitor_btn)

        self.shutdown_checkbox = QCheckBox("Shutdown after download finishes?")
        layout.addWidget(self.shutdown_checkbox)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #2e2e2e; color: white;")
        layout.addWidget(self.log_area)

        self.monitor_thread = None
        self.monitor_worker = None

        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_scheduled_download)
        self.scheduled_time = None

    def animate_title_color(self):
        if self.r == 255 and self.g < 255 and self.b == 0:
            self.g += self.color_step
        elif self.g == 255 and self.r > 0 and self.b == 0:
            self.r -= self.color_step
        elif self.g == 255 and self.b < 255 and self.r == 0:
            self.b += self.color_step
        elif self.b == 255 and self.g > 0 and self.r == 0:
            self.g -= self.color_step
        elif self.b == 255 and self.r < 255 and self.g == 0:
            self.r += self.color_step
        elif self.r == 255 and self.b > 0 and self.g == 0:
            self.b -= self.color_step

        color = f"rgb({self.r}, {self.g}, {self.b})"
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")

    def schedule_download(self):
        time_str = self.time_edit.text().strip()
        if not time_str:
            QMessageBox.warning(self, "No Time", "Please enter time in HH:MM format.")
            return

        try:
            hour_min = time_str.split(":")
            if len(hour_min) != 2:
                raise ValueError("Invalid format")
            hh = int(hour_min[0])
            mm = int(hour_min[1])
            if not (0 <= hh < 24 and 0 <= mm < 60):
                raise ValueError("Out of range")

            self.scheduled_time = (hh, mm)
            self.schedule_timer.start(2000)
            self.log_area.appendPlainText(f"Download scheduled at {hh:02d}:{mm:02d} ...")
        except:
            QMessageBox.warning(self, "Format Error", "Please enter time in HH:MM format (24-hour).")

    def check_scheduled_download(self):
        if not self.scheduled_time:
            return

        now = datetime.now()
        current_h = now.hour
        current_m = now.minute

        if (current_h == self.scheduled_time[0] and
                current_m == self.scheduled_time[1]):
            self.schedule_timer.stop()
            self.start_download()
            self.log_area.appendPlainText("Scheduled time reached; started download.")
            self.scheduled_time = None

    def start_download(self):
        app_id = self.app_id_edit.text().strip()
        if not app_id:
            QMessageBox.warning(self, "No AppID", "Please provide a valid AppID.")
            return

        cmd = f'start steam://rungameid/{app_id}'        

        os.system(cmd)
        self.log_area.appendPlainText(f"Executing: {cmd}")

    def start_monitoring(self):
        self.start_monitor_btn.setEnabled(False)
        self.stop_monitor_btn.setEnabled(True)

        self.log_area.appendPlainText("Starting log monitoring in background...")

        self.monitor_worker = LogMonitorWorker(KEYWORDS, poll_interval=3)
        self.monitor_worker.log_signal.connect(self.on_log_message)
        self.monitor_worker.found_signal.connect(self.on_keyword_found)
        self.monitor_worker.stopped_signal.connect(self.on_monitor_stopped)

        self.monitor_thread = threading.Thread(target=self.monitor_worker.start_monitoring)
        self.monitor_thread.start()

    def stop_monitoring(self):
        if self.monitor_worker:
            self.monitor_worker.stop()
        self.log_area.appendPlainText("Requesting to stop monitoring...")

    def on_log_message(self, msg):
        self.log_area.appendPlainText(msg)

    def on_keyword_found(self):
        self.log_area.appendPlainText("Keyword found => download likely finished.")
        if self.shutdown_checkbox.isChecked():
            self.log_area.appendPlainText("Preparing to shutdown the PC...")
            os.system("shutdown /s /f /t 0")

    def on_monitor_stopped(self):
        self.log_area.appendPlainText("Monitoring stopped.")
        self.start_monitor_btn.setEnabled(True)
        self.stop_monitor_btn.setEnabled(False)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
