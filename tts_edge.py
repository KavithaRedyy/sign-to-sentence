import asyncio
import edge_tts
import uuid
import os
import threading
from playsound import playsound

def _run_tts(sentence):
    async def _speak():
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(
            text=sentence,
            voice="en-US-AriaNeural"
        )
        await communicate.save(filename)
        playsound(filename)
        os.remove(filename)

    asyncio.run(_speak())

def speak_sentence(sentence):
    t = threading.Thread(target=_run_tts, args=(sentence,))
    t.start()

