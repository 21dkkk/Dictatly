"""
Audio capture module using sounddevice (WASAPI / DirectSound / MME).
Records mono float32 audio with real-time RMS volume callbacks for the HUD.
Features dynamic native sample-rate probing, automated fallback resampling to 16 kHz,
and robust hardware device recovery.
"""

import time
import threading
from typing import Optional, List, Dict, Callable, Tuple
import numpy as np
import sounddevice as sd

TARGET_SAMPLE_RATE = 16000
CHANNELS = 1
MIN_CLIP_SECONDS = 0.25
MAX_RECORDING_SECONDS = 20 * 60  # 20 minutes

def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """
    Resamples float32 audio from orig_sr to target_sr using zero-dependency linear interpolation.
    Downmixes multi-channel input to mono 1D if necessary.
    Fast, reliable, and requires no external heavy libraries (scipy/librosa).
    """
    if audio is None or len(audio) == 0:
        return np.empty(0, dtype=np.float32)

    # Downmix multi-channel to mono 1D
    if audio.ndim > 1:
        if audio.shape[1] > 1:
            audio = np.mean(audio, axis=1).astype(np.float32)
        else:
            audio = audio.flatten().astype(np.float32)
    elif audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    if orig_sr == target_sr:
        return audio

    duration = len(audio) / float(orig_sr)
    num_target_samples = int(round(duration * target_sr))
    if num_target_samples <= 0:
        return np.empty(0, dtype=np.float32)
    orig_indices = np.linspace(0.0, len(audio) - 1.0, len(audio), dtype=np.float32)
    target_indices = np.linspace(0.0, len(audio) - 1.0, num_target_samples, dtype=np.float32)
    return np.interp(target_indices, orig_indices, audio).astype(np.float32)

class AudioRecorder:
    def __init__(self, device_index: Optional[int] = None, silence_timeout_seconds: float = 15.0, device_name: Optional[str] = None):
        self.device_index = device_index
        self.device_name = device_name
        self.is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._last_sound_time: float = 0.0
        self._current_sample_rate: int = TARGET_SAMPLE_RATE
        self.silence_timeout_seconds = silence_timeout_seconds
        self.on_volume_level: Optional[Callable[[float], None]] = None
        self.on_silence_timeout: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    @staticmethod
    def get_extra_settings(device_index: Optional[int] = None):
        """Return host-specific stream settings (e.g. WASAPI auto sample rate conversion)."""
        try:
            target_idx = device_index if device_index is not None else sd.default.device[0]
            if target_idx is not None and target_idx >= 0:
                dev_info = sd.query_devices(target_idx)
                hostapi_info = sd.query_hostapis(dev_info.get("hostapi", 0))
                if "wasapi" in hostapi_info.get("name", "").lower():
                    return sd.WasapiSettings(auto_convert=True)
        except Exception:
            pass
        return None

    @staticmethod
    def get_input_devices() -> List[Dict[str, any]]:
        """List available physical audio input devices without duplicates."""
        devices = []
        try:
            hostapis = sd.query_hostapis()

            # Prefer WASAPI on modern Windows (clean Unicode names, low latency, no virtual mappers)
            target_api = next(
                (h for h in hostapis if "wasapi" in h.get("name", "").lower() and any(
                    sd.query_devices(i).get("max_input_channels", 0) > 0 for i in h.get("devices", [])
                )),
                None
            )

            if not target_api:
                def_api_idx = getattr(sd.default, "hostapi", 0)
                if isinstance(def_api_idx, int) and 0 <= def_api_idx < len(hostapis):
                    target_api = hostapis[def_api_idx]
                elif hostapis:
                    target_api = hostapis[0]

            candidate_indices = target_api.get("devices", []) if target_api else range(len(sd.query_devices()))
            default_in = target_api.get("default_input_device", sd.default.device[0]) if target_api else sd.default.device[0]

            seen_names = set()
            ignored_substrings = (
                "sound mapper", "переназначение звуковых",
                "primary sound capture", "первичный драйвер записи"
            )

            for idx in candidate_indices:
                try:
                    dev = sd.query_devices(idx)
                except Exception:
                    continue

                if dev.get("max_input_channels", 0) <= 0:
                    continue

                name = dev.get("name", f"Device {idx}").strip()
                name_lower = name.lower()

                # Skip virtual redirectors
                if any(sub in name_lower for sub in ignored_substrings):
                    continue

                # Deduplicate by normalized name
                norm_key = name_lower.replace("\r", " ").replace("\n", " ").strip()
                if norm_key in seen_names:
                    continue
                seen_names.add(norm_key)

                devices.append({
                    "index": idx,
                    "name": name,
                    "hostapi": dev.get("hostapi", 0),
                    "default": idx == default_in
                })
        except Exception as e:
            print(f"[Audio] Error querying devices: {e}")
        return devices

    @staticmethod
    def find_device_by_name(device_name: str) -> Optional[int]:
        """Resolve current device index matching a saved device name."""
        if not device_name:
            return None
        target = device_name.strip().lower()
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    name = dev.get("name", "").strip().lower()
                    if target == name or target in name or name in target:
                        return idx
        except Exception:
            pass
        return None

    def set_device(self, device_index: Optional[int], device_name: Optional[str] = None):
        """Set the input device index and optional persistent name."""
        self.device_index = device_index
        self.device_name = device_name

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Low-latency audio callback from PortAudio."""
        if not self.is_recording:
            return

        # If device delivers stereo/multi-channel, collapse to mono
        if indata.ndim > 1 and indata.shape[1] > 1:
            mono_data = np.mean(indata, axis=1, keepdims=True).astype(np.float32)
        else:
            mono_data = indata.astype(np.float32)

        with self._lock:
            self._frames.append(mono_data.copy())

        # Calculate volume level (RMS normalised 0.0 .. 1.0)
        rms = float(np.sqrt(np.mean(np.square(mono_data))))
        norm_vol = min(1.0, rms * 15.0)

        now = time.time()
        if norm_vol > 0.04:
            self._last_sound_time = now

        if self.on_volume_level:
            self.on_volume_level(norm_vol)

        # Check silence timeout
        if (
            self.silence_timeout_seconds > 0
            and (now - self._start_time) > 2.0
            and (now - self._last_sound_time) >= self.silence_timeout_seconds
        ):
            if self.on_silence_timeout:
                cb = self.on_silence_timeout
                self.on_silence_timeout = None
                threading.Thread(target=cb, daemon=True).start()

    def _try_open_stream(self, device_idx: Optional[int]) -> Optional[Tuple[sd.InputStream, int]]:
        """
        Attempts to open an InputStream on device_idx.
        First tries 16000 Hz. If rejected by hardware, probes native sample rate (48000/44100 Hz).
        """
        extra_settings = self.get_extra_settings(device_idx)

        # Determine native rate of target device
        native_sr = 48000
        if device_idx is not None:
            try:
                dev_info = sd.query_devices(device_idx)
                native_sr = int(round(dev_info.get("default_samplerate", 48000)))
            except Exception:
                native_sr = 48000

        # Try list of sample rates: 16000 first, then native rate, then common fallbacks
        candidate_rates = [TARGET_SAMPLE_RATE]
        if native_sr not in candidate_rates and native_sr > 0:
            candidate_rates.append(native_sr)
        for fallback_rate in [48000, 44100]:
            if fallback_rate not in candidate_rates:
                candidate_rates.append(fallback_rate)

        for sr in candidate_rates:
            for ch in [1, 2]:
                try:
                    stream = sd.InputStream(
                        samplerate=sr,
                        channels=ch,
                        dtype="float32",
                        device=device_idx,
                        blocksize=512 if sr == TARGET_SAMPLE_RATE else 1024,
                        callback=self._audio_callback,
                        extra_settings=extra_settings
                    )
                    stream.start()
                    return stream, sr
                except Exception:
                    continue
        return None

    def start(self) -> bool:
        """
        Start capturing audio with cascading hardware fallback:
        1. Configured device_index
        2. Configured device_name (if index changed)
        3. System default input device (None)
        4. First working physical input device
        """
        if self.is_recording:
            return False

        with self._lock:
            self._frames.clear()
            self.is_recording = True
            self._start_time = time.time()
            self._last_sound_time = self._start_time

        # Candidate 1: Specified device index
        stream_res = None
        target_idx = self.device_index
        if target_idx is not None:
            stream_res = self._try_open_stream(target_idx)

        # Candidate 2: Match by persistent device name if index failed
        if stream_res is None and self.device_name:
            resolved_idx = self.find_device_by_name(self.device_name)
            if resolved_idx is not None and resolved_idx != target_idx:
                stream_res = self._try_open_stream(resolved_idx)

        # Candidate 3: System default input device
        if stream_res is None:
            stream_res = self._try_open_stream(None)

        # Candidate 4: Iterate all input devices
        if stream_res is None:
            try:
                for dev_info_item in self.get_input_devices():
                    idx = dev_info_item["index"]
                    stream_res = self._try_open_stream(idx)
                    if stream_res is not None:
                        break
            except Exception:
                pass

        if stream_res is not None:
            self._stream, self._current_sample_rate = stream_res
            return True

        self.is_recording = False
        err_msg = "No available or working audio input device detected."
        print(f"[Audio] {err_msg}")
        if self.on_error:
            try:
                self.on_error(err_msg)
            except Exception:
                pass
        return False

    def stop(self) -> Optional[np.ndarray]:
        """
        Stop capturing and return 1D float32 numpy array of audio samples normalized to 16 kHz.
        """
        if not self.is_recording:
            return None

        self.is_recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            if not self._frames:
                return None
            audio = np.concatenate(self._frames, axis=0).flatten()
            self._frames.clear()

        # Resample to 16 kHz if recorded at native 44.1/48 kHz
        sample_rate = self._current_sample_rate
        if sample_rate != TARGET_SAMPLE_RATE and len(audio) > 0:
            audio = resample_audio(audio, orig_sr=sample_rate, target_sr=TARGET_SAMPLE_RATE)

        duration = len(audio) / float(TARGET_SAMPLE_RATE)
        if duration < MIN_CLIP_SECONDS:
            return None

        return audio

    @property
    def recording_duration(self) -> float:
        """Return current recording duration in seconds."""
        if not self.is_recording:
            return 0.0
        return time.time() - self._start_time
