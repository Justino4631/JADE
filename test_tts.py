import asyncio
import edge_tts
import pygame
import io

async def main(TEXT="") -> None:
    print("Communicating with Edge TTS engine...")

    VOICE = "en-US-AvaNeural" 
    communicate = edge_tts.Communicate(TEXT, VOICE)

    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    print("Playing audio...")

    pygame.mixer.init()
    pygame.mixer.music.load(io.BytesIO(audio_data), "mp3")
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
        
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main("Hello, World!!!"))