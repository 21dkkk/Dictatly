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
        candidate_roots = [
            Path(sys.prefix) / "Lib" / "site-packages",
            Path(sys.base_prefix) / "Lib" / "site-packages",
            Path(r"F:\Coding\Dictatly\venv\Lib\site-packages"),
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidate_roots.append(Path(local_app) / "Programs" / "Python" / "Python312" / "Lib" / "site-packages")
            candidate_roots.append(Path(local_app) / "Dictatly" / "venv" / "Lib" / "site-packages")

        try:
            import site
            for sp in site.getsitepackages():
                candidate_roots.append(Path(sp))
        except Exception:
            pass

        for root in candidate_roots:
            for sub in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin", "ctranslate2"]:
                p = root / sub
                if p.exists():
                    try:
                        os.add_dll_directory(str(p))
                    except Exception:
                        pass
                    if str(p) not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")

setup_cuda_dll_path()

def get_model_cache_dir(model_size: str = "") -> str:
    """Return model cache dir, checking bundled models alongside application and cached models first."""
    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
    bundled = base_dir / "models"
    if bundled.exists():
        if model_size:
            safe = model_size.replace("/", "--").replace(" ", "-")
            if any(bundled.glob(f"*{safe}*")):
                return str(bundled)
        elif any(bundled.iterdir()):
            return str(bundled)

    # Search candidates where model might already be cached
    raw_candidates = [
        Path.home() / ".cache" / "dictatly" / "models",
        Path.home() / ".cache" / "superdictate" / "models",
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    user_prof = os.environ.get("USERPROFILE")
    if user_prof:
        up = Path(user_prof)
        raw_candidates.extend([
            up / ".cache" / "dictatly" / "models",
            up / ".cache" / "superdictate" / "models",
            up / ".cache" / "huggingface" / "hub",
        ])

    candidates = []
    seen = set()
    for c in raw_candidates:
        try:
            resolved = c.resolve()
            if resolved not in seen:
                seen.add(resolved)
                candidates.append(c)
        except Exception:
            candidates.append(c)

    if model_size:
        patterns = [model_size.replace("/", "--").replace(" ", "-")]
        try:
            from faster_whisper.utils import _MODELS
            if model_size in _MODELS:
                patterns.append(_MODELS[model_size].replace("/", "--").replace(" ", "-"))
        except Exception:
            pass

        for cand in candidates:
            if cand.exists():
                for pat in patterns:
                    try:
                        for entry in cand.glob(f"*{pat}*"):
                            if entry.is_dir():
                                # Check that the folder contains actual model weights (.bin or .safetensors)
                                if any(entry.rglob("*.bin")) or any(entry.rglob("*.safetensors")):
                                    return str(cand)
                    except Exception:
                        pass

    primary = Path.home() / ".cache" / "dictatly" / "models"
    primary.mkdir(parents=True, exist_ok=True)
    return str(primary)

def resolve_local_model_path(model_size: str) -> Optional[str]:
    """Resolve direct snapshot directory containing model.bin if already cached locally."""
    cache_dir = get_model_cache_dir(model_size)
    p_cache = Path(cache_dir)
    if not p_cache.exists():
        return None

    patterns = [model_size.replace("/", "--").replace(" ", "-")]
    try:
        from faster_whisper.utils import _MODELS
        if model_size in _MODELS:
            patterns.append(_MODELS[model_size].replace("/", "--").replace(" ", "-"))
    except Exception:
        pass

    for pat in patterns:
        for entry in p_cache.glob(f"*{pat}*"):
            if entry.is_dir():
                if (entry / "model.bin").exists():
                    return str(entry)
                snapshots = entry / "snapshots"
                if snapshots.exists() and snapshots.is_dir():
                    for snap in snapshots.iterdir():
                        if snap.is_dir() and (snap / "model.bin").exists():
                            return str(snap)
    return None

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
                            import ctypes
                            try:
                                ctypes.CDLL("cublas64_12.dll")
                                ctypes.CDLL("cublasLt64_12.dll")
                                use_cuda = True
                            except Exception:
                                print("[ASR] cublas64_12.dll / cublasLt64_12.dll not loadable, falling back to CPU.")
                                use_cuda = False
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
                
                # Check for direct local directory to avoid online checks
                direct_path = resolve_local_model_path(self.model_size)
                model_target = direct_path if direct_path else self.model_size
                cache_root = None if direct_path else get_model_cache_dir(self.model_size)

                self._model = WhisperModel(
                    model_target,
                    device=self.active_device,
                    compute_type=self.active_compute_type,
                    cpu_threads=threads,
                    download_root=cache_root
                )
                print(f"[ASR] Model loaded in {time.time() - start_t:.2f}s.")
            except Exception as e:
                print(f"[ASR] Failed to load on {self.active_device}: {e}. Falling back to CPU.")
                try:
                    from faster_whisper import WhisperModel
                    self.active_device = "cpu"
                    self.active_compute_type = "int8"
                    threads = min(4, os.cpu_count() or 4)
                    direct_path = resolve_local_model_path(self.model_size)
                    model_target = direct_path if direct_path else self.model_size
                    cache_root = None if direct_path else get_model_cache_dir(self.model_size)

                    self._model = WhisperModel(
                        model_target,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=threads,
                        download_root=cache_root
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
        if audio is None or len(audio) == 0:
            return ""

        # Check RMS energy to avoid hallucinating on pure background silence
        rms_energy = float(np.sqrt(np.mean(np.square(audio))))
        if rms_energy < 0.002:
            return ""

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

            # Fallback only if there is audible voice energy but VAD was overly strict
            if not result and rms_energy >= 0.004:
                segments, info = self._model.transcribe(
                    audio,
                    language=lang,
                    beam_size=3,
                    vad_filter=False,
                    condition_on_previous_text=False
                )
                collected_text = [seg.text.strip() for seg in segments]
                result = " ".join(collected_text).strip()

            # Clean out pure punctuation / whisper hallucination artifacts
            if result:
                alphanumeric_chars = [c for c in result if c.isalnum()]
                if not alphanumeric_chars:
                    return ""
                lower_trimmed = result.strip().lower()
                known_hallucinations = {
                    "продолжение следует", "редактор субтитров", "субтитры сделал",
                    "субтитры", "спасибо за просмотр", "thank you for watching",
                    "subtitles by", "translated by", "subscribe", "подпишитесь на канал"
                }
                if lower_trimmed in known_hallucinations:
                    return ""

            return result
        except Exception as e:
            print(f"[ASR] Transcription error on {self.active_device}: {e}")
            if self.active_device == "cuda":
                print("[ASR] Automatic fallback: retrying transcription on CPU int8...")
                self._model = None
                try:
                    self.active_device = "cpu"
                    self.active_compute_type = "int8"
                    threads = min(4, os.cpu_count() or 4)
                    from faster_whisper import WhisperModel
                    direct_path = resolve_local_model_path(self.model_size)
                    model_target = direct_path if direct_path else self.model_size
                    cache_root = None if direct_path else get_model_cache_dir(self.model_size)

                    self._model = WhisperModel(
                        model_target,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=threads,
                        download_root=cache_root
                    )
                    segments, info = self._model.transcribe(
                        audio,
                        language=lang,
                        beam_size=3,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500),
                        condition_on_previous_text=False
                    )
                    collected = [s.text.strip() for s in segments]
                    return " ".join(collected).strip()
                except Exception as ex:
                    print(f"[ASR] CPU fallback failed: {ex}")
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
