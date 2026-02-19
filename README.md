# 实时音频翻译工具

一个实时捕获系统音频并进行语音识别和翻译的桌面应用程序。 如果大家觉得好用，给一下star

## 功能特点

- **实时音频捕获**：直接捕获系统音频输出（无需麦克风）
- **语音识别**：使用 sherpa-onnx 进行本地 ASR 识别
- **实时翻译**：支持多种翻译 API（默认 DeepSeek）
- **标点恢复**：自动为识别结果添加标点符号
- **简洁界面**：横条式 GUI，支持窗口置顶
- **代理支持**：可配置是否绕过系统代理

## 安装

### 依赖要求

- Python 3.9+
- Windows 操作系统（需要 WASAPI 音频接口）

### 安装步骤

1. 解压 `opencode.zipx` 及分卷文件（使用 7-Zip 或 WinRAR）
2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 首次使用请点击"设置"配置 API：
   - API Key：翻译服务的密钥
   - API Base：API 地址（默认 DeepSeek）
   - 翻译模型：选择使用的模型
   - 目标语言：翻译目标语言

3. 播放视频或音频，点击"开始"按钮

4. 程序会实时显示识别的原文和翻译结果

5. 点击"结果"查看所有翻译历史

## 界面说明

| 按钮 | 功能 |
|------|------|
| 开始 | 开始音频捕获和翻译 |
| 停止 | 停止当前会话 |
| 置顶 | 将窗口置于最前 |
| 设置 | 打开设置对话框 |
| 结果 | 查看所有翻译结果 |

## 配置说明

### API 设置

- **API Key**：翻译服务的 API 密钥
- **API Base**：API 服务地址
- **绕过系统代理**：勾选后不使用系统代理（国内 API 推荐）

### 支持的翻译服务

- DeepSeek（默认）
- OpenAI
- 其他兼容 OpenAI API 格式的服务

## 项目结构

```
asr_translate/
├── main.py           # 主程序入口
├── config.py         # 配置管理
├── audio_capture.py  # 音频捕获模块
├── asr_processor.py  # 语音识别模块
├── translator.py     # 翻译模块
├── ui_main.py        # 主界面
├── ui_settings.py    # 设置界面
├── ui_result.py      # 结果界面
├── ui_splash.py      # 启动画面
├── requirements.txt  # 依赖列表
└── settings.json     # 用户配置
```

## 技术栈

- **GUI**：PySide6
- **音频捕获**：pyaudiowpatch (WASAPI Loopback)
- **语音识别**：sherpa-onnx
- **翻译 API**：OpenAI API 格式
- **HTTP 客户端**：httpx

## 注意事项

1. 首次运行会自动下载 ASR 模型（约 100MB）
2. 需要系统支持 WASAPI Loopback 音频捕获
3. 如使用代理访问国外 API，请取消"绕过系统代理"选项
4. 如访问国内 API（如 DeepSeek），请勾选"绕过系统代理"

## 许可证

MIT License
