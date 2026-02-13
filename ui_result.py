from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import json
from datetime import datetime

class ResultDialog(QDialog):
    def __init__(self, translations, parent=None):
        super().__init__(parent)
        self.translations = translations
        self._init_ui()
        self._display_results()
    
    def _init_ui(self):
        self.setWindowTitle("翻译结果")
        self.setMinimumSize(600, 400)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.result_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        copy_btn = QPushButton("复制全部")
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(self._on_copy)
        btn_layout.addWidget(copy_btn)
        
        export_btn = QPushButton("导出")
        export_btn.setFixedWidth(80)
        export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(export_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """)
        
        font = QFont("Microsoft YaHei", 11)
        self.result_text.setFont(font)
    
    def _display_results(self):
        if not self.translations:
            self.result_text.setText("暂无翻译结果")
            return
        
        lines = []
        lines.append(f"=== 翻译结果 ({len(self.translations)} 条) ===\n")
        
        for i, item in enumerate(self.translations, 1):
            original = item.get("original", "")
            translated = item.get("translated", "")
            lines.append(f"[{i}] 原文: {original}")
            lines.append(f"    译文: {translated}")
            lines.append("")
        
        self.result_text.setText("\n".join(lines))
    
    def _on_copy(self):
        text = self.result_text.toPlainText()
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def _on_export(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出翻译结果",
            f"translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;JSON文件 (*.json)"
        )
        
        if file_path:
            if file_path.endswith(".json"):
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.translations, f, ensure_ascii=False, indent=2)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.result_text.toPlainText())
