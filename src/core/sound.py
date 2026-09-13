"""
Audio feedback cues for Dictatly using native Windows multimedia audio.
Plays subtle, muffled acoustic keypress clicks on dictation start and stop.
"""

import sys
import io
import wave
import math
import struct
import threading
from typing import Optional

_START_WAV: Optional[bytes] = None
_STOP_WAV: Optional[bytes] = None

def _generate_muffled_key_click(base_freq: float, duration_ms: int = 28, volume: float = 0.08) -> bytes:
    """
    Synthesize a warm, dampened mechanical keypress thud.
    Uses exponential decay and pitch envelope to mimic an acoustic tactile switch.
    """
    sample_rate = 44100
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        decay_rate = 140.0
        for i in range(n_samples):
            t = i / sample_rate
            # 2ms smooth fade-in prevents sharp transient click
            if t < 0.002:
                envelope = t / 0.002
            else:
                envelope = math.exp(-(t - 0.002) * decay_rate)

            # Natural pitch dip of a mechanical switch bottoming out
            pitch = base_freq * (1.0 + 0.35 * math.exp(-t * 220.0))
            val = math.sin(2.0 * math.pi * pitch * t)
            # Soft harmonic for acoustic body
            val += 0.25 * math.sin(4.0 * math.pi * pitch * t)

            sample_val = int(val * envelope * volume * 32767.0)
            sample_val = max(-32767, min(32767, sample_val))
            frames.extend(struct.pack("<h", sample_val))
        wav.writeframes(frames)
    return buffer.getvalue()

def _init_audio_cues():
    global _START_WAV, _STOP_WAV
    if _START_WAV is None:
        try:
            # Subtle, soft tactile press (~240 Hz base, decaying in 28ms)
            _START_WAV = _generate_muffled_key_click(base_freq=240.0, duration_ms=28, volume=0.08)
            # Deep, gentle release thud (~170 Hz base, decaying in 26ms)
            _STOP_WAV = _generate_muffled_key_click(base_freq=170.0, duration_ms=26, volume=0.06)
        except Exception:
            _START_WAV = b""
            _STOP_WAV = b""

def _play_wav_worker(wav_data: bytes):
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(wav_data, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
    except Exception:
        pass

def play_audio_cue(event_type: str, enabled: bool = True) -> bool:
    """
    Play non-blocking subtle, muffled acoustic audio cue.
    event_type: 'start' (subtle tactile click) or 'stop' (deep gentle release).
    Returns True if sound was queued, False otherwise.
    """
    if not enabled or sys.platform != "win32":
        return False

    _init_audio_cues()

    wav_data = _START_WAV if event_type == "start" else (_STOP_WAV if event_type == "stop" else None)
    if not wav_data:
        return False

    threading.Thread(target=_play_wav_worker, args=(wav_data,), daemon=True).start()
    return True
