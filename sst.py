from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import WebSocket, WebSocketDisconnect
import whisper
import uuid
import os
import json
import time
import threading
from datetime import datetime
import edge_tts
from model_logic import process_text
from contextlib import asynccontextmanager
from pushnotification import reminder_notification



AUDIO_DIR = "./audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

connected_clients: set[WebSocket] = set()
whisper_model = whisper.load_model("small")
VOICE = "en-GB-ThomasNeural"

REMINDER_JSON = "./reminder.json"
last_triggered = set()  

def read_reminder():
    global last_triggered
    print("🔔 Reminder service started")

    while True:
        try:
            if not os.path.exists(REMINDER_JSON):
                time.sleep(60)
                continue

            with open(REMINDER_JSON, "r") as f:
                reminder_list = json.load(f)

            current_time = datetime.now().strftime("%H:%M")

            for reminder in reminder_list:
                reminder_id = f"{reminder['task']}_{reminder['time']}"
                if reminder["time"] == current_time and reminder_id not in last_triggered:
                    print(f" Reminder: {reminder['task']}")
                    reminder_notification(reminder['task'])
                    last_triggered.add(reminder_id)

            time.sleep(60)
            last_triggered.clear()

        except Exception as e:
            print("❌ Reminder error:", e)
            time.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=read_reminder, daemon=True)
    thread.start()
    print(" FastAPI app starting...")
    yield
    print(" FastAPI app shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask_voice")
async def ask_voice(audio: UploadFile = File(...)):
    uid = str(uuid.uuid4())
    input_audio = f"temp_{uid}.webm"
    output_audio = f"{uid}.mp3"
    output_path = os.path.join(AUDIO_DIR, output_audio)

    with open(input_audio, "wb") as f:
        f.write(await audio.read())

    # STT
    result = whisper_model.transcribe(input_audio)
    text = result["text"].strip()
    print("🗣 User:", text)

    if not text:
        response_text = "I could not hear you clearly. Please speak again."
    else:
        response_text = process_text(text)

    print("🤖 AI:", response_text)

    communicate = edge_tts.Communicate(response_text, VOICE)
    await communicate.save(output_path)

    os.remove(input_audio)

    audio_url = f"http://localhost:8000/audio/{output_audio}"


    dead_clients = set()
    for ws in connected_clients:
        try:
            await ws.send_json({
                "type": "audio",
                "url": audio_url,
                "text": response_text
            })
        except:
            dead_clients.add(ws)

    connected_clients.difference_update(dead_clients)

    return {"status": "broadcasted"}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)
    print("🔗 Client connected")

    try:
        while True:
            await ws.receive_text()  
    except WebSocketDisconnect:
        connected_clients.remove(ws)
        print("❌ Client disconnected")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    return FileResponse(
        path=os.path.join(AUDIO_DIR, filename),
        media_type="audio/mpeg"
    )
