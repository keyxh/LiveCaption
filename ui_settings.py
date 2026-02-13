from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QGroupBox,
    QFormLayout, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal
from openai import OpenAI
import httpx

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
TARGET_LANGUAGES = [
    "中文", "英文", "日文", "韩文", "法文", "德文", 
    "西班牙文", "俄文", "葡萄牙文", "意大利文"
]
DEFAULT_MODELS = ["deepseek-chat"]

class ModelLoaderThread(QThread):
    models_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, api_key, api_base, bypass_proxy=True):
        super().__init__()
        self.api_key = api_key
        self.api_base = api_base
        self.bypass_proxy = bypass_proxy
    
    def run(self):
        try:
            if self.bypass_proxy:
                http_client = httpx.Client(proxy=None)
                client = OpenAI(api_key=self.api_key, base_url=self.api_base, http_client=http_client)
            else:
                client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            models = client.models.list()
            model_ids = sorted([m.id for m in models.data])
            self.models_loaded.emit(model_ids)
        except Exception as e:
            self.error_occurred.emit(str(e))

class SettingsDialog(QDialog):
    config_saved = Signal(dict)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.loader_thread = None
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        self.setWindowTitle("设置")
        self.setFixedSize(450, 450)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        api_group = QGroupBox("API 设置")
        api_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key")
        self.api_key_edit.textChanged.connect(self._on_api_changed)
        api_layout.addRow("API Key:", self.api_key_edit)
        
        self.api_base_edit = QLineEdit()
        self.api_base_edit.setPlaceholderText("https://api.deepseek.com")
        self.api_base_edit.textChanged.connect(self._on_api_changed)
        api_layout.addRow("API Base:", self.api_base_edit)
        
        self.bypass_proxy_cb = QCheckBox("绕过系统代理")
        self.bypass_proxy_cb.setChecked(False)
        api_layout.addRow("", self.bypass_proxy_cb)
        
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(DEFAULT_MODELS)
        model_layout.addWidget(self.model_combo, 1)
        
        self.load_models_btn = QPushButton("加载")
        self.load_models_btn.setFixedWidth(60)
        self.load_models_btn.clicked.connect(self._load_models)
        model_layout.addWidget(self.load_models_btn)
        
        api_layout.addRow("翻译模型:", model_layout)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        whisper_group = QGroupBox("语音识别设置")
        whisper_layout = QFormLayout()
        
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(WHISPER_MODELS)
        whisper_layout.addRow("Whisper模型:", self.whisper_model_combo)
        
        whisper_group.setLayout(whisper_layout)
        layout.addWidget(whisper_group)
        
        translate_group = QGroupBox("翻译设置")
        translate_layout = QFormLayout()
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(TARGET_LANGUAGES)
        translate_layout.addRow("目标语言:", self.target_lang_combo)
        
        translate_group.setLayout(translate_layout)
        layout.addWidget(translate_group)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self._apply_style()
    
    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
            QLineEdit, QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)
    
    def _on_api_changed(self):
        pass
    
    def _load_models(self):
        api_key = self.api_key_edit.text().strip()
        api_base = self.api_base_edit.text().strip() or "https://api.deepseek.com"
        bypass_proxy = self.bypass_proxy_cb.isChecked()
        
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return
        
        self.load_models_btn.setEnabled(False)
        self.load_models_btn.setText("加载中...")
        
        self.loader_thread = ModelLoaderThread(api_key, api_base, bypass_proxy)
        self.loader_thread.models_loaded.connect(self._on_models_loaded)
        self.loader_thread.error_occurred.connect(self._on_load_error)
        self.loader_thread.start()
    
    def _on_models_loaded(self, models):
        self.load_models_btn.setEnabled(True)
        self.load_models_btn.setText("加载")
        
        current_text = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        
        index = self.model_combo.findText(current_text)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        elif models:
            self.model_combo.setCurrentIndex(0)
    
    def _on_load_error(self, error):
        self.load_models_btn.setEnabled(True)
        self.load_models_btn.setText("加载")
        QMessageBox.warning(self, "加载失败", f"无法获取模型列表:\n{error}")
    
    def _load_config(self):
        self.api_key_edit.setText(self.config.get("api_key", ""))
        self.api_base_edit.setText(self.config.get("api_base", "https://api.deepseek.com"))
        self.bypass_proxy_cb.setChecked(self.config.get("bypass_proxy", False))
        
        model = self.config.get("model", "deepseek-chat")
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            self.model_combo.setCurrentText(model)
        
        whisper_model = self.config.get("whisper_model", "base")
        index = self.whisper_model_combo.findText(whisper_model)
        if index >= 0:
            self.whisper_model_combo.setCurrentIndex(index)
        
        target_lang = self.config.get("target_language", "中文")
        index = self.target_lang_combo.findText(target_lang)
        if index >= 0:
            self.target_lang_combo.setCurrentIndex(index)
    
    def _on_save(self):
        self.config["api_key"] = self.api_key_edit.text().strip()
        self.config["api_base"] = self.api_base_edit.text().strip() or "https://api.deepseek.com"
        self.config["bypass_proxy"] = self.bypass_proxy_cb.isChecked()
        self.config["model"] = self.model_combo.currentText().strip()
        self.config["whisper_model"] = self.whisper_model_combo.currentText()
        self.config["target_language"] = self.target_lang_combo.currentText()
        self.config_saved.emit(self.config)
        self.accept()
    
    def get_config(self):
        return self.config
    
    def closeEvent(self, event):
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()
        event.accept()
