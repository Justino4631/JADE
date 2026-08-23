# JADE

JADE is a project I've worked on this past summer. It stands for "Justin's Autonomous Desktop E-ssistant". It
uses a variety of cool programming things like a raspberrypi, agents, apis, etc... to create a working
hardware desktop project that takes in audio, processes it, sends it to an agent, executes a task, and outputs audio.

# How It Works

(Check out JADE.jpeg to see the hardware assembly) JADE initially waits for a wakeword (e.g. "Jade"). It uses a
trained wakeword model from the openwakeword api to process audio and check if the wakeword is said. Once it detects the wakeword, it switches modes to then detect speech and translate it into text (using the speech_recognition package). Once the user finishes speaking, or exceeds the time limit on commands, it takes
whatever text it got out of processing the user's speech and feeds it to an embedding model. This embedding model uses a dictionary of tool names and their descriptions to get the 5 most relevant tools before passing the request
to an agent (strands api, ollama) which uses one of the tools to execute a request. Then, once the request is executed, it spits out some message like "Request successfully completed" or something similar, which is then outputted as audio.

As for the hardware side of things, a raspberrypi 4 runs the code. A breadboard is connected to some jumpers, which is then connected to a mini microphone (ICS 43434), a mini-amp (12S 98357A) and a mini speaker. The microphone is used for all the audio processing (e.g. listening to wakeword, speech-to-text) and the mini-amp and speaker are used for the audio output.

# Process

Here, I'm gonna talk about my process in creating this project. I first created the tools, which can be found in the Tools folder. Initially, I tried to go for a global-agent controls mini-agents that handle different things like tools that use weather apis (OpenMeteo), calendar apis (Google Calendar), web (wikipedia among other packages) and writing. However, once I ran this structure on the raspberrypi, it failed because using two or more agents with 3B+ parameters on a raspberrypi, as I found out, causes the rpi to shut itself off. However these tool classes were created first and tested, and later the tools were just put into one file (flattened) instead of multipls.

Then, I tested software on the computer in the form of audio output, wakeword detection, and stt. These files were then named according to whatever they were testing and put into the tests folder. How I programmed this project was by creating one feature at a time, testing it (test files) then once all the features were done individually, integrating them into one pipeline file. 

Once my hardware assembly was done, I moved my code over to the raspberrypi and made feature and test scripts that ran on the rpi. I made pipeline testing files to run on the computer and raspberrypi to debug when something went wrong. After months of hard work, I was done.

# Results

Ultimately, by working on this project, I created my first hardware project (using the rpi, breadboard, mini speaker, etc...) and learned how to work with agents and different apis. I made a working pipeline which I could reliably use as a personal Siri/Alexa to do tasks for me. This was a great learning experience and the skills I learned while creating this project will help me with otehr coding projects like projects for the Congressional App Challenge (which I won in 2025 with my friend Logan for district NV-02) and FRC stuff (for my team, The Ionizers 10903).

# AI Usage

When I first shipped, I got dinged for quote "using massive amounts of AI"- that is false. Some of my commits may have been misleading such as the "Comments (Made By AI...)". Almost the entirety of the code was written by me, and AI was only used to, like the commit said, write comments, or to debug features which I had never worked on before like stuff for audio i/o on ths raspberrypi. The idea was mine and was original, all the testing and features were created by *me* first, not AI. I recognize that using AI to write the original README.md may have been too far (which is why I am writing this one myself :3). I admit (and included in the AI Usage section of this ship) that I used AI to write comments, which the purpose of was to help readers of the code understand the code, as I had other projects and things I wanted to do other than spend grueling hours commenting already complete code. However, I want to reiterate that AI wrote little-to-none code in this project and was only used for commenting or debugging issues. 

# Final Thoughts

Thank you for reading the Readme! Whether you are a Hackclub employee or casual code scroller I hope you thought this project was cool because I really worked hard on it!

-Justin