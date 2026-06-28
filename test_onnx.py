import os
import pyaudio
import numpy as np
from openwakeword.model import Model

MODEL_PATH = "output/jade/jade.onnx"

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Could not find the trained jade.onnx at {MODEL_PATH}")

print("Loading jade.onnx")
model = Model(wakeword_models=[MODEL_PATH])

CHUNK_SIZE = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16_000
GAIN = 1.0

p = pyaudio.PyAudio()
mic_stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK_SIZE
)

print(f"Mic active (Volume Gain: {GAIN}x), say 'Jade' to test")

try:
    while True:
        raw_audio_bytes = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        audio_array = np.frombuffer(raw_audio_bytes, dtype=np.int16)

        if GAIN != 1.0:
            audio_array = audio_array.astype(np.float32) * GAIN
            audio_array = np.clip(audio_array, -32768, 32767).astype(np.int16)

        prediction = model.predict(audio_array)

        jade_score = prediction.get("jade", 0.0) #type: ignore

        if jade_score > 0.05:
            status_bar = "█" * int(jade_score * 20)
            print(f"Listening... Raw Confidence [{status_bar:<20}] {jade_score:.2f}", end='\r')

        if jade_score > 0.40:
            print(f"\nSUCCESS: Jade detected! Raw confidence: {jade_score:.2f}\n")

except KeyboardInterrupt:
    print(f"\nStopping local audio test...")
except Exception as e:
    print(f"An error occurred when testing wakeword: {e}")
finally:
    mic_stream.stop_stream()
    mic_stream.close()
    p.terminate()