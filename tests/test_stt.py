"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Basic speech-to-text interactive test using SpeechRecognition.
"""

import os
import sys
import speech_recognition as sr

def process_text(text):
    sys.stdout.write(f"\r{text}")
    sys.stdout.flush()

if __name__ == "__main__":
    print("Initializing SpeechRecognition (this may take a few moments...)")
    
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

    print("System ready, speak into the microphone to test... (Press Ctrl+C to stop)")
    
    try:
        while True:
            with microphone as source:
                audio = recognizer.listen(source, phrase_time_limit=5)
            
            try:
                text = recognizer.recognize_google(audio, language='en-US') #type: ignore
                process_text(text + "\n")
            except sr.UnknownValueError:
                process_text("... ")
            except sr.RequestError as e:
                print(f"\nCould not request results; {e}")
                
    except KeyboardInterrupt:
        print("\nStopping transcription")