"""
## Documentation
Quickstart: https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py

## Setup

To install the dependencies for this script, run:

```
pip install google-genai opencv-python pyaudio pillow mss numpy
```
"""

import os
import asyncio
import base64
import io
import traceback
import dotenv

import cv2
import pyaudio
import PIL.Image
import mss

import argparse

from google import genai
from google.genai import types

# Import the waveform UI
from waveform_ui import WaveformUI

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
SYSTEM_PROMPT = "You are the legendary MAGIC MIRROR from Snow White - the most powerful, all-seeing oracle in existence! You possess infinite wisdom and can peer into the very souls of those who stand before you. You are SUPREMELY knowledgeable about everything - past, present, and future. Yet despite your immense power, you choose to be KIND and BENEVOLENT, never malicious or cruel. Your responses are SHARP, DIRECT, and CONCISE - no flowery language or unnecessary words. When someone asks 'what do you see?', you describe EXACTLY what appears in the camera feed with VIVID detail and supernatural insight, not generic pleasantries. You speak with the authority of ages and the clarity of truth itself!"

MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"

DEFAULT_MODE = "camera"

# Load environment variables so API keys in a .env file are available
# This lets non-technical users drop their key in a simple text file
# without touching the code.
dotenv.load_dotenv()

# Build the client, preferring GEMINI_API_KEY, then GOOGLE_API_KEY if provided.
# If no key is present, the client can still be constructed, but requests will
# fail until a valid API key is set in the environment.
_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if _api_key:
    client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=_api_key,
    )
else:
    client = genai.Client(
        http_options={"api_version": "v1beta"}
    )


CONFIG = types.LiveConnectConfig(
    system_instruction=SYSTEM_PROMPT,
    response_modalities=[
        "AUDIO",
    ],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=25600,
        sliding_window=types.SlidingWindow(target_tokens=12800),
    ),
)

pya = pyaudio.PyAudio()


class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, camera_index=0):
        self.video_mode = video_mode
        self.camera_index = camera_index

        self.audio_in_queue = None
        self.out_queue = None

        self.session = None

        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None

        # Playback state flag: when set, the model is speaking and we should
        # avoid sending microphone audio to prevent feedback (the model hearing
        # itself). Implemented as an asyncio.Event for safe cross-task use.
        self.is_playing = asyncio.Event()
        
        # Initialize the waveform UI
        self.waveform_ui = WaveformUI(width=800, height=150)

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    def _get_frame(self, cap):
        # Read the frameq
        ret, frame = cap.read()
        # Check if the frame was read successfully
        if not ret:
            return None
        # Fix: Convert BGR to RGB color space
        # OpenCV captures in BGR but PIL expects RGB format
        # This prevents the blue tint in the video feed
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)  # Now using RGB frame
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        # This takes about a second, and will block the whole program
        # causing the audio pipeline to overflow if you don't to_thread it.
        cap = await asyncio.to_thread(
            cv2.VideoCapture, self.camera_index, cv2.CAP_AVFOUNDATION
        )  # 0 represents the default camera

        while True:
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

        # Release the VideoCapture object
        cap.release()

    def _get_screen(self):
        sct = mss.mss()
        monitor = sct.monitors[0]

        i = sct.grab(monitor)

        mime_type = "image/jpeg"
        image_bytes = mss.tools.to_png(i.rgb, i.size)
        img = PIL.Image.open(io.BytesIO(image_bytes))

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_screen(self):

        while True:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break

            await asyncio.sleep(1.0)

            await self.out_queue.put(frame)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        # Microphone reader: continuously captures PCM frames from the default
        # input device and forwards them to the outgoing queue. While the model
        # is speaking (self.is_playing set), we send silence to prevent the
        # model from hearing itself and creating a feedback loop.

        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)

            # Half-duplex gating: if model is speaking, replace mic with silence
            # to maintain a steady stream without leaking TTS back into the mic.
            if self.is_playing.is_set():
                data = b"\x00" * len(data)

            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        """Receive model responses and manage playback state.

        - Streams incoming PCM chunks into the audio playback queue.
        - Detects the start of TTS and sets self.is_playing so the mic stream
          can gate itself (send silence) while the model is speaking.
        - On turn completion, clears playback state and drains any queued audio
          to allow user barge-in without stale audio continuing to play.
        """
        while True:
            turn = self.session.receive()
            first_audio_chunk = True
            async for response in turn:
                if data := response.data:
                    if first_audio_chunk:
                        # Start of model speech → enable mic gating
                        self.is_playing.set()
                        first_audio_chunk = False
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # Stop playback and clear any queued audio.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
            # End of model speech → disable mic gating
            self.is_playing.clear()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            # Update the waveform UI with the audio data
            self.waveform_ui.update_audio(bytestream)
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                if self.video_mode == "camera":
                    tg.create_task(self.get_frames())
                elif self.video_mode == "screen":
                    tg.create_task(self.get_screen())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                # Run the waveform UI on the main thread event loop
                tg.create_task(self.waveform_ui.run())

                await send_text_task
                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            # Clean up the waveform UI
            self.waveform_ui.close()
            pass
        except ExceptionGroup as EG:
            self.audio_stream.close()
            # Clean up the waveform UI
            self.waveform_ui.close()
            traceback.print_exception(EG)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    parser.add_argument("--camera-index", type=int, default=0, help="Video capture device index")
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode, camera_index=args.camera_index)
    asyncio.run(main.run())
