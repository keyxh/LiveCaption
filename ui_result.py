from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QFileDialog, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import json
from datetime import datetime

class OrganizeThread(QThread):
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, translator, translations):
        super().__init__()
        self.translator = translator
        self.translations = translations
    
    def run(self):
        result, error = self.translator.organize_results(self.translations)
        if error:
            self.error.emit(error)
        else:
            self.finished.emit(result)

class ResultDialog(QDialog):
    def __init__(self, translations, translator=None, parent=None):
        super().__init__(parent)
        self.translations = translations
        self.translator = translator
        self.organized_text = ""
        self.organize_thread = None
        self._init_ui()
        self._display_results()
    
    def _init_ui(self):
        self.setWindowTitle("翻译结果")
        self.setMinimumSize(800, 500)
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.original_text.setPlaceholderText("原文和译文")
        splitter.addWidget(self.original_text)
        
        self.organized_text_edit = QTextEdit()
        self.organized_text_edit.setReadOnly(True)
        self.organized_text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.organized_text_edit.setPlaceholderText("整理后的文本（点击'整理'按钮生成）")
        splitter.addWidget(self.organized_text_edit)
        
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.organize_btn = QPushButton("整理")
        self.organize_btn.setFixedWidth(80)
        self.organize_btn.clicked.connect(self._on_organize)
        btn_layout.addWidget(self.organize_btn)
        
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
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QSplitter::handle {
                background-color: #3c3c3c;
                width: 2px;
            }
        """)
        
        font = QFont("Microsoft YaHei", 11)
        self.original_text.setFont(font)
        self.organized_text_edit.setFont(font)
    
    def _display_results(self):
        if not self.translations:
            self.original_text.setText("暂无翻译结果")
            return
        
        lines = []
        lines.append(f"=== 翻译结果 ({len(self.translations)} 条) ===\n")
        
        for i, item in enumerate(self.translations, 1):
            original = item.get("original", "")
            translated = item.get("translated", "")
            lines.append(f"[{i}] 原文: {original}")
            lines.append(f"    译文: {translated}")
            lines.append("")
        
        self.original_text.setText("\n".join(lines))
    
    def _on_organize(self):
        if not self.translator:
            self.organized_text_edit.setText("[错误: 未配置翻译器]")
            return
        
        if not self.translations:
            self.organized_text_edit.setText("[没有翻译结果]")
            return
        
        self.organize_btn.setEnabled(False)
        self.organize_btn.setText("整理中...")
        self.organized_text_edit.setText("正在整理...")
        
        self.organize_thread = OrganizeThread(self.translator, self.translations)
        self.organize_thread.finished.connect(self._on_organize_finished)
        self.organize_thread.error.connect(self._on_organize_error)
        self.organize_thread.start()
    
    def _on_organize_finished(self, result):
        self.organized_text = result
        self.organized_text_edit.setText(result)
        self.organize_btn.setEnabled(True)
        self.organize_btn.setText("整理")
    
    def _on_organize_error(self, error):
        self.organized_text_edit.setText(f"[整理错误: {error}]")
        self.organize_btn.setEnabled(True)
        self.organize_btn.setText("整理")
    
    def _on_copy(self):
        text = "=== 原始翻译 ===\n" + self.original_text.toPlainText()
        if self.organized_text:
            text += "\n\n=== 整理后 ===\n" + self.organized_text
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
                export_data = {
                    "translations": self.translations,
                    "organized": self.organized_text if self.organized_text else None
                }
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                text = "=== 原始翻译 ===\n" + self.original_text.toPlainText()
                if self.organized_text:
                    text += "\n\n=== 整理后 ===\n" + self.organized_text
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
    
    def closeEvent(self, event):
        if self.organize_thread and self.organize_thread.isRunning():
            self.organize_thread.terminate()
            self.organize_thread.wait()
        event.accept()
