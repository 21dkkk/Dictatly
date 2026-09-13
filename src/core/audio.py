"""
Audio capture module using sounddevice (WASAPI / DirectSound).
Records 16 kHz mono float32 audio with real-time RMS volume callbacks for the HUD.
"""

import time
import threading
from typing import Optional, List, Dict, Callable
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
MIN_CLIP_SECONDS = 0.25
MAX_RECORDING_SECONDS = 20 * 60  # 20 minutes

class AudioRecorder:
    def __init__(self, device_index: Optional[int] = None, silence_timeout_seconds: float = 15.0):
        self.device_index = device_index
        self.is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._last_sound_time: float = 0.0
        self.silence_timeout_seconds = silence_timeout_seconds
        self.on_volume_level: Optional[Callable[[float], None]] = None
        self.on_silence_timeout: Optional[Callable[[], None]] = None

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
                dev = sd.query_devices(idx)
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

    def set_device(self, device_index: Optional[int]):
        """Set the input device index (None = system default)."""
        self.device_index = device_index

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Low-latency audio callback from PortAudio/WASAPI."""
        if status:
            pass  # Overflow or underflow
        
        if not self.is_recording:
            return

        with self._lock:
            self._frames.append(indata.copy())

        # Calculate volume level (RMS normalised 0.0 .. 1.0)
        rms = float(np.sqrt(np.mean(np.square(indata))))
        norm_vol = min(1.0, rms * 15.0)

        now = time.time()
        if norm_vol > 0.06:
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

    def start(self) -> bool:
        """Start capturing audio."""
        if self.is_recording:
            return False

        with self._lock:
            self._frames.clear()
            self.is_recording = True
            self._start_time = time.time()
            self._last_sound_time = self._start_time

        try:
            extra_settings = self.get_extra_settings(self.device_index)
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=self.device_index,
                blocksize=512,
                callback=self._audio_callback,
                extra_settings=extra_settings
            )
            self._stream.start()
            return True
        except Exception as e:
            print(f"[Audio] Error starting stream: {e}")
            self.is_recording = False
            return False

    def stop(self) -> Optional[np.ndarray]:
        """Stop capturing and return 1D float32 numpy array of audio samples."""
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

        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_CLIP_SECONDS:
            return None

        return audio

    @property
    def recording_duration(self) -> float:
        """Return current recording duration in seconds."""
        if not self.is_recording:
            return 0.0
        return time.time() - self._start_time
