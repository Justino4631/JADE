import pyaudio
import numpy as np
from openwakeword.model import Model
import asyncio
import sys
import speech_recognition as sr
from agent import agent as strands_agent
import io
import edge_tts
import pygame.mixer as mixer

OWW_Model = Model(wakeword_models=['jade.onnx'])

CHUNK_SIZE = 1280
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16_000
GAIN = 1.0

MAX_COMMAND_CHUNKS = 200

VOICE = 'en-US-AvaNeural'

def detect_wake_word(raw_audio_bytes: bytes) -> bool:

    audio_array = np.frombuffer(raw_audio_bytes, dtype=np.int16)
    if GAIN != 1.0:
        audio_array = audio_array.astype(np.float32) * GAIN
        audio_array = np.clip(audio_array, -32768, 32767).astype(np.int16)
    
    prediction = OWW_Model.predict(audio_array)
    score = prediction.get("jade", 0.0) #type: ignore
    print(score)
    return True if score > 0.12 else False

async def speak(text: str = "") -> tuple:
    try:
        print(f'Connecting to Edge TTS, generating audio with voice {VOICE}')

        audio_buffer = io.BytesIO()
        communicate = edge_tts.Communicate(text, VOICE)

        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_buffer.write(chunk['data']) #type: ignore
        audio_buffer.seek(0)

        mixer.init()
        mixer.music.load(audio_buffer)
        mixer.music.play()

        print("Speaking...")

        while mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        return "Finished speaking with no errors", True
    except Exception as e:
        return f"An error occurred while speaking: {e}", False

async def main() -> None:
    p = pyaudio.PyAudio()
    mic_stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    print("Mic stream open, start talking...")

    state = "WAKEWORD"
    command_buffer = []

    recognizer = sr.Recognizer()

    try:
        while True:
            raw_chunk = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)

            if state == "WAKEWORD":
                activated = detect_wake_word(raw_chunk)
                
                if activated:
                    print("Jade detected")
                    state = "RECORDING"
                    command_buffer = []
            else:
                command_buffer.append(raw_chunk)

                if len(command_buffer) >= MAX_COMMAND_CHUNKS:

                    audio_bytes = b"".join(command_buffer)
                    audio_data = sr.AudioData(audio_bytes, sample_rate=16_000, sample_width=2)
                    
                    try:
                        text = recognizer.recognize_google(audio_data, language='en-US') #type: ignore
                        if "quit" in text:
                            quit()
                        print(f"You said: {text}")
                    except sr.UnknownValueError:
                        print("Could not recognize audio")
                    except Exception as e:
                        print(f"An STT error occurred: {e}")

                    print("Invoking asynchronous agent request...")
                    response = await strands_agent.invoke_async(text) #NOTE: try strands_agent.stream_async?
                    message = response.message["content"][0]["text"] #type: ignore

                    print(f"\nAgent response: {message}")

                    speak_response = await speak(message)
                    if speak_response[1] is not True:
                        print(f"An error occurred when trying to speak: {speak_response[0]}")
                        quit()

                    command_buffer = []
                    state = "WAKEWORD"
                    print("\nReturning to wake word detection...")

    except KeyboardInterrupt:
        print("Process stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())