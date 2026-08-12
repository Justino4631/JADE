# JADE: Voice-Driven Agent System

JADE is a distributed voice assistant that listens for commands, processes them through AI agents and tools, and responds naturally with synthesized speech. It uses Raspberry Pi 4s for edge audio processing and a computer for agent reasoning.

## How It Works

The system creates a voice pipeline: microphone → RPi (wakeword detection) → computer (speech recognition, agent processing, tool execution) → RPi (synthesis) → speaker.

When you say "jade," the wakeword detector activates. Your speech is transcribed to text, passed to a Strands Agent that selects appropriate tools, and the response is converted back to speech and played through the speaker.

## Features

JADE has access to several integrated tools: Google Calendar for event management, Open-Meteo for weather, web search and news via DuckDuckGo and NewsAPI, and local notes/todos/journal storage. The agent intelligently routes requests to the right tool.

## Getting Started

Install dependencies with `pip install -r requirements.txt`. Set up Google Calendar by saving OAuth credentials as `credentials.json` from Google Cloud Console. Test the pipeline with `python test_pipeline_rpi.py`.

## Usage

```python
from flattened_tools_agent import call_agent
import asyncio

response = asyncio.run(call_agent("What's my schedule today?"))
print(response)
```

You can also call individual tools:
```python
from flattened_tools_agent import get_current_weather, read_upcoming_events

weather = get_current_weather("San Francisco")
events = read_upcoming_events(max_results=5)
```

## Project Structure

- `flattened_tools_agent.py`: Main agent with tool integrations
- `test_pipeline_rpi.py`: Audio pipeline test for Raspberry Pi
- `jade.onnx`: Wakeword detection model
- `Tools/`: Calendar, Weather, Web, and Writing tool modules
- `tests/`: Test suite for each component

## Configuration

Customize wakewords and model settings in `jade.yaml`. Adjust audio parameters like sample rate (48kHz) and chunk size in `test_pipeline_rpi.py`.

## Technical Stack

Uses PyAudio for audio I/O, SpeechRecognition for STT, edge-tts for TTS, Strands Agent framework for reasoning, OpenWakeWord for wakeword detection, and various APIs (Google Calendar, Open-Meteo, NewsAPI).

## Status

Core pipeline works with wakeword detection, speech recognition, agent processing, and response synthesis. Full Raspberry Pi hardware integration is in progress. Currently designed for English speakers.

## Author

Justin Baratta, Summer 2026