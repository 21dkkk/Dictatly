# Contributing to Dictatly

Guidelines for development, architecture, testing, and submitting contributions.

---

## Development Setup

### Prerequisites

- **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python:** 3.10, 3.11, or 3.12 (64-bit).
- **Hardware:** Microphone input. NVIDIA GPU with CUDA 12 support recommended for FP16 inference; multi-threaded CPU fallback is supported.

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/21dkkk/Dictatly.git
   cd Dictatly
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Launch the application in development:
   ```bash
   # Run main tray application
   python main.py

   # Open Settings directly
   python main.py --settings

   # Open History directly
   python main.py --history
   ```

---

## Testing

Always verify that automated unit and UI tests pass before submitting changes:

```bash
# Run core component tests
python tests/test_all.py

# Run UI tests (runs headless via offscreen QPA)
python tests/test_ui.py
```

---

## Architecture & Code Guidelines

### Modular Separation

- **`src/core/`**: Platform-level integrations (Win32 low-level hooks, caret tracking, text injection via clipboard simulation, audio stream capture, SQLite history database, DPAPI encryption). Keep UI-agnostic.
- **`src/engine/`**: Speech recognition (`faster-whisper`) and optional text post-processing (`httpx`).
- **`src/ui/`**: PySide6 widgets (floating HUD, settings panel, quick history, system tray).
- **`src/localization.py`**: Dictionary for bilingual (RU / EN) string lookup.

### Thread Safety & Concurrency

- All Qt widget manipulations and UI updates must execute on the main thread.
- Audio streaming, model loading, transcription inference, and HTTP requests must run on worker threads and pass data back to UI components using Qt signals or thread-safe callbacks.
- When stopping worker threads or Windows hook message loops, join threads with explicit timeouts to prevent race conditions during service restarts or shutdowns.

### Win32 API Practices

- When defining Win32 API functions via `ctypes`, declare explicit `argtypes` and `restype` signatures compatible with 64-bit Windows pointers (`DWORD`, `WPARAM`, `LPARAM`, `c_ulonglong`).
- Ensure all allocated Windows resources (`GlobalAlloc`, `HHOOK`, mutexes) are freed or unhooked in `finally` blocks or explicit teardown methods.

---

## Pull Request Process

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/issue-description
   ```
2. Make atomic, well-tested commits.
3. Verify that all tests pass (`test_all.py` and `test_ui.py`).
4. Push to your fork and submit a Pull Request describing the problem solved and the approach taken.

---

## License

By contributing to Dictatly, you agree that your contributions will be licensed under the [MIT License](LICENSE).
