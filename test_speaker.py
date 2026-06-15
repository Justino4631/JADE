import asyncio
import edge_tts
import io
import pyaudio
from pydub import AudioSegment

async def main(TEXT="") -> None:
    print("Streaming from Edge TTS engine...")

    VOICE = "en-US-GuyNeural" 
    communicate = edge_tts.Communicate(TEXT, VOICE)

    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"] #type: ignore
    
    print("Processing audio in memory...")
    
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")

    audio_segment = audio_segment.set_frame_rate(24000).set_channels(1)
    raw_pcm_data = audio_segment.raw_data

    print("Streaming directly to I2S hardware...")

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
        
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main("Hello, World! This audio is playing on the raspberry pi."))