# Contributing to Dictatly

Thank you for your interest in contributing to **Dictatly**! We welcome bug reports, feature suggestions, documentation improvements, and pull requests.

---

## 🛠️ Development Setup

### Prerequisites
- **OS:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python 3.10, 3.11, or 3.12 (64-bit).
- **GPU (Recommended):** NVIDIA GPU with CUDA 12 support (RTX 30-series or newer recommended for real-time FP16 inference). CPU mode with int8 quantization is also supported.

### Getting Started

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/your-username/dictatly.git
   cd dictatly
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run the Application:**
   ```bash
   # Background service
   run.bat

   # Open Settings Panel
   settings.bat

   # Open History Window
   history.bat
   ```

---

## 🧪 Running Tests

Always verify that automated unit tests and UI tests pass before submitting a pull request:

```bash
# Run core test suite
python tests/test_all.py

# Run UI test suite
python tests/test_ui.py
```

---

## 📐 Design & Code Guidelines

- **Architecture:** Maintain clear modular boundaries between `core/` (Win32 APIs, audio, database, hotkeys), `engine/` (Whisper ASR, LLM cleaner), and `ui/` (PySide6 widgets).
- **UI/UX Philosophy:** Follow Apple macOS Sequoia design guidelines:
  - Warm neutral dark graphite (`#1E1E20`) and cards (`#28282A`).
  - Subtle borders (`rgba(255, 255, 255, 0.08)`).
  - 10px card radius, tactile 5px keycap styling.
  - Native system typography (`-apple-system`, `SF Pro Display`, `Segoe UI Variable`).
  - Zero AI-slop: avoid garish neon glows, oversized badges, and unnecessary boilerplate.
- **Thread Safety:** Qt GUI operations must execute on the Qt main thread. Background audio capture, Whisper transcription, and network calls must run in worker threads using Qt signals.

---

## 📝 Submitting Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "feat(injector): add thread input attachment for foreground recovery"
   ```
3. Push to your fork and submit a Pull Request.

---

## 📄 License
By contributing to Dictatly, you agree that your contributions will be licensed under the [MIT License](LICENSE).
