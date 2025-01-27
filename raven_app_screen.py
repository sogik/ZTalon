from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy, QGraphicsView
)
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPixmap
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
import os
import sys

class AnimatedButton(QPushButton):
    def __init__(self, text, color, hover_color=None):
        super().__init__(text)
        self.default_color = color
        self.hover_color = hover_color if hover_color else color
        self.setStyleSheet(f"background-color: {self.default_color.name()}; color: white; border: none;")
        self.setFont(QFont("Chakra Petch", 14, QFont.Bold))
        self.setFixedSize(240, 40)
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(80)
        self.shadow_effect.setColor(self.default_color.darker(200))
        self.shadow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow_effect)
        self.animation = QPropertyAnimation(self.shadow_effect, b"blurRadius")
        self.animation.setDuration(800)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

    def enterEvent(self, event):
        self.animation.stop()
        self.animation.setStartValue(self.shadow_effect.blurRadius())
        self.animation.setEndValue(200)
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.stop()
        self.animation.setStartValue(self.shadow_effect.blurRadius())
        self.animation.setEndValue(80)
        self.animation.start()
        super().leaveEvent(event)

class RavenAppScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optional: Install Raven Software")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")
        self.load_chakra_petch_font()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("Optional: Install Raven Software")
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_label.setFont(QFont("Chakra Petch", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        body_label = QLabel(
            "Simple, powerful, and privacy focused. Lightweight software designed to just work, with minimal distractions and hassle."
        )
        body_label.setStyleSheet("color: white; font-weight: normal;")
        body_label.setFont(QFont("Chakra Petch", 16))
        body_label.setWordWrap(True)
        body_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(body_label)
        image_label = QLabel(self)
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(base_path, "additional_software_offer.png")
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaledToWidth(int(self.width() * 0.6), Qt.SmoothTransformation)
        image_label.setPixmap(scaled_pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignCenter)
        yes_button = AnimatedButton("Yes, Install", QColor(34, 139, 34), QColor(50, 205, 50))
        no_button = AnimatedButton("No, Thanks", QColor(139, 0, 0), QColor(205, 92, 92))
        yes_button.clicked.connect(lambda: self.select_option(True))
        no_button.clicked.connect(lambda: self.select_option(False))
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.selected_option = None

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

    def select_option(self, option):
        self.selected_option = option
        print(f"Selected option: {'Yes' if option else 'No'}")
        self.close()
        return self.selected_option
