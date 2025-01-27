import ctypes
import time
import threading
import os
import sys
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import wmi

class DefenderCheck(QWidget):
    defender_disabled_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.load_chakra_petch_font()
        self.setWindowTitle("Raven Talon")
        self.setFixedSize(600, 200)
        self.setStyleSheet("background-color: black; color: white;")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        self.message_label = QLabel("Windows Defender is currently enabled, which causes Talon to not work properly.\n\nPlease disable Windows Defender. Talon will automatically proceed afterwards.")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("color: white; font-size: 18px; padding: 12px; line-height: 1.5;")
        self.message_label.setFont(QFont("Chakra Petch", 16))
        self.message_label.setWordWrap(True)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.message_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_defender_status)
        self.check_defender_status(immediate_check=True)
        self.setLayout(layout)

    def load_chakra_petch_font(self):
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            font_path = os.path.join(base_path, "ChakraPetch-Regular.ttf")

            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id == -1:
                print("Failed to load font.")
            else:
                print("Font loaded successfully.")
        except Exception as e:
            print(f"Error loading font: {e}")

    def check_defender_status(self, immediate_check=False):
        if immediate_check:
            if not self.is_defender_enabled():
                self.message_label.setText("Windows Defender has been disabled. Close this window to proceed.")
                print("Success: Defender disabled (initial check)")
                self.defender_disabled_signal.emit()
            else:
                self.message_label.setText("Windows Defender is enabled. Waiting 3 seconds before rechecking...")
                self.timer.start(3000)
                print("Defender is still enabled. Checking again in 3 seconds...")

        else:
            if not self.is_defender_enabled():
                self.message_label.setText("Windows Defender has been disabled. Closing this window...")
                self.timer.stop()
                print("Success: Defender disabled (after periodic check)")
                self.defender_disabled_signal.emit()
            else:
                print("Defender is still enabled. Checking again in 3 seconds...")

    def is_defender_enabled(self):
        try:
            w = wmi.WMI(namespace="root\\SecurityCenter2")
            for defender in w.query("SELECT * FROM AntiVirusProduct"):
                if defender.displayName == "Windows Defender":
                    # 0x1000 (Bit 12) indicates rt protection is enabled
                    if defender.productState & 0x1000:
                        return True
                    else:
                        return False
            return False
        except Exception as e:
            print(f"Error checking Defender status: {e}")
            return False  # if there's an error, assume Defender is disabled