<div align="center">

# Dictatly

**High-performance, private, local speech-to-text dictation & transcription for Windows 10/11.**  
*Native Apple macOS Sequoia design language • Hardware-accelerated Faster-Whisper • Zero AI-slop.*

---

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D4?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Engine](https://img.shields.io/badge/ASR-Faster--Whisper%20(CUDA%20FP16)-76B900?logo=nvidia&logoColor=white)](https://github.com/SYSTRAN/faster-whisper)
[![UI](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52?logo=qt&logoColor=white)](https://qt.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 🌟 Highlights

Dictatly is a lightweight, system-wide speech dictation and transcription utility built from the ground up for Windows. It runs completely offline on your local GPU or CPU, ensuring that your voice and text never leave your machine unless you explicitly choose to use optional cloud LLM cleanup.

- ⚡ **Near-Instant Local Transcription:** Powered by `faster-whisper` (`large-v3-turbo` / `small` models) with NVIDIA CUDA FP16 acceleration. A 5–10 second voice recording is transcribed in ~100–150 ms with accurate punctuation and capitalization.
- 💊 **Floating Liquid Glass HUD:** A frameless, non-activating floating capsule HUD appears dynamically above your active text cursor across any application (VS Code, Word, Chrome, Notepad, Telegram). It features an interactive volume equalizer and automatically vanishes upon completion.
- ⌨️ **Low-Level Global Hotkeys:** Powered by a native Win32 low-level keyboard hook (`WH_KEYBOARD_LL`) that accurately distinguishes left and right modifier keys (`Right Ctrl`, `Right Alt / AltGr`, `Right Shift`, `Right Win`).
- 📋 **Seamless Text Injection:** Injects transcribed text directly at the cursor using hardware-scan clipboard simulation with thread-input attachment, foreground window recovery, and automatic clipboard restoration.
- 📜 **Quick History & Drag-and-Drop Batch Processing:** Instant history popup with fast search, pagination, and click-to-copy. Drag and drop audio files (`.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`) directly into the window for automated batch transcription into `.txt` files.
- 🪄 **Optional AI Text Cleanup:** Fix stuttering, filler words, and polish formatting using any OpenAI-compatible API (Groq, OpenAI, DeepSeek, or local Ollama). API keys are encrypted locally via Windows DPAPI (`CryptProtectData`).
- 🍎 **Apple macOS Sequoia Aesthetics:** Clean grouped card layout, warm neutral graphite palette (`#1E1E20`), tactile MacBook-style chiclet keycaps, and native typography (`-apple-system`, `Segoe UI Variable`).
- 🌐 **Full Bilingual Support:** Instant toggle between English and Russian across all windows and notifications.

---

## 📸 Screenshots & Aesthetics

- **Settings & Control Panel:** Grouped card architecture with tactile keycaps, audio device picker, model quantization selectors, and theme configuration.
- **Floating HUD Capsule:** Minimalist dark glass pill with amber recording indicator and dynamic 4-bar equalizer.
- **Quick History:** Searchable transcript cards with timestamps, word counts, and drag-and-drop batch import.

---

## ⌨️ Default Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Right Ctrl`** | **Toggle Dictation** | Press once to start recording; press again to finish and inject text. |
| **`Right Shift + Right Ctrl`** | **Alternative Finish** | Inverts the "Press Enter after insert" setting for the current phrase. |
| **`Right Alt + Right Ctrl`** | **Quick History** | Opens the Quick History window and drag-and-drop batch transcription. |

*All shortcuts can be customized in the Settings panel.*

---

## 💻 System Requirements

- **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python:** Python 3.10 to 3.12 (64-bit).
- **Audio:** Working microphone input.
- **GPU (Recommended):** NVIDIA GPU with CUDA 12 support (RTX 3060 or newer recommended for ~100ms FP16 inference).
- **CPU Fallback:** Multi-threaded CPU mode with int8 quantization is automatically supported if no NVIDIA GPU is detected.

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/dictatly.git
cd dictatly
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

> **NVIDIA CUDA Note:** If using an NVIDIA GPU, ensure the CUDA 12 PyTorch/CTranslate2 dependencies are installed. Faster-Whisper automatically utilizes CUDA when available.

### 3. Launch Dictatly

- **Run in Background (System Tray):**
  Double-click `run.bat` or run:
  ```bash
  python main.py
  ```
- **Open Settings:**
  Double-click `settings.bat` or run:
  ```bash
  python main.py --settings
  ```
- **Open History:**
  Double-click `history.bat` or run:
  ```bash
  python main.py --history
  ```

---

## 🏗️ Project Architecture

```
dictatly/
├── main.py                     # Application entry point & single-instance mutex
├── requirements.txt            # Python dependencies
├── run.bat                     # Background service launcher
├── settings.bat                # Settings window launcher
├── history.bat                 # History window launcher
├── resources/                  # High-DPI icons & assets
│   ├── app_icon.png            # 512x512 squircle icon
│   └── app_icon_64.png         # 64x64 window icon
├── src/
│   ├── app.py                  # Main coordinator & lifecycle manager
│   ├── config.py               # JSON settings manager (%APPDATA%/Dictatly)
│   ├── localization.py         # RU / EN internationalization dictionary
│   ├── core/
│   │   ├── audio.py            # PyAudio recording & RMS volume meter
│   │   ├── database.py         # SQLite storage for transcript history
│   │   ├── hotkey.py           # Win32 WH_KEYBOARD_LL low-level hook
│   │   ├── injector.py         # Thread-attached clipboard text injection
│   │   ├── security.py         # Windows DPAPI encryption for secrets
│   │   └── caret.py            # Windows active caret position locator
│   ├── engine/
│   │   ├── transcriber.py      # Faster-Whisper ASR engine (CUDA / CPU)
│   │   └── ai_cleaner.py       # OpenAI-compatible post-processing
│   └── ui/
│       ├── hud.py              # Floating glassmorphism capsule widget
│       ├── settings_window.py  # macOS Sequoia grouped settings panel
│       ├── history_window.py   # Quick history & batch processing window
│       └── tray.py             # Windows system tray integration
└── tests/
    ├── test_all.py             # Core component unit tests
    └── test_ui.py              # PySide6 headless UI tests
```

---

## 🔒 Security & Privacy

- **100% Local Processing by Default:** All audio processing and Whisper transcription are executed entirely on your local machine. No voice data or transcribed text is uploaded to any server.
- **DPAPI Key Storage:** If optional AI cleanup is enabled, API keys are encrypted at rest using the Windows Data Protection API (`CryptProtectData`), which ties the encryption keys to your Windows user login credentials.
- **Single-Instance Enforcement:** Protected by a global named Windows mutex to prevent conflicting audio hooks or duplicate processes.

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for details on setting up your development environment and running the test suite.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
