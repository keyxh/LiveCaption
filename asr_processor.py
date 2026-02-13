import os
import threading
import queue
import time
import numpy as np
from pathlib import Path

class ASRProcessor:
    def __init__(self, model_dir=None, preloaded_recognizer=None, preloaded_punct=None):
        self.model_dir = model_dir or self._get_default_model_dir()
        self.recognizer = preloaded_recognizer
        self.punct_model = preloaded_punct
        self.audio_queue = queue.Queue(maxsize=50)
        self.result_queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.sample_rate = 16000
        
        if preloaded_recognizer is None:
            self._init_model()
    
    def _get_default_model_dir(self):
        base_dir = Path(__file__).parent
        return base_dir / "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
    
    def _init_model(self):
        try:
            import sherpa_onnx
            
            model_path = Path(self.model_dir)
            
            encoder = str(model_path / "encoder-epoch-99-avg-1.int8.onnx")
            decoder = str(model_path / "decoder-epoch-99-avg-1.int8.onnx")
            joiner = str(model_path / "joiner-epoch-99-avg-1.int8.onnx")
            tokens = str(model_path / "tokens.txt")
            
            if not all(Path(p).exists() for p in [encoder, decoder, joiner, tokens]):
                encoder = str(model_path / "encoder-epoch-99-avg-1.onnx")
                decoder = str(model_path / "decoder-epoch-99-avg-1.onnx")
                joiner = str(model_path / "joiner-epoch-99-avg-1.onnx")
            
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                tokens=tokens,
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                enable_endpoint_detection=True,
                rule1_min_trailing_silence=2.4,
                rule2_min_trailing_silence=1.2,
                rule3_min_utterance_length=30.0
            )
            
            self._init_punct_model()
            
            print(f"[ASR] 模型加载成功: {self.model_dir}")
            
        except Exception as e:
            print(f"[ASR] 模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _init_punct_model(self):
        try:
            import sherpa_onnx
            
            base_dir = Path(__file__).parent
            punct_dir = base_dir / "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12"
            punct_model_path = str(punct_dir / "model.onnx")
            
            if punct_dir.exists():
                model_config = sherpa_onnx.OfflinePunctuationModelConfig(
                    ct_transformer=punct_model_path,
                    num_threads=2
                )
                config = sherpa_onnx.OfflinePunctuationConfig(model=model_config)
                self.punct_model = sherpa_onnx.OfflinePunctuation(config)
                print("[ASR] 标点模型加载成功")
        except Exception as e:
            print(f"[ASR] 标点模型加载失败 (可选): {e}")
            self.punct_model = None
    
    def add_audio(self, audio_data):
        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            pass
    
    def _process_thread(self):
        stream = self.recognizer.create_stream()
        last_result = ""
        audio_count = 0
        
        print("[ASR] 开始处理音频流...")
        
        while self.is_running:
            try:
                audio_data = self.audio_queue.get(timeout=0.2)
                audio_count += 1
                
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                stream.accept_waveform(self.sample_rate, audio_data)
                
                while self.recognizer.is_ready(stream):
                    self.recognizer.decode_stream(stream)
                
                result = self.recognizer.get_result(stream)
                
                if result and result != last_result:
                    last_result = result
                    text = result.strip()
                    if text:
                        print(f"[ASR] 实时识别: {text}")
                        self.result_queue.put({
                            "text": text,
                            "is_final": False
                        })
                
                if self.recognizer.is_endpoint(stream):
                    result = self.recognizer.get_result(stream)
                    if result and result.strip():
                        text = result.strip()
                        if self.punct_model:
                            try:
                                text = self.punct_model.add_punctuation(text)
                            except:
                                pass
                        
                        print(f"[ASR] 最终结果: {text}")
                        self.result_queue.put({
                            "text": text,
                            "is_final": True
                        })
                    
                    self.recognizer.reset(stream)
                    last_result = ""
                
            except queue.Empty:
                if self.recognizer.is_ready(stream):
                    self.recognizer.decode_stream(stream)
                    result = self.recognizer.get_result(stream)
                    if result and result != last_result:
                        last_result = result
                        text = result.strip()
                        if text:
                            print(f"[ASR] 实时识别(空): {text}")
                            self.result_queue.put({
                                "text": text,
                                "is_final": False
                            })
                continue
            except Exception as e:
                print(f"[ASR] 处理错误: {e}")
                import traceback
                traceback.print_exc()
    
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._process_thread, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def get_result(self, timeout=None):
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
