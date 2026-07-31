import os
import sys
import speech_recognition as sr
import pyaudio

MIC_DEVICE_INDEX = 1  

class VoiceHatMicrophone(sr.Microphone):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        super().__init__(device_index=device_index, sample_rate=sample_rate, chunk_size=chunk_size)
        self.CHANNELS = 2 

def process_text(text):
    sys.stdout.write(f"\r{text}")
    sys.stdout.flush()

if __name__ == "__main__":
    os.environ['AUDIODEV'] = 'null'
    
    print("Initializing SpeechRecognition... ")
    
    recognizer = sr.Recognizer()
    microphone = VoiceHatMicrophone(
        device_index=MIC_DEVICE_INDEX,
        sample_rate=16000,
        chunk_size=1024 
    )

    try:
        with microphone as source:
            print("Adjusting for ambient noise, please wait...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            
    except Exception as e:
        print(f"\nFailed to open the microphone: {e}")
        sys.exit(1)

    print("\nSystem ready, speak into the microphone to test...")
    
    try:
        while True:
            with microphone as source:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            
            try:
                text = recognizer.recognize_google(audio, language='en-US') #type: ignore
                process_text(text + "\n")
            except sr.UnknownValueError:
                process_text("... ")
            except sr.RequestError as e:
                print(f"\nCould not request results: {e}")
                
    except KeyboardInterrupt:
        print("\nStopping transcription.")