# Changelog

## [2024-01-09] - Audio Waveform Visualization

### Added
- **WaveformUI Component** (`waveform_ui.py`)
  - Real-time audio visualization with smooth wave animations
  - White line with rounded edges that responds to audio amplitude
  - 60 FPS animation loop for fluid motion
  - Multiple sine wave harmonics for organic movement
  - Amplitude-based glow effects
  - Smooth interpolation between amplitude states
  
- **Integration with AudioLoop**
  - Waveform UI automatically launches when starting the Magic Mirror
  - Audio data is passed to the waveform in real-time during playback
  - Proper cleanup when exiting the application

### Technical Details
- Uses tkinter for cross-platform GUI support
- Numpy for efficient audio data processing
- Thread-safe queue for audio data transfer
- Amplitude calculation from PCM audio samples
- Smooth decay when no audio is playing

### Visual Features
- Base waveform with 3 harmonic frequencies for natural movement
- Dynamic line width based on audio amplitude
- Opacity variations across the waveform length
- Glow effect for high amplitude audio
- Black background for high contrast

### Installation
- Added numpy to dependencies in documentation
- Updated setup instructions in README.md
