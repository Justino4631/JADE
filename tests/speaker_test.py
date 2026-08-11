"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Speaker test that streams Edge TTS output to local audio hardware.
"""

import asyncio
import edge_tts
import io
import pyaudio
from pydub import AudioSegment

TEXT = "Hi dad! This is Justin's raspberry pi talking to you through his program."

async def test_speaker(text="") -> None:
    try:
        print("Streaming from Edge TTS engine...")

        VOICE = "en-US-AvaNeural"
        communicate = edge_tts.Communicate(text, VOICE)

        audio_data = b""
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_data += chunk['data'] #type: ignore
        
        print("Processing audio...")

        audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format='mp3')

        audio_segment = audio_segment.set_frame_rate(24_000).set_channels(1)
        raw_pcm_data = audio_segment.raw_data

        print("Streaming to I2S 98357 Amp...")

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

        print("Done speaking")
        return
    except Exception as e:
        print(f"An error occurred when testing the speaker: {e}")

if __name__ == "__main__":
    asyncio.run(test_speaker(text=TEXT))