import os
import sys
import threading
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Signal, QObject

from config import load_config, save_config
from audio_capture import AudioCapture
from asr_processor import ASRProcessor
from translator import Translator
from ui_main import TranslationBar
from ui_settings import SettingsDialog
from ui_result import ResultDialog
from ui_splash import SplashScreen

class SignalBridge(QObject):
    original_updated = Signal(str)
    translated_updated = Signal(str, str)
    status_updated = Signal(str)
    start_finished = Signal(bool)

class RealtimeTranslator:
    def __init__(self):
        self.config = load_config()
        
        self.audio_capture = None
        self.asr_processor = None
        self.translator = Translator(
            api_key=self.config.get("api_key", ""),
            api_base=self.config.get("api_base", "https://api.deepseek.com"),
            model=self.config.get("model", "deepseek-chat"),
            bypass_proxy=self.config.get("bypass_proxy", False),
            translate_api_key=self.config.get("translate_api_key", ""),
            translate_api_base=self.config.get("translate_api_base", "https://api.siliconflow.cn/v1"),
            translate_model=self.config.get("translate_model", "Qwen/Qwen3-8B"),
            organize_api_key=self.config.get("organize_api_key", ""),
            organize_api_base=self.config.get("organize_api_base", "https://api.deepseek.com"),
            organize_model=self.config.get("organize_model", "deepseek-chat")
        )
        
        self.is_running = False
        self.process_thread = None
        
        self.signal_bridge = SignalBridge()
    
    def start_async(self):
        if self.is_running:
            self.signal_bridge.start_finished.emit(True)
            return
        
        def init_thread():
            try:
                print("[DEBUG] 开始初始化...")
                
                if self.audio_capture is None:
                    self.audio_capture = AudioCapture(sample_rate=16000)
                
                self.signal_bridge.status_updated.emit("正在初始化音频...")
                print("[DEBUG] 启动音频捕获...")
                self.audio_capture.start()
                
                print("[DEBUG] 等待音频初始化...")
                if not self.audio_capture.wait_initialized(timeout=5.0):
                    status = self.audio_capture.get_status()
                    error_msg = status.get('error', '未知错误')
                    print(f"[DEBUG] 音频初始化失败: {error_msg}")
                    self.signal_bridge.status_updated.emit(f"音频失败: {error_msg}")
                    self.signal_bridge.start_finished.emit(False)
                    return
                
                print("[DEBUG] 音频初始化成功")
                self.signal_bridge.status_updated.emit("正在加载识别模型...")
                
                if self.asr_processor is None:
                    try:
                        self.asr_processor = ASRProcessor()
                        self.asr_processor.start()
                    except Exception as e:
                        print(f"[DEBUG] ASR初始化失败: {e}")
                        self.signal_bridge.status_updated.emit(f"模型加载失败: {str(e)[:50]}")
                        self.signal_bridge.start_finished.emit(False)
                        return
                
                self.signal_bridge.status_updated.emit("正在启动翻译引擎...")
                self.translator.start()
                
                self.is_running = True
                self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
                self.process_thread.start()
                
                self.signal_bridge.status_updated.emit("运行中")
                self.signal_bridge.start_finished.emit(True)
                print("[DEBUG] 初始化完成")
                
            except Exception as e:
                print(f"[DEBUG] 初始化异常: {e}")
                import traceback
                traceback.print_exc()
                self.signal_bridge.status_updated.emit(f"初始化失败: {str(e)[:50]}")
                self.signal_bridge.start_finished.emit(False)
        
        threading.Thread(target=init_thread, daemon=True).start()
    
    def stop(self):
        self.is_running = False
        
        if self.audio_capture:
            self.audio_capture.stop()
        if self.asr_processor:
            self.asr_processor.stop()
        self.translator.stop()
        
        if self.process_thread:
            self.process_thread.join(timeout=2)
        
        self.signal_bridge.status_updated.emit("已停止")
    
    def _process_loop(self):
        while self.is_running:
            try:
                if not self.audio_capture:
                    time.sleep(0.1)
                    continue
                    
                audio_chunk = self.audio_capture.get_audio_chunk(timeout=0.1)
                if audio_chunk is not None and self.asr_processor:
                    self.asr_processor.add_audio(audio_chunk)
                
                if self.asr_processor:
                    asr_result = self.asr_processor.get_result(timeout=0.05)
                    if asr_result:
                        text = asr_result["text"]
                        self.signal_bridge.original_updated.emit(text)
                        if asr_result.get("is_final"):
                            self.translator.add_text(text, self.config.get("target_language", "中文"))
                
                translate_result = self.translator.get_result(timeout=0.05)
                if translate_result:
                    self.signal_bridge.translated_updated.emit(
                        translate_result["original"],
                        translate_result["translated"]
                    )
                    
            except Exception as e:
                print(f"处理循环错误: {e}")
                time.sleep(0.1)

class MainWindow(TranslationBar):
    def __init__(self):
        super().__init__()
        
        self.translator = RealtimeTranslator()
        self.settings_dialog = None
        self.result_dialog = None
        
        self.start_clicked.connect(self.on_start_clicked)
        self.stop_clicked.connect(self.on_stop_clicked)
        self.settings_clicked.connect(self.on_settings_clicked)
        self.result_clicked.connect(self.on_result_clicked)
        
        self.translator.signal_bridge.original_updated.connect(self.update_original_text)
        self.translator.signal_bridge.translated_updated.connect(self.update_translated_text)
        self.translator.signal_bridge.status_updated.connect(self.update_status)
        self.translator.signal_bridge.start_finished.connect(self.on_start_finished)
    
    def on_start_clicked(self):
        self.translator.start_async()
    
    def on_stop_clicked(self):
        self.translator.stop()
    
    def on_settings_clicked(self):
        self.settings_dialog = SettingsDialog(self.translator.config)
        self.settings_dialog.config_saved.connect(self.on_config_saved)
        self.settings_dialog.exec()
    
    def on_config_saved(self, config):
        save_config(config)
        self.translator.config = config
        self.translator.translator = Translator(
            api_key=config.get("api_key", ""),
            api_base=config.get("api_base", "https://api.deepseek.com"),
            model=config.get("model", "deepseek-chat"),
            bypass_proxy=config.get("bypass_proxy", False),
            translate_api_key=config.get("translate_api_key", ""),
            translate_api_base=config.get("translate_api_base", "https://api.siliconflow.cn/v1"),
            translate_model=config.get("translate_model", "Qwen/Qwen3-8B"),
            organize_api_key=config.get("organize_api_key", ""),
            organize_api_base=config.get("organize_api_base", "https://api.deepseek.com"),
            organize_model=config.get("organize_model", "deepseek-chat")
        )
    
    def on_result_clicked(self):
        self.result_dialog = ResultDialog(self.translator.translator.get_all_results(), self.translator.translator)
        self.result_dialog.exec()
    
    def on_start_finished(self, success):
        self.set_running(success)
    
    def update_original_text(self, text):
        self.set_original_text(text)
    
    def update_translated_text(self, original, translated):
        self.set_translated_text(original, translated)
    
    def update_status(self, status):
        self.set_status(status)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    splash.show()
    
    main_window = [None]
    
    def on_loading_finished():
        main_window[0] = MainWindow()
        main_window[0].show()
        splash.close()
    
    splash.loading_finished.connect(on_loading_finished)
    splash.start_loading()
    
    sys.exit(app.exec())
