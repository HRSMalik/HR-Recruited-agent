"""Standalone live-mic test for faster-whisper, independent of the LiveKit pipeline.

Install:
    pip install faster-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple

Run:
    python test_faster_whisper_live.py

Speak into your mic; each time you pause, the segment gets transcribed and printed.
Ctrl+C to stop.
"""
import queue
import sys

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
BLOCK_MS = 30
SILENCE_RMS_THRESHOLD = 0.01
SILENCE_BLOCKS_TO_CUT = 20  # ~600ms of silence ends an utterance
MIN_SPEECH_BLOCKS = 8  # ~240ms minimum before a segment is worth transcribing

_audio_q: "queue.Queue[np.ndarray]" = queue.Queue()


def _on_audio(indata, frames, time_info, status) -> None:
    if status:
        print(f"[mic] {status}", file=sys.stderr)
    _audio_q.put(indata[:, 0].copy())


def _record_utterances():
    buffer: list[np.ndarray] = []
    silence_run = 0
    speaking = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=int(SAMPLE_RATE * BLOCK_MS / 1000),
        callback=_on_audio,
    ):
        print("Listening... speak now (Ctrl+C to stop)", file=sys.stderr)
        while True:
            block = _audio_q.get()
            rms = float(np.sqrt(np.mean(block**2)))

            if rms >= SILENCE_RMS_THRESHOLD:
                buffer.append(block)
                speaking = True
                silence_run = 0
            elif speaking:
                buffer.append(block)
                silence_run += 1
                if silence_run >= SILENCE_BLOCKS_TO_CUT:
                    if len(buffer) - silence_run >= MIN_SPEECH_BLOCKS:
                        yield np.concatenate(buffer)
                    buffer = []
                    speaking = False
                    silence_run = 0


def main() -> None:
    print("Loading faster-whisper model (large-v3, int8, cpu)...", file=sys.stderr)
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print("Model loaded.", file=sys.stderr)

    for utterance in _record_utterances():
        segments, info = model.transcribe(utterance, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        if text.strip():
            print(f"[{info.language}] {text.strip()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
