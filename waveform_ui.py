"""
Waveform UI component for visualizing audio output with smooth wave animations.
OpenCV-based implementation (no tkinter), drawing a white rounded polyline.
Renders on the main thread via an asyncio run loop to avoid HighGUI threading issues.
"""

import asyncio
import time
from collections import deque
from typing import Deque

import cv2
import numpy as np
import queue


class WaveformUI:
    def __init__(self, width: int = 800, height: int = 200, window_name: str = "Magic Mirror - Waveform"):
        # UI geometry
        self.width = width
        self.height = height
        self.window_name = window_name
        # Supersampling factor for smoother rendering (2-3 recommended)
        self.ss = 3

        # Runtime flags/state
        self.is_running: bool = True

        # Audio queue populated from playback task (thread-safe Queue)
        self.audio_queue: "queue.Queue[bytes]" = queue.Queue(maxsize=100)

        # Amplitude smoothing state
        self.amplitude_history: Deque[float] = deque(maxlen=50)
        self.current_amplitude: float = 0.0
        self.target_amplitude: float = 0.0
        self._last_audio_time: float = 0.0

        # Animation state
        self.wave_phase: float = 0.0
        self.wave_speed: float = 0.35

    def update_audio(self, audio_data: bytes) -> None:
        """Called from audio playback to feed fresh PCM bytes for visualization."""
        self._last_audio_time = time.time()
        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            # Drop oldest to keep UI responsive
            try:
                _ = self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_data)
            except queue.Empty:
                pass

    def close(self) -> None:
        """Signal the UI loop to stop and close the window."""
        self.is_running = False
        try:
            cv2.destroyWindow(self.window_name)
        except Exception:
            pass

    async def run(self) -> None:
        """Main-thread render loop. Call this as an asyncio task.
        Continues until close() is called or the window is dismissed.
        """
        # Create window on the main thread
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.width, self.height)

        try:
            while self.is_running:
                # Drain audio queue and compute target amplitude
                try:
                    while True:
                        audio = self.audio_queue.get_nowait()
                        if audio:
                            amp = np.abs(np.frombuffer(audio, dtype=np.int16)).mean() / 32768.0
                            self.amplitude_history.append(amp)
                            self.target_amplitude = max(self.amplitude_history) if self.amplitude_history else 0.0
                except queue.Empty:
                    pass

                # Decay when idle
                if time.time() - self._last_audio_time > 0.1:
                    self.target_amplitude *= 0.96

                # Smooth toward target and advance phase
                self.current_amplitude += (self.target_amplitude - self.current_amplitude) * 0.18
                self.wave_phase += self.wave_speed

                # Offscreen high-res frame for supersampling
                off_w = int(self.width * self.ss)
                off_h = int(self.height * self.ss)
                off_frame = np.zeros((off_h, off_w, 3), dtype=np.uint8)

                # Use many points (per 1-2px at offscreen res) for smoother curves
                num_points = max(400, off_w // 2)
                # Horizontal margin so tips are visible
                thickness_base = int((6 + self.current_amplitude * 6) * self.ss)
                margin = max(thickness_base, int(12 * self.ss))
                xs = np.linspace(margin, off_w - 1 - margin, num_points)
                t = np.linspace(0, 1, num_points)

                # Multi-harmonic wave for organic motion
                w1 = np.sin(self.wave_phase + t * 4 * np.pi) * 0.35
                w2 = np.sin(self.wave_phase * 1.7 + t * 7 * np.pi) * 0.22
                w3 = np.sin(self.wave_phase * 0.8 + t * 2 * np.pi) * 0.5
                wave = (w1 + w2 + w3) * self.current_amplitude

                ys = (off_h / 2 + wave * off_h * 0.28).astype(np.int32)
                pts = np.stack([xs.astype(np.int32), ys], axis=1)

                # Thickness scales with supersampling
                thickness = max(2, min(24 * self.ss, thickness_base))

                # Main line at high-res
                cv2.polylines(
                    off_frame,
                    [pts],
                    isClosed=False,
                    color=(255, 255, 255),
                    thickness=thickness,
                    lineType=cv2.LINE_AA,
                )
                # Round end-caps
                p0 = tuple(pts[0])
                p1 = tuple(pts[-1])
                cap_r = max(1, thickness // 2)
                cv2.circle(off_frame, p0, cap_r, (255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)
                cv2.circle(off_frame, p1, cap_r, (255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)

                # Glow when louder (high-res first, then downsample)
                if self.current_amplitude > 0.25:
                    glow = off_frame.copy()
                    cv2.polylines(
                        glow,
                        [pts],
                        False,
                        (255, 255, 255),
                        thickness=int(thickness * 1.8),
                        lineType=cv2.LINE_AA,
                    )
                    # Glow caps
                    glow_cap_r = max(1, int(thickness * 0.9))
                    cv2.circle(glow, p0, glow_cap_r, (255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)
                    cv2.circle(glow, p1, glow_cap_r, (255, 255, 255), thickness=-1, lineType=cv2.LINE_AA)

                    glow = cv2.GaussianBlur(glow, (0, 0), sigmaX=10, sigmaY=10)
                    off_frame = cv2.addWeighted(glow, 0.25, off_frame, 1.0, 0)

                # Downsample with high-quality filter
                frame = cv2.resize(off_frame, (self.width, self.height), interpolation=cv2.INTER_AREA)
                cv2.imshow(self.window_name, frame)
                # Handle close (ESC)
                if cv2.waitKey(1) & 0xFF == 27:
                    self.close()
                    break

                # Yield to the event loop (~60fps)
                await asyncio.sleep(0.016)
        finally:
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass


# Example usage for testing
if __name__ == "__main__":
    import pyaudio
    
    # Create waveform UI
    waveform = WaveformUI()
    
    # Generate some test audio to visualize
    pa = pyaudio.PyAudio()
    
    # Simulate audio playback with varying amplitude
    import math
    for i in range(1000):
        # Generate test audio with varying amplitude
        t = i * 0.01
        amplitude = (math.sin(t * 0.5) * 0.5 + 0.5) * 32767
        frequency = 440  # A4 note
        
        # Generate sine wave
        samples = []
        for j in range(441):  # 0.01 seconds at 44100 Hz
            sample = amplitude * math.sin(2 * math.pi * frequency * j / 44100)
            samples.append(int(sample))
        
        audio_data = np.array(samples, dtype=np.int16).tobytes()
        waveform.update_audio(audio_data)
        
        time.sleep(0.01)
    
    # Keep running
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        waveform.close()
