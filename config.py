import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "settings.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "api_base": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "target_language": "中文",
    "whisper_model": "base",
    "window_topmost": False,
    "font_size": 14,
    "window_opacity": 0.9,
    "bypass_proxy": False
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            for key in DEFAULT_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_CONFIG[key]
            return config
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
