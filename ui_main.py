from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTextEdit, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

class TranslationBar(QWidget):
    new_translation = Signal(str, str)
    start_clicked = Signal()
    stop_clicked = Signal()
    topmost_changed = Signal(bool)
    settings_clicked = Signal()
    result_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.translations = []
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(700, 100)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)
        
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedWidth(60)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedWidth(60)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        control_layout.addWidget(self.stop_btn)
        
        self.topmost_btn = QPushButton("置顶")
        self.topmost_btn.setFixedWidth(50)
        self.topmost_btn.setCheckable(True)
        self.topmost_btn.clicked.connect(self._on_topmost)
        control_layout.addWidget(self.topmost_btn)
        
        self.settings_btn = QPushButton("设置")
        self.settings_btn.setFixedWidth(50)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        control_layout.addWidget(self.settings_btn)
        
        self.result_btn = QPushButton("结果")
        self.result_btn.setFixedWidth(50)
        self.result_btn.clicked.connect(self.result_clicked.emit)
        control_layout.addWidget(self.result_btn)
        
        control_layout.addStretch()
        
        self.status_label = QLabel("就绪")
        self.status_label.setFixedWidth(80)
        control_layout.addWidget(self.status_label)
        
        main_layout.addLayout(control_layout)
        
        text_layout = QHBoxLayout()
        
        self.original_label = QLabel("原文: 等待音频...")
        self.original_label.setWordWrap(True)
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_layout.addWidget(self.original_label, 1)
        
        self.translated_label = QLabel("译文: 等待翻译...")
        self.translated_label.setWordWrap(True)
        self.translated_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_layout.addWidget(self.translated_label, 1)
        
        main_layout.addLayout(text_layout)
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QPushButton:checked {
                background-color: #0078d4;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
                padding: 2px;
            }
        """)
        
        font = QFont("Microsoft YaHei", 11)
        self.original_label.setFont(font)
        self.translated_label.setFont(font)
    
    def _on_topmost(self, checked):
        if checked:
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.topmost_btn.setText("取消置顶")
        else:
            self.setWindowFlags(Qt.WindowType.Window)
            self.topmost_btn.setText("置顶")
        self.show()
        self.topmost_changed.emit(checked)
    
    def update_original(self, text):
        self.original_label.setText(f"原文: {text}")
    
    def update_translated(self, original, translated):
        self.translated_label.setText(f"译文: {translated}")
        self.translations.append({
            "original": original,
            "translated": translated
        })
    
    def update_status(self, status):
        self.status_label.setText(status)
    
    def set_running(self, running):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        if running:
            self.status_label.setText("运行中...")
        else:
            self.status_label.setText("已停止")
    
    def set_original_text(self, text):
        self.original_label.setText(f"原文: {text}")
    
    def set_translated_text(self, original, translated):
        self.translated_label.setText(f"译文: {translated}")
        self.translations.append({
            "original": original,
            "translated": translated
        })
    
    def set_status(self, status):
        self.status_label.setText(status)
    
    def get_translations(self):
        return self.translations.copy()
    
    def clear_translations(self):
        self.translations = []
        self.original_label.setText("原文: 等待音频...")
        self.translated_label.setText("译文: 等待翻译...")
    
    def set_topmost(self, topmost):
        self.topmost_btn.setChecked(topmost)
        self._on_topmost(topmost)
