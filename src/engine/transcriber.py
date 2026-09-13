"""
Speech-to-Text Transcription Engine using Faster-Whisper.
Supports CUDA acceleration on NVIDIA RTX GPUs and CPU int8 fallback.
Handles both real-time mic buffers and batch file transcription.
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
import numpy as np

# Ensure NVIDIA DLL directories are discovered on Windows if installed via pip
def setup_cuda_dll_path():
    if sys.platform == "win32":
        site_packages = Path(sys.prefix) / "Lib" / "site-packages"
        for sub in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin"]:
            p = site_packages / sub
            if p.exists():
                try:
                    os.add_dll_directory(str(p))
                except Exception:
                    pass
                # Also append to PATH
                if str(p) not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")

setup_cuda_dll_path()

class SpeechTranscriber:
    def __init__(self, model_size: str = "large-v3-turbo", device_pref: str = "auto"):
        self.model_size = model_size
        self.device_pref = device_pref
        self._model = None
        self._lock = threading.Lock()
        self.active_device = "cpu"
        self.active_compute_type = "int8"
        self.is_loading = False

    def load_model(self):
        """Loads or reloads the Whisper model with appropriate compute device."""
        with self._lock:
            if self._model is not None:
                return

            self.is_loading = True
            try:
                import ctranslate2
                from faster_whisper import WhisperModel

                # Determine device
                use_cuda = False
                if self.device_pref in ("auto", "cuda"):
                    try:
                        supported = ctranslate2.get_supported_compute_types("cuda")
                        if supported and len(supported) > 0:
                            use_cuda = True
                    except Exception:
                        use_cuda = False

                if use_cuda:
                    self.active_device = "cuda"
                    self.active_compute_type = "float16"
                else:
                    self.active_device = "cpu"
                    self.active_compute_type = "int8"

                print(f"[ASR] Loading WhisperModel({self.model_size}) on {self.active_device} ({self.active_compute_type})...")
                start_t = time.time()
                threads = min(4, os.cpu_count() or 4)
                self._model = WhisperModel(
                    self.model_size,
                    device=self.active_device,
                    compute_type=self.active_compute_type,
                    cpu_threads=threads,
                    download_root=str(Path.home() / ".cache" / "superdictate" / "models")
                )
                print(f"[ASR] Model loaded in {time.time() - start_t:.2f}s.")
            except Exception as e:
                print(f"[ASR] Failed to load on {self.active_device}: {e}. Falling back to CPU.")
                try:
                    from faster_whisper import WhisperModel
                    self.active_device = "cpu"
                    self.active_compute_type = "int8"
                    threads = min(4, os.cpu_count() or 4)
                    self._model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=threads,
                        download_root=str(Path.home() / ".cache" / "superdictate" / "models")
                    )
                except Exception as ex:
                    print(f"[ASR] Fatal error loading model: {ex}")
            finally:
                self.is_loading = False

    def transcribe_audio(self, audio: np.ndarray, language: Optional[str] = None) -> str:
        """
        Transcribes 16kHz float32 audio numpy array.
        language: None/'auto', or 'ru', 'en'.
        """
        if self._model is None:
            self.load_model()
            
        if self._model is None:
            return ""

        lang = None if (not language or language == "auto") else language

        try:
            segments, info = self._model.transcribe(
                audio,
                language=lang,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False
            )
            
            collected_text = []
            for seg in segments:
                collected_text.append(seg.text.strip())

            result = " ".join(collected_text).strip()

            # Fallback if VAD was too aggressive on quiet voice
            if not result:
                segments, info = self._model.transcribe(
                    audio,
                    language=lang,
                    beam_size=3,
                    vad_filter=False,
                    condition_on_previous_text=False
                )
                collected_text = [seg.text.strip() for seg in segments]
                result = " ".join(collected_text).strip()

            return result
        except Exception as e:
            print(f"[ASR] Transcription error: {e}")
            return ""

    def transcribe_file(self, file_path: str, language: Optional[str] = None,
                        on_progress: Optional[Callable[[float], None]] = None) -> str:
        """
        Transcribe an audio file from disk (.mp3, .wav, .m4a, etc.).
        """
        if self._model is None:
            self.load_model()
            
        if self._model is None:
            return ""

        lang = None if (not language or language == "auto") else language

        try:
            segments, info = self._model.transcribe(
                file_path,
                language=lang,
                beam_size=5,
                vad_filter=True
            )
            
            total_duration = info.duration if info and info.duration else 1.0
            collected = []
            
            for seg in segments:
                collected.append(seg.text.strip())
                if on_progress:
                    prog = min(1.0, seg.end / total_duration)
                    on_progress(prog)

            return " ".join(collected).strip()
        except Exception as e:
            print(f"[ASR] File transcription error: {e}")
            return ""
