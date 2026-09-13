<p align="center">
  <img src="resources/app_icon.png" width="128" height="128" alt="Dictatly Icon" />
</p>

<h1 align="center">Dictatly</h1>

<p align="center">
  <b>Fast, private, local speech-to-text dictation and transcription utility for Windows 10 and 11.</b>
</p>

<p align="center">
  <a href="https://github.com/21dkkk/Dictatly/actions/workflows/test.yml">
    <img src="https://github.com/21dkkk/Dictatly/actions/workflows/test.yml/badge.svg" alt="CI Status" />
  </a>
  <a href="https://microsoft.com/windows">
    <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0078D4?logo=windows&logoColor=white" alt="Platform" />
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python" />
  </a>
  <a href="https://github.com/SYSTRAN/faster-whisper">
    <img src="https://img.shields.io/badge/ASR-Faster--Whisper%20(CUDA%20FP16)-76B900?logo=nvidia&logoColor=white" alt="Engine" />
  </a>
  <a href="https://qt.io">
    <img src="https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52?logo=qt&logoColor=white" alt="UI" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
  </a>
</p>

---

## 🎙️ Overview

**Dictatly** is a lightweight, zero-latency desktop dictation tool designed specifically for Windows. It captures speech from your microphone, transcribes it locally using hardware-accelerated Whisper models, and instantly injects the recognized text directly into whichever application you are typing in.

All audio processing happens **100% on your machine**. Your voice and data never leave your computer unless you explicitly opt into optional cloud AI post-processing.

```
                  ┌───────────────────────────────┐
                  │   🟠  ılı  [ ● ● ● ● ]        │  ← Floating Glass Capsule
                  └───────────────┬───────────────┘
                                  ▼
           [ Active Caret in VS Code / Telegram / Browser ]
```

---

## ✨ Features

- **⚡ Local GPU & CPU Acceleration:** Powered by [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (`large-v3-turbo`, `small`, or `base`). Uses NVIDIA CUDA FP16 for near-instant inference, with automatic multi-threaded CPU fallback (`int8`).
- **📍 Caret-Anchored Capsule HUD:** Floating dark glass capsule widget centered dynamically above your typing cursor (`GetGUIThreadInfo`). Utilizes Win32 `WS_EX_NOACTIVATE` so it **never steals keyboard focus** from your active window.
- **⌨️ Low-Level Win32 Keyboard Hook:** Native `WH_KEYBOARD_LL` hook running in a dedicated message loop. Correctly identifies physical Left vs. Right modifiers (`Right Ctrl`, `Right Alt / AltGr`, `Right Shift`) and supports both **Toggle** and **Push-to-Talk** modes.
- **🎯 Reliable Text Injection:** Restores target window focus, synchronizes with the Windows clipboard, and simulates `Ctrl+V` key events using hardware scan codes and thread input attachment (`AttachThreadInput`).
- **🗂️ Transcription History & Batch Drop Zone:** SQLite database with search and pagination. Drag-and-drop any audio files (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`) directly into the history window for automatic batch transcription and export to `.txt`.
- **🔤 Smart Punctuation & Custom Vocabulary:** Automatic sentence capitalization and punctuation spacing while protecting decimal numbers (`3.14`, `1,5`), clock times (`12:30`), and domain names (`google.com`). User-defined replacement dictionary for domain terms (e.g. `пайтон` → `Python`, `гитхаб` → `GitHub`).
- **🔒 Privacy First & DPAPI Security:** API keys used for optional AI cleanup (Groq, OpenAI, Ollama) are encrypted locally using the Windows Data Protection API (`CryptProtectData`), tied strictly to your Windows user account.
- **🔇 Audio Cues & Gaming Pause:** Soft, muffled acoustic feedback on start/stop. System tray option to pause hotkeys temporarily during gaming sessions or voice calls.
- **🌍 Bilingual Interface:** Complete English and Russian support across all dialogs, settings, menus, and system notifications.

---

## ⌨️ Default Keyboard Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Right Ctrl</kbd> | **Toggle Dictation** | Press once to start recording; press again to transcribe and insert text at active cursor. |
| <kbd>Right Shift</kbd> + <kbd>Right Ctrl</kbd> | **Alternative Finish** | Finishes recording and inverts the configured "Enter after insert" setting. |
| <kbd>Right Alt</kbd> + <kbd>Right Ctrl</kbd> | **Quick History** | Opens transcript history and batch audio drop zone. |
| <kbd>Esc</kbd> | **Cancel Dictation** | Immediately discards the current recording without pasting text. |

> [!TIP]
> All hotkeys can be rebound to any single key or multi-key chord in the **Settings** window.

---

## 💻 System Requirements

- **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python:** 3.10, 3.11, or 3.12 (64-bit).
- **Audio:** Any functional microphone or audio input device (WASAPI supported).
- **GPU (Recommended):** NVIDIA GPU with CUDA 12 for real-time FP16 speech recognition.
- **CPU (Fallback):** Multi-core CPU with int8 quantization works out of the box if an NVIDIA GPU is not present.

---

## 🚀 Quick Start Guide

### 1. Clone the Repository

```powershell
git clone https://github.com/21dkkk/Dictatly.git
cd Dictatly
```

### 2. Set Up Python Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Launching Dictatly

- **Silent Launch (No Console Window):**
  Double-click `Dictatly.vbs` or launch via the generated Desktop shortcut.
- **Terminal Launch:**
  ```powershell
  .\run.bat
  # or: python main.py
  ```
- **Open Settings Directly:**
  ```powershell
  .\settings.bat
  # or: python main.py --settings
  ```
- **Open History Directly:**
  ```powershell
  .\history.bat
  # or: python main.py --history
  ```

---

## 📁 Repository Structure

```
Dictatly/
├── main.py                     # Application entry point & single-instance mutex
├── Dictatly.vbs                # Silent native Windows launcher (no console window)
├── requirements.txt            # Python dependencies (PySide6, faster-whisper, sounddevice)
├── run.bat                     # Terminal launcher
├── settings.bat                # Direct settings window launcher
├── history.bat                 # Direct history window launcher
├── resources/                  # High-resolution vector icons and assets
│   ├── app_icon.ico            # Multi-resolution Windows icon (256×256)
│   ├── app_icon.png            # 512×512 icon
│   └── app_icon_64.png         # 64×64 icon
├── scripts/
│   └── build_launcher.py       # C# launcher compiler (Dictatly.exe)
├── src/
│   ├── app.py                  # Main coordinator and Qt lifecycle manager
│   ├── config.py               # JSON settings manager (%APPDATA%/Dictatly)
│   ├── localization.py         # RU / EN localization dictionary
│   ├── core/
│   │   ├── audio.py            # WASAPI audio capture and RMS volume stream
│   │   ├── autostart.py        # Windows Startup shortcut and registry manager
│   │   ├── database.py         # Thread-safe SQLite history storage (WAL mode)
│   │   ├── hotkey.py           # Win32 WH_KEYBOARD_LL low-level hook manager
│   │   ├── injector.py         # Thread-attached clipboard text injector
│   │   ├── security.py         # Windows DPAPI encryption (CryptProtectData)
│   │   ├── sound.py            # Muffled mechanical key click audio cues
│   │   ├── text_postprocess.py # Smart punctuation & custom vocabulary engine
│   │   └── caret.py            # Windows active caret position locator
│   ├── engine/
│   │   ├── transcriber.py      # Faster-Whisper ASR engine (CUDA / CPU)
│   │   └── ai_cleaner.py       # OpenAI-compatible text post-processing
│   └── ui/
│       ├── hud.py              # Floating capsule HUD widget (multi-monitor aware)
│       ├── settings_window.py  # Settings & Control Panel (theme, audio, hotkeys)
│       ├── history_window.py   # History, productivity stats & batch drop zone
│       ├── onboarding_dialog.py# First-run welcome and quick setup dialog
│       └── tray.py             # System tray icon and context menu
└── tests/
    ├── test_all.py             # Core component, security, and concurrency tests
    └── test_ui.py              # PySide6 headless UI tests
```

---

## 🧪 Testing

Run the automated test suite to verify all modules, concurrency, and UI components:

```powershell
.\venv\Scripts\python.exe -m unittest discover tests -v
```

---

## 🛡️ Security & Privacy

1. **Local Processing:** Audio captured by Dictatly is transcribed locally in system RAM and GPU VRAM. It is never written to temporary files or sent across the internet.
2. **DPAPI Key Storage:** Any API key used for optional AI cleanup is encrypted via Windows DPAPI (`CryptProtectData`), ensuring it cannot be decrypted by other user accounts or transferred to other machines.
3. **Single Instance Guarantee:** Enforced via a named Win32 global mutex (`Global\Dictatly_SingleInstance_Mutex`).

---

## 👤 Author

Created and maintained by **[21dkkk](https://github.com/21dkkk)**.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
