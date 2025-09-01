import asyncio
from google import genai
from dotenv import load_dotenv
import wave
import sounddevice as sd

load_dotenv()

client = genai.Client()
model = "gemini-live-2.5-flash-preview"
instructions = "You are a cowboy, you are talking to a user about your life and your experiences."

config = {"response_modalities": ["AUDIO"]}


async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        wf = wave.open("audio.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)

        with sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16') as stream:

            while True:
                message = input("Enter your message: ")
                if message.lower() == "quit":
                    break


                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": message}]}, turn_complete=True
                )

                async for response in session.receive():
                    if response.data is not None:
                        stream.write(response.data)
                                # Un-comment this code to print audio data info
                    if response.server_content.model_turn is not None:
                        print(response.server_content.model_turn.parts[0].inline_data.mime_type)
                wf.close()

    


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBye")
