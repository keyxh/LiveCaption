import threading
import queue
import os
from openai import OpenAI
import httpx

class Translator:
    def __init__(self, 
                 api_key="", api_base="https://api.deepseek.com", model="deepseek-chat", bypass_proxy=False,
                 translate_api_key="", translate_api_base="https://api.siliconflow.cn/v1", translate_model="Qwen/Qwen3-8B",
                 organize_api_key="", organize_api_base="https://api.deepseek.com", organize_model="deepseek-chat"):
        
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.bypass_proxy = bypass_proxy
        
        self.translate_api_key = translate_api_key or api_key
        self.translate_api_base = translate_api_base
        self.translate_model = translate_model
        
        self.organize_api_key = organize_api_key or api_key
        self.organize_api_base = organize_api_base
        self.organize_model = organize_model
        
        self.translate_client = None
        self.organize_client = None
        self.client = None
        
        self.translate_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        self.thread = None
        self.all_results = []
        
        self._init_clients()
    
    def _create_client(self, api_key, api_base):
        if not api_key:
            return None
        if self.bypass_proxy:
            http_client = httpx.Client(trust_env=False)
            return OpenAI(api_key=api_key, base_url=api_base, http_client=http_client)
        else:
            return OpenAI(api_key=api_key, base_url=api_base)
    
    def _init_clients(self):
        print(f"[Translator] 初始化客户端: bypass_proxy={self.bypass_proxy}")
        
        self.translate_client = self._create_client(self.translate_api_key, self.translate_api_base)
        self.organize_client = self._create_client(self.organize_api_key, self.organize_api_base)
        
        if self.api_key:
            self.client = self._create_client(self.api_key, self.api_base)
    
    def update_config(self, **kwargs):
        if 'api_key' in kwargs:
            self.api_key = kwargs['api_key']
        if 'api_base' in kwargs:
            self.api_base = kwargs['api_base']
        if 'model' in kwargs:
            self.model = kwargs['model']
        if 'bypass_proxy' in kwargs:
            self.bypass_proxy = kwargs['bypass_proxy']
        if 'translate_api_key' in kwargs:
            self.translate_api_key = kwargs['translate_api_key']
        if 'translate_api_base' in kwargs:
            self.translate_api_base = kwargs['translate_api_base']
        if 'translate_model' in kwargs:
            self.translate_model = kwargs['translate_model']
        if 'organize_api_key' in kwargs:
            self.organize_api_key = kwargs['organize_api_key']
        if 'organize_api_base' in kwargs:
            self.organize_api_base = kwargs['organize_api_base']
        if 'organize_model' in kwargs:
            self.organize_model = kwargs['organize_model']
        
        self._init_clients()
    
    def add_text(self, text, target_language="中文"):
        self.translate_queue.put({"text": text, "target_language": target_language})
    
    def _process_thread(self):
        while self.is_running:
            try:
                item = self.translate_queue.get(timeout=0.5)
                text = item["text"]
                target_language = item["target_language"]
                
                client = self.translate_client or self.client
                model = self.translate_model if self.translate_client else self.model
                
                if not client or not (self.translate_api_key or self.api_key):
                    self.result_queue.put({
                        "original": text,
                        "translated": "[未配置API密钥]",
                        "success": False
                    })
                    continue
                
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system", 
                                "content": f"你是一个翻译助手。请将用户输入的文本翻译成{target_language}。\n\n注意：输入文本来自语音识别，可能存在识别错误。请在翻译时：\n1. 根据上下文推断并纠正可能的识别错误\n2. 输出通顺自然的翻译结果\n3. 只输出翻译结果，不要输出其他内容\n4. 如果输入已经是{target_language}，请直接输出原文"
                            },
                            {"role": "user", "content": text}
                        ],
                        temperature=0.3,
                        max_tokens=4096
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
        client = self.translate_client or self.client
        model = self.translate_model if self.translate_client else self.model
        
        if not client or not (self.translate_api_key or self.api_key):
            return {"original": text, "translated": "[未配置API密钥]", "success": False}
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"你是一个翻译助手。请将用户输入的文本翻译成{target_language}。\n\n注意：输入文本来自语音识别，可能存在识别错误。请在翻译时：\n1. 根据上下文推断并纠正可能的识别错误\n2. 输出通顺自然的翻译结果\n3. 只输出翻译结果，不要输出其他内容\n4. 如果输入已经是{target_language}，请直接输出原文"
                    },
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=4096
            )
            
            translated = response.choices[0].message.content.strip()
            return {"original": text, "translated": translated, "success": True}
            
        except Exception as e:
            return {"original": text, "translated": f"[翻译错误: {str(e)}]", "success": False}
    
    def _organize_chunk(self, text_chunk):
        client = self.organize_client or self.client
        model = self.organize_model if self.organize_client else self.model
        
        if not client:
            return None, "未配置整理API密钥"
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个文本整理助手。用户会给你一段来自语音识别翻译的文本，可能存在以下问题：\n1. 识别错误导致的错别字\n2. 翻译不准确\n3. 句子不连贯\n\n请整理这段文本：\n- 保留所有内容，不要删除任何信息\n- 纠正明显的识别错误\n- 使句子通顺连贯\n- 保持原意不变\n- 输出完整连贯的段落"
                    },
                    {"role": "user", "content": text_chunk}
                ],
                temperature=0.3,
                max_tokens=8192
            )
            
            return response.choices[0].message.content.strip(), None
            
        except Exception as e:
            return None, str(e)
    
    def organize_results(self, translations):
        if not translations:
            return None, "没有翻译结果"
        
        client = self.organize_client or self.client
        if not client:
            return None, "未配置API密钥"
        
        all_text = "\n".join([t.get("translated", "") for t in translations])
        
        max_chunk_chars = 6000
        if len(all_text) <= max_chunk_chars:
            return self._organize_chunk(all_text)
        
        chunks = []
        lines = all_text.split("\n")
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_chunk_chars:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n" + line if current_chunk else line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"[Translator] 分段整理: {len(chunks)} 段, 总字符: {len(all_text)}")
        
        organized_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"[Translator] 整理第 {i+1}/{len(chunks)} 段 ({len(chunk)}字符)...")
            result, error = self._organize_chunk(chunk)
            if error:
                return None, f"第{i+1}段整理错误: {error}"
            organized_chunks.append(result)
        
        if len(organized_chunks) == 1:
            return organized_chunks[0], None
        
        final_text = "\n\n".join(organized_chunks)
        
        try:
            print(f"[Translator] 最终整合 {len(organized_chunks)} 段...")
            response = client.chat.completions.create(
                model=self.organize_model if self.organize_client else self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个文本整合助手。用户会给你多段已整理的文本，请将它们整合成一篇完整连贯的文章。\n- 保留所有内容，不要删除任何信息\n- 保持内容连贯\n- 合并成一段完整的文本\n- 只输出整合后的文本"
                    },
                    {"role": "user", "content": final_text}
                ],
                temperature=0.3,
                max_tokens=8192
            )
            
            return response.choices[0].message.content.strip(), None
            
        except Exception as e:
            print(f"[Translator] 最终整合失败: {e}")
            return final_text, None
