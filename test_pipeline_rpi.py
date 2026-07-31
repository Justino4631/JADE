import pyaudio
import numpy as np
from openwakeword.model import Model
import asyncio
import sys
import speech_recognition as sr
from flattened_tools_agent import call_agent
import io
import edge_tts
from pydub import AudioSegment
import os
from sentence_transformers import SentenceTransformer, util

OWW_Model = Model(wakeword_model_paths=['jade.onnx'])

CHUNK_SIZE = 1280 
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 16_000
GAIN = 1.0
MIC_DEVICE_INDEX = 1

VOICE = 'en-US-AvaNeural'

TOOLS_MAP = {
    # --- Calendar Tools ---
    "read_upcoming_events": "Retrieves upcoming Google Calendar events.",
    "add_event": "Creates a new event on Google Calendar given a summary, start time, and end time.",
    "delete_event": "Deletes an existing Google Calendar event using its event ID.",
    "get_now": "Returns the current ISO date and time for the America/Los_Angeles timezone.",
    "get_events_and_ids": "Returns a mapping of upcoming Google Calendar event names to their IDs and start times.",

    # --- Weather Tools ---
    "get_current_weather": "Gets current weather conditions (temperature, wind speed, precipitation, weather code) for a city.",
    "get_forecast": "Gets daily weather forecast max/min temperatures and conditions for a city.",
    "get_weather_summary": "Returns a compact current weather snapshot combined with a multi-day forecast for a city.",
    "get_forecast_summary": "Returns a human-readable text forecast summary for a city across specified days.",

    # --- Web Tools ---
    "search_and_lookup": "Searches Wikipedia or DuckDuckGo web search for general knowledge, current events, and facts.",
    "get_stock_prices": "Fetches current stock price details, day high/low, and company info for ticker symbols.",
    "get_news_headlines": "Fetches top news article headlines.",

    # --- Writing / Local Storage Tools ---
    "create_notes_entry": "Creates a new text note entry saved locally for today's date.",
    "create_todo_entry": "Creates a new todo list entry with tasks and optional tags for today's date.",
    "create_journal_entry": "Creates a new journal entry saved locally for today's date.",
    "list_writing_entries": "Lists local writing entries (notes, todos, or journals) matching a search query.",
    "search_entries": "Searches local writing entries by title or content using substring matching.",
    "read_entry": "Reads full content of a specific local writing entry by its title.",
    "complete_todo": "Marks a specific task inside a todo file as complete.",
    "get_incomplete_todos": "Retrieves all incomplete todo tasks across all local todo files.",
    "get_todo_summary": "Provides a high-level summary of total, completed, and incomplete todo tasks and tags.",
    "add_task": "Appends a new task to an existing local todo entry file.",
    "update_entry": "Updates or appends text content to an existing local note or journal entry.",
    "get_today": "Returns today's date in YYYY-MM-DD format."
}

EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
TOOL_NAMES, TOOL_DESCRIPTIONS = list(TOOLS_MAP.keys()), list(TOOLS_MAP.values())
TOOL_EMBEDDINGS = EMBEDDER.encode(TOOL_DESCRIPTIONS, convert_to_tensor=True)

class VoiceHatMicrophone(sr.Microphone):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        super().__init__(device_index=device_index, sample_rate=sample_rate, chunk_size=chunk_size)
        self.CHANNELS = 2

def process_wakeword_frame(raw_stereo_bytes: bytes) -> bool:
    """Downmixes stereo frame to mono and predicts wake word."""
    stereo_arr = np.frombuffer(raw_stereo_bytes, dtype=np.int16)

    mono_arr = (stereo_arr[0::2].astype(np.int32) + stereo_arr[1::2].astype(np.int32)) // 2
    audio_arr = mono_arr.astype(np.int16)

    if GAIN != 1.0:
        audio_arr = audio_arr.astype(np.float32) * GAIN #type: ignore
        audio_arr = np.clip(audio_arr, -32768, 32767).astype(np.int16)

    prediction = OWW_Model.predict(audio_arr)
    score = prediction.get("jade", 0.0) #type: ignore
    if score > 0.1:
        print(score)
    return True if score > 0.16 else False

def get_relevant_tools(user_query: str, top_k: int = 5):
    query_emb = EMBEDDER.encode(user_query, convert_to_tensor=True)

    hits = util.semantic_search(query_emb, TOOL_EMBEDDINGS, top_k=top_k)[0]

    selected_tools = [TOOL_NAMES[hit['corpus_id']] for hit in hits] #type: ignore
    return selected_tools

async def speak(text: str = "") -> tuple:
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        audio_data = b""

        async for chunk in communicate.stream():
            if chunk['type'] == "audio":
                audio_data += chunk['data'] #type: ignore
        
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format='mp3')
        audio_segment = audio_segment.set_frame_rate(24_000).set_channels(1)
        raw_pcm_data = audio_segment.raw_data

        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(audio_segment.sample_width),
            channels=audio_segment.channels,
            rate=audio_segment.frame_rate,
            output=True
        )

        stream.write(raw_pcm_data)
        stream.stop_stream()
        stream.close()
        p.terminate()

        return "Spoke successfully!", True
    
    except Exception as e:
        return f"An error occurred when trying to speak: {e}", False

async def main() -> None:
    os.environ['AUDIODEV'] = 'null'

    recognizer = sr.Recognizer()
    microphone = VoiceHatMicrophone(
        device_index=MIC_DEVICE_INDEX,
        sample_rate=16_000,
        chunk_size=1024
    )

    p = pyaudio.PyAudio()
    state = 'WAKEWORD'
    
    live_stream = None
    print("System started, listening for 'Jade'...")
    activated = False

    try:
        while True:
            if state == 'WAKEWORD':
                if live_stream is None:
                    live_stream = p.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=MIC_DEVICE_INDEX,
                        frames_per_buffer=CHUNK_SIZE
                    )

                raw_bytes = await asyncio.to_thread(
                    live_stream.read, CHUNK_SIZE, False
                )
                
                activated = process_wakeword_frame(raw_bytes)

                if activated:
                    print("\n[Jade detected!]")
                    try:
                        live_stream.stop_stream()
                        live_stream.close()
                    except Exception:
                        pass
                    live_stream = None
                    
                    s = await speak("How can I help you?")
                    await asyncio.sleep(0.5)
                    state = "RECORDING"

            elif state == "RECORDING":
                
                with microphone as source:
                    try:

                        recognizer.pause_threshold = 2.5
                        recognizer.phrase_threshold = 0.5 
                        recognizer.non_speaking_duration = 0.75

                        recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        print("Adjusted to environment ambient noise... speak now")

                        audio_data = await asyncio.to_thread(
                            recognizer.listen, source, timeout=10, phrase_time_limit=15
                        )
                        
                        text = await asyncio.to_thread(
                            recognizer.recognize_google, audio_data, language='en-US' #type: ignore
                        )
                        tools = get_relevant_tools(text)
                        print(f"You said: {text}")
                        print(f"Tools available for agent: {tools}")

                    except sr.WaitTimeoutError:
                        print("No speech detected...")
                        text = ""
                    except sr.UnknownValueError:
                        print("Could not understand the audio...")
                        text = ""

                    if text:
                        if "quit" in text.lower():
                            print("Stopping process...")
                            sys.exit()

                        print("Invoking asynchronous agent request...")
                        response = await call_agent(text, tools)

                        print(f"\nAgent response: {response}")
                        speak_response = await speak(response)
                        if speak_response[1] is not True:
                            print(f"An error occurred when trying to speak: {speak_response[0]}")
                            sys.exit()

                OWW_Model.reset()
                
                state = "WAKEWORD"
                activated = False
                print("\nReturning to wake word detection...")
                
    except KeyboardInterrupt:
        print("\nStopping the process...")
    except Exception as e:
        print(f"\nAn error occurred while running the process: {e}")
    finally:
        if live_stream is not None:
            try:
                live_stream.stop_stream()
                live_stream.close()
            except Exception:
                pass
        p.terminate()

if __name__ == "__main__":
    asyncio.run(main())