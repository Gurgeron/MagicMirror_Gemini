# Magic Mirror with Audio Waveform Visualization

A real-time AI assistant that uses Google's Gemini Live API with visual audio feedback. Features a beautiful animated waveform that responds to the AI's voice output.

## Features

- **Real-time AI conversation** using Gemini Live API
- **Beautiful waveform visualization** - A white line with smooth wave animations that responds to audio
- **Multiple input modes**:
  - Camera mode (default) - AI can see through your camera
  - Screen mode - AI can see your screen
  - Audio-only mode - Voice conversation without video
- **Voice activity detection** - Automatic mic gating when AI is speaking

## Prerequisites

- Python 3.8 or higher
- A Google API key (either `GOOGLE_API_KEY` or `GEMINI_API_KEY`)
- macOS, Windows, or Linux with audio support

## Setup

1. Clone or download this repository

2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install google-genai opencv-python pyaudio pillow mss numpy
   ```

4. Create a `.env` file in the project directory with your API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   or
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

## Running the Application

### Basic usage (camera mode with waveform):
```bash
python gcode.py
```

### Different modes:
```bash
# Screen sharing mode
python gcode.py --mode screen

# Audio only mode  
python gcode.py --mode none

# Use a different camera
python gcode.py --camera 1
```

## How to Use

1. Run the application - a waveform window will appear
2. Type your message and press Enter to send to the AI
3. The AI will respond with voice, and you'll see the waveform animate
4. The white line creates smooth waves that respond to the AI's voice amplitude
5. Type "quit" to exit the application

## Waveform Visualization

The waveform UI features:
- **White line with rounded edges** that animates smoothly
- **Wave effect** that increases with audio amplitude
- **Glow effect** when the AI speaks loudly
- **60 FPS smooth animation** for a polished look
- **Real-time response** to audio output

## Troubleshooting

### No audio output
- Check your system volume
- Ensure your audio output device is correctly selected
- Verify the API key is set correctly

### Waveform not appearing
- Make sure you have tkinter installed (usually comes with Python)
- Check that numpy is installed: `pip install numpy`

### "python: command not found"
- Use `python3` instead of `python`
- Or activate your virtual environment first
- Or use the full path: `./venv/bin/python gcode.py`

### PyAudio installation issues
- On macOS: `brew install portaudio` then `pip install pyaudio`
- On Ubuntu/Debian: `sudo apt-get install portaudio19-dev` then `pip install pyaudio`
- On Windows: `pip install pyaudio` should work directly

## API Keys

To get an API key:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

## Notes

- The AI is configured as the "Magic Mirror" from Snow White - knowledgeable but kind
- The waveform visualization runs in a separate thread for smooth performance
- Audio is streamed in real-time for immediate playback
- The system uses voice activity detection to prevent feedback loops

## Changelog

- Added real-time audio waveform visualization with smooth animations
- Integrated WaveformUI class with tkinter for visual feedback
- Added 60 FPS animation loop with wave effects
- Implemented amplitude-based animations and glow effects
