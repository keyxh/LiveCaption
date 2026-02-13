from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, Signal, QThread
from pathlib import Path

class LoadingThread(QThread):
    progress = Signal(str, int)
    finished = Signal()
    error = Signal(str)
    
    def run(self):
        try:
            self.progress.emit("正在导入依赖库...", 10)
            import sherpa_onnx
            
            self.progress.emit("正在加载语音识别模型...", 30)
            
            base_dir = Path(__file__).parent
            model_dir = base_dir / "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
            
            encoder = str(model_dir / "encoder-epoch-99-avg-1.int8.onnx")
            decoder = str(model_dir / "decoder-epoch-99-avg-1.int8.onnx")
            joiner = str(model_dir / "joiner-epoch-99-avg-1.int8.onnx")
            tokens = str(model_dir / "tokens.txt")
            
            self.progress.emit("初始化识别引擎...", 50)
            
            recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                tokens=tokens,
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search"
            )
            
            self.progress.emit("正在加载标点模型...", 70)
            
            punct_model = None
            punct_dir = base_dir / "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12"
            punct_model_path = str(punct_dir / "model.onnx")
            
            if punct_dir.exists():
                try:
                    model_config = sherpa_onnx.OfflinePunctuationModelConfig(
                        ct_transformer=punct_model_path,
                        num_threads=2
                    )
                    config = sherpa_onnx.OfflinePunctuationConfig(model=model_config)
                    punct_model = sherpa_onnx.OfflinePunctuation(config)
                except Exception as e:
                    print(f"标点模型加载失败 (可选): {e}")
            
            self.progress.emit("模型加载完成", 100)
            
            self._recognizer = recognizer
            self._punct_model = punct_model
            self.finished.emit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def get_recognizer(self):
        return getattr(self, '_recognizer', None)
    
    def get_punct_model(self):
        return getattr(self, '_punct_model', None)

class SplashScreen(QWidget):
    loading_finished = Signal()
    
    def __init__(self):
        super().__init__()
        self.loading_thread = None
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.title_label = QLabel("实时翻译助手")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(self.title_label)
        
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #cccccc;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            QProgressBar {
                background-color: #3c3c3c;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 4px;
            }
        """)
    
    def start_loading(self):
        self.loading_thread = LoadingThread()
        self.loading_thread.progress.connect(self._on_progress)
        self.loading_thread.finished.connect(self._on_finished)
        self.loading_thread.error.connect(self._on_error)
        self.loading_thread.start()
    
    def _on_progress(self, status, value):
        self.status_label.setText(status)
        self.progress_bar.setValue(value)
    
    def _on_finished(self):
        self.loading_finished.emit()
    
    def _on_error(self, error):
        self.status_label.setText(f"加载失败: {error}")
        self.status_label.setStyleSheet("font-size: 12px; color: #ff6b6b;")
    
    def closeEvent(self, event):
        if self.loading_thread and self.loading_thread.isRunning():
            self.loading_thread.terminate()
            self.loading_thread.wait()
        event.accept()
