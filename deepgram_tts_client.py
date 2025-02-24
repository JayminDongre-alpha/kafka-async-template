from signal import SIGINT, SIGTERM
import asyncio
from typing import Optional, Callable, Dict, Any, List
from deepgram.utils import verboselogs

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    SpeakWebSocketEvents,
    SpeakWSOptions,
)

global warning_notice
warning_notice = True

async def shutdown(signal, loop, dg_connection):
    print(f"Received exit signal {signal.name}...")
    await dg_connection.finish()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    print(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    print("Shutdown complete.")

class DeepgramTTSClient:

    client = None
    dg_connection = None

    def __init__(
            self,
            api_key: str
    ):
        config: DeepgramClientOptions = DeepgramClientOptions(
            # options={
            #     # "auto_flush_speak_delta": "500",
            #     "speaker_playback": "true"
            # },
            # verbose=verboselogs.SPAM,
        )
        self.client = DeepgramClient(api_key, config=config)
        self.init_connection()

    def init_connection(self):
        loop = asyncio.get_event_loop()

        for signal in (SIGTERM, SIGINT):
            loop.add_signal_handler(
                signal,
                lambda: asyncio.create_task(shutdown(signal, loop, self.dg_connection)),
            )

        async def on_open(self, open, **kwargs):
            print(f"\n\n{open}\n\n")

        async def on_metadata(self, metadata, **kwargs):
            print("on meta_data")
            print(f"\n\n{metadata}\n\n")

        async def on_flush(self, flushed, **kwargs):
            print(f"\n\n{flushed}\n\n")

        async def on_clear(self, clear, **kwargs):
            print(f"\n\n{clear}\n\n")

        async def on_close(self, close, **kwargs):
            print(f"\n\n{close}\n\n")

        async def on_warning(self, warning, **kwargs):
            print(f"\n\n{warning}\n\n")

        async def on_error(self, error, **kwargs):
            print(f"\n\n{error}\n\n")

        async def on_unhandled(self, unhandled, **kwargs):
            print(f"\n\n{unhandled}\n\n")

        async def on_binary_data(self, data, **kwargs):
            print("data is recived............................")
            global warning_notice

            print(len(data))
            if warning_notice:
                print("Received binary data")
                print("You can do something with the binary data here")
                print("OR")
                print(
                    "If you want to simply play the audio, set speaker_playback to true in the options for DeepgramClientOptions"
                )
                warning_notice = False

        self.dg_connection = self.client.speak.asyncwebsocket.v("1")
        self.dg_connection.on(SpeakWebSocketEvents.Open, on_open)
        # self.dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)
        self.dg_connection.on(SpeakWebSocketEvents.Metadata, on_metadata)
        self.dg_connection.on(SpeakWebSocketEvents.Flushed, on_flush)
        self.dg_connection.on(SpeakWebSocketEvents.Cleared, on_clear)
        self.dg_connection.on(SpeakWebSocketEvents.Close, on_close)
        self.dg_connection.on(SpeakWebSocketEvents.Error, on_error)
        self.dg_connection.on(SpeakWebSocketEvents.Warning, on_warning)
        self.dg_connection.on(SpeakWebSocketEvents.Unhandled, on_unhandled)


    def get_speak_options(self, model: str = "aura-asteria-en",
            encoding: str = "linear16",
            sample_rate: int = 16000,):
        options: SpeakWSOptions = SpeakWSOptions(
            model=model,
            encoding=encoding,
            sample_rate=sample_rate,
        )
        return options

    def bind_audio_event(self, method):
        self.dg_connection.on(SpeakWebSocketEvents.AudioData, method)


# FastAPI WebSocket integration
from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()


@app.websocket("/tts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Create a new TTS client for this connection
    tts_client = DeepgramTTSClient(
        api_key="f90942b7ca7ef783e07e2381c1d37901ed4001f1"
    )

    # Set up the callback to send audio to the WebSocket
    async def send_audio_to_websocket(self, data, **kwargs):
        print("helloo su................")
        print(kwargs)
        print(data)
        await websocket.send_bytes(data)

    tts_client.bind_audio_event(send_audio_to_websocket)
    await tts_client.dg_connection.start(tts_client.get_speak_options())


    try:
        while True:
            # Receive text from the client
            text = await websocket.receive_text()

            print("sending text")
            # Send to Deepgram for TTS conversion
            await tts_client.dg_connection.send_text(text)

            # Flush to make sure all text is processed
            await tts_client.dg_connection.flush()

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up
        await tts_client.dg_connection.disconnect()
        await websocket.close()

#uvicorn deepgram_tts_client:app