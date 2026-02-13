import threading
import queue
import os
from openai import OpenAI
import httpx

class Translator:
    def __init__(self, api_key="", api_base="https://api.deepseek.com", model="deepseek-chat", bypass_proxy=False):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.bypass_proxy = bypass_proxy
        self.client = None
        self.translate_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.all_results = []
        self._init_client()
    
    def _init_client(self):
        print(f"[Translator] 初始化客户端: bypass_proxy={self.bypass_proxy}, api_base={self.api_base}")
        if self.api_key:
            if self.bypass_proxy:
                print("[Translator] 绕过代理模式")
                http_client = httpx.Client(trust_env=False)
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                    http_client=http_client
                )
            else:
                print("[Translator] 使用系统代理模式")
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base
                )
    
    def update_config(self, api_key=None, api_base=None, model=None, bypass_proxy=None):
        print(f"[Translator] 更新配置: bypass_proxy={bypass_proxy}")
        if api_key is not None:
            self.api_key = api_key
        if api_base is not None:
            self.api_base = api_base
        if model is not None:
            self.model = model
        if bypass_proxy is not None:
            self.bypass_proxy = bypass_proxy
        self._init_client()
    
    def add_text(self, text, target_language="中文"):
        self.translate_queue.put({"text": text, "target_language": target_language})
    
    def _process_thread(self):
        while self.is_running:
            try:
                item = self.translate_queue.get(timeout=0.5)
                text = item["text"]
                target_language = item["target_language"]
                
                if not self.client or not self.api_key:
                    self.result_queue.put({
                        "original": text,
                        "translated": "[未配置API密钥]",
                        "success": False
                    })
                    continue
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system", 
                                "content": f"你是一个翻译助手。请将用户输入的文本翻译成{target_language}。\n\n注意：输入文本来自语音识别，可能存在识别错误。请在翻译时：\n1. 根据上下文推断并纠正可能的识别错误\n2. 输出通顺自然的翻译结果\n3. 只输出翻译结果，不要输出其他内容\n4. 如果输入已经是{target_language}，请直接输出原文"
                            },
                            {"role": "user", "content": text}
                        ],
                        temperature=0.3,
                        max_tokens=1024
                    )
                    
                    translated = response.choices[0].message.content.strip()
                    result = {
                        "original": text,
                        "translated": translated,
                        "success": True
                    }
                    self.all_results.append(result)
                    self.result_queue.put(result)
                    
                except Exception as e:
                    import traceback
                    print(f"[Translator] 翻译错误: {e}")
                    traceback.print_exc()
                    self.result_queue.put({
                        "original": text,
                        "translated": f"[翻译错误: {str(e)}]",
                        "success": False
                    })
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"翻译处理错误: {e}")
    
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
    
    def get_all_results(self):
        return self.all_results.copy()
    
    def clear_results(self):
        self.all_results = []
    
    def translate_sync(self, text, target_language="中文"):
        if not self.client or not self.api_key:
            return {"original": text, "translated": "[未配置API密钥]", "success": False}
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"你是一个翻译助手。请将用户输入的文本翻译成{target_language}。\n\n注意：输入文本来自语音识别，可能存在识别错误。请在翻译时：\n1. 根据上下文推断并纠正可能的识别错误\n2. 输出通顺自然的翻译结果\n3. 只输出翻译结果，不要输出其他内容\n4. 如果输入已经是{target_language}，请直接输出原文"
                    },
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            translated = response.choices[0].message.content.strip()
            return {"original": text, "translated": translated, "success": True}
            
        except Exception as e:
            return {"original": text, "translated": f"[翻译错误: {str(e)}]", "success": False}
