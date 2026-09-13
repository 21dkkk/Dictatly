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
    def __init__(self, device_index: Optional[int] = None):
        self.device_index = device_index
        self.is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self.on_volume_level: Optional[Callable[[float], None]] = None

    @staticmethod
    def get_input_devices() -> List[Dict[str, any]]:
        """List all available audio input devices."""
        devices = []
        try:
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Device {idx}"),
                        "hostapi": dev.get("hostapi", 0),
                        "default": idx == sd.default.device[0]
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
        if self.on_volume_level:
            rms = float(np.sqrt(np.mean(np.square(indata))))
            # Scale rms logarithmically/smoothly
            norm_vol = min(1.0, rms * 15.0)
            self.on_volume_level(norm_vol)

    def start(self) -> bool:
        """Start capturing audio."""
        if self.is_recording:
            return False

        with self._lock:
            self._frames.clear()
            self.is_recording = True
            self._start_time = time.time()

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=self.device_index,
                blocksize=512,
                callback=self._audio_callback
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
