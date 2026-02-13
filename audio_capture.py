import threading
import queue
import numpy as np
import time

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    import pyaudio

class AudioCapture:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=4096):
        self.target_sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.audio_queue = queue.Queue(maxsize=100)
        self.is_capturing = False
        self.is_initialized = False
        self.init_error = None
        self.pyaudio_instance = None
        self.stream = None
        self.thread = None
        self.buffer = []
        self.buffer_size = 8
        
    def _get_loopback_device(self, p):
        try:
            for i in range(p.get_device_count()):
                device = p.get_device_info_by_index(i)
                if device.get("isLoopbackDevice", False):
                    print(f"[Audio] 找到 Loopback 设备: {device['name']}")
                    return device
            for i in range(p.get_device_count()):
                device = p.get_device_info_by_index(i)
                name = device.get("name", "").lower()
                if "loopback" in name:
                    print(f"[Audio] 找到 Loopback 设备(名称匹配): {device['name']}")
                    return device
            print("[Audio] 未找到 Loopback 设备")
            return None
        except Exception as e:
            print(f"[Audio] 获取设备列表错误: {e}")
            return None
    
    def _resample(self, audio_data, orig_sr, target_sr):
        if orig_sr == target_sr:
            return audio_data
        ratio = target_sr / orig_sr
        new_length = int(len(audio_data) * ratio)
        indices = np.linspace(0, len(audio_data) - 1, new_length)
        return np.interp(indices, np.arange(len(audio_data)), audio_data)
    
    def _callback(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        if self.sample_rate != self.target_sample_rate:
            audio_data = self._resample(audio_data, self.sample_rate, self.target_sample_rate)
        
        self.buffer.append(audio_data)
        if len(self.buffer) >= self.buffer_size:
            combined = np.concatenate(self.buffer)
            self.buffer = []
            try:
                self.audio_queue.put_nowait(combined)
            except queue.Full:
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(combined)
                except:
                    pass
        
        return (in_data, pyaudio.paContinue)
    
    def _capture_thread(self):
        try:
            print("[Audio] 创建 PyAudio 实例...")
            self.pyaudio_instance = pyaudio.PyAudio()
            
            print("[Audio] 查找 Loopback 设备...")
            device = self._get_loopback_device(self.pyaudio_instance)
            
            if device is None:
                self.init_error = "未找到系统音频捕获设备"
                self.is_capturing = False
                print(f"[Audio] 错误: {self.init_error}")
                return
            
            self.sample_rate = int(device.get("defaultSampleRate", 48000))
            print(f"[Audio] 使用设备: {device['name']} (index={device['index']}, rate={self.sample_rate})")
            
            print("[Audio] 打开音频流...")
            self.stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=self.chunk_size,
                stream_callback=self._callback
            )
            
            print("[Audio] 启动音频流...")
            self.stream.start_stream()
            self.is_initialized = True
            print("[Audio] 音频流已启动")
            
            while self.is_capturing and self.stream and self.stream.is_active():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"[Audio] 捕获线程错误: {e}")
            import traceback
            traceback.print_exc()
            self.init_error = str(e)
            self.is_capturing = False
        finally:
            self._cleanup()
    
    def _cleanup(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
            self.pyaudio_instance = None
    
    def start(self):
        if self.is_capturing:
            return
        self.is_capturing = True
        self.is_initialized = False
        self.init_error = None
        self.thread = threading.Thread(target=self._capture_thread, daemon=True)
        self.thread.start()
    
    def wait_initialized(self, timeout=5.0):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_initialized:
                return True
            if self.init_error:
                return False
            time.sleep(0.05)
        self.init_error = "初始化超时"
        return False
    
    def stop(self):
        self.is_capturing = False
        self._cleanup()
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
    
    def get_audio_chunk(self, timeout=None):
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_status(self):
        if self.init_error:
            return {"ok": False, "error": self.init_error}
        if self.is_initialized:
            return {"ok": True, "error": None}
        return {"ok": False, "error": "未初始化"}
