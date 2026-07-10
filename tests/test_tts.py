import asyncio
import edge_tts
import io
import pygame

VOICE = "en-US-AvaNeural"

async def speak(text:str = "") -> str:
    try:
        print(f"Connection to Edge TTS and generating audio with voice {VOICE}")
        
        audio_buffer = io.BytesIO()
        communicate = edge_tts.Communicate(text, VOICE)

        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_buffer.write(chunk['data']) #type: ignore

        audio_buffer.seek(0)

        pygame.mixer.init()
        pygame.mixer.music.load(audio_buffer)
        pygame.mixer.music.play()

        print(f"Speaking...")

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        return "Finished speaking"
    except Exception as e:
        return f"An error occurred: {e}"

# if __name__ == "__main__":
    # asyncio.run(speak(text=""))