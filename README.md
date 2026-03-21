

## Overview

HakunaMatata is a voice-first assistant built for elderly users. The user-facing entry point is a browser UI (`news/index.html`) where users press a button to speak. Audio is recorded and sent to a FastAPI backend, which transcribes it using OpenAI Whisper, classifies the intent, and responds using either a local LLM (Qwen3-4B), a live API (weather/push), or rule-based logic (reminders). Responses are converted back to speech using Microsoft Edge TTS and delivered to the frontend via WebSocket.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   news/index.html  (Browser UI)                 │
│                                                                 │
│   ┌─────────────────────┐      ┌──────────────────────────┐    │
│   │  "Talk" Button      │      │  "Enable Sound" Button   │    │
│   │  Records 5s audio   │      │  Unlocks autoplay audio  │    │
│   └────────┬────────────┘      └──────────────────────────┘    │
│            │  WebM audio blob                                   │
│            │  POST /ask_voice                                   │
│            │                         WebSocket /ws              │
│            │                  ◀── { audio_url, text } ──────    │
│            │                         audioPlayer.play()         │
└────────────┼────────────────────────────────────────────────────┘
             │  news/test.js handles recording, fetch, WS
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server (sst.py)                    │
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│   │  Whisper STT │───▶│ model_logic  │───▶│  Edge TTS (MP3) │  │
│   │  (small)     │    │  process_text│    │  Edge-TTS lib   │  │
│   └──────────────┘    └──────┬───────┘    └────────┬────────┘  │
│                              │                     │           │
│                              ▼                     ▼           │
│                     ┌────────────────┐    ┌────────────────┐   │
│                     │ Intent Router  │    │ WebSocket Push │   │
│                     └────────────────┘    │ (audio URL +   │   │
│                                           │  transcript)   │   │
└───────────────────────────────────────────┴────────────────┘
```

---

## Request Flow Diagram

```
User opens news/index.html in browser
     │
     ▼
┌──────────────────────────────────┐
│  Presses "Talk" button           │
│  (news/test.js)                  │
│  MediaRecorder captures 5s WebM  │
│  POST /ask_voice → FastAPI       │
└──────────────┬───────────────────┘
               │
               │
               ▼
┌──────────────────────┐
│  Whisper Transcribes │
│  Audio → Text        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  user_input_label()  │  ← Regex-based intent classifier
│  in model_logic.py   │
└──────────┬───────────┘
           │
     ┌─────┴──────────────────────────────────────────┐
     │                                                │
     ▼                                                ▼
EMERGENCY?                                      REMINDER_SET?
     │                                                │
     ▼                                                ▼
┌─────────────────┐                        ┌──────────────────────┐
│ push_notification│                        │ extract_reminder()   │
│ (Pushover API)  │                         │ → saves to           │
│ "Alert caretaker│                         │   reminder.json      │
│  immediately"   │                         └──────────────────────┘
└─────────────────┘
     │
     │       WEATHER?                         GENERAL?
     │           │                                │
     │           ▼                                ▼
     │   ┌───────────────┐              ┌─────────────────────┐
     │   │ get_weather() │              │  Qwen3-4B LLM       │
     │   │ OpenWeatherMap│              │  (4-bit quantized)  │
     │   │ API           │              │  via HuggingFace    │
     │   └───────────────┘              │  pipeline           │
     │                                  └─────────────────────┘
     │
     └──────────────────────────────────────────────┐
                                                    ▼
                                         ┌──────────────────────┐
                                         │  Edge TTS            │
                                         │  Text → MP3 Audio    │
                                         └──────────┬───────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │  WebSocket Broadcast │
                                         │  { audio_url, text } │
                                         └──────────┬───────────┘
                                                    │
                                                    ▼
                                         ┌──────────────────────┐
                                         │  news/test.js        │
                                         │  ws.onmessage fires  │
                                         │  audioPlayer.play()  │
                                         │  → User hears reply  │
                                         └──────────────────────┘
```

---

## Component Breakdown

### `news/index.html` — User Interface

The entry point for the application. Opened in a browser by the elderly user. Contains:
- A **"Talk" button** — starts a 5-second recording session when clicked
- An **"Enable Sound" button** — unlocks browser audio autoplay (required on first visit)
- A fullscreen background video (`itachi.mp4`) that pauses while listening
- Loads `news/test.js` for all interaction logic

### `news/test.js` — Frontend Logic

Handles all client-side behaviour:
- Opens a **WebSocket** connection to `/ws` on page load to receive AI responses
- On Talk button click: captures microphone audio via `MediaRecorder` for 5 seconds, then POSTs the `.webm` blob to `/ask_voice`
- On WebSocket message: sets `audioPlayer.src` to the returned MP3 URL and plays it automatically
- Manages audio unlock state in `localStorage` to persist across page refreshes

### `sst.py` — FastAPI Server & Orchestrator

The main entry point. Handles:
- Receiving audio uploads via `POST /ask_voice`
- Running Whisper STT to transcribe audio
- Calling `process_text()` to get a response
- Generating TTS audio with Edge TTS
- Broadcasting the result to all connected WebSocket clients
- Running the background reminder checker thread

### `model_logic.py` — Intent Router & LLM

- Loads the **Qwen3-4B** model with 4-bit quantization (BitsAndBytes `nf4`)
- Classifies user input using regex patterns into one of:
  - `EMERGENCY`, `REMINDER_SET`, `WEATHER`, `GENERAL`
- Routes to the appropriate handler
- For `GENERAL` queries, formats a chat template and generates a response via the pipeline

### `reminder.py` — Reminder Extraction

- Parses reminder requests using regex patterns
- Extracts **task** (what to do) and **time** (when) from natural language
- Saves reminders to `reminder.json`, sorted by time

### `pushnotification.py` — Pushover Notifications

- Sends **emergency alerts** with a hardcoded location message via [Pushover](https://pushover.net)
- Sends **reminder notifications** to the caretaker's device at the scheduled time

### `weather.py` — Weather Module

- Queries the OpenWeatherMap API for current weather in a given city
- Returns a short, human-readable weather sentence (e.g., "It is 22°C. The weather is light rain.")

---

## File Structure

```
project/
│
├── news/                   # Frontend — user entry point
│   ├── index.html          # Browser UI (Talk button, Enable Sound button)
│   ├── test.js             # Recording, WebSocket, audio playback logic
│   └── itachi.mp4          # Background video (not committed if large)
│
├── sst.py                  # FastAPI server, STT, TTS, WebSocket
├── model_logic.py          # Intent classification, LLM, routing
├── reminder.py             # Reminder extraction & JSON storage
├── pushnotification.py     # Pushover emergency & reminder alerts
├── weather.py              # OpenWeatherMap API integration
│
├── reminder.json           # Persisted reminder list (runtime)
├── keys.py                 # API keys (Pushover token & user) — NOT committed
│
├── audio/                  # Temporary TTS output files
│   └── <uuid>.mp3
│
└── model/                  # Cached Qwen3-4B model weights
    └── ...
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- CUDA-capable GPU (recommended for Qwen3-4B 4-bit inference)
- `ffmpeg` installed (required by Whisper)

### Install Dependencies

```bash
pip install torch transformers bitsandbytes accelerate
pip install fastapi uvicorn python-multipart
pip install openai-whisper edge-tts
pip install requests geocoder
```

### Create `keys.py`

```python
# keys.py
token = "your_pushover_app_token"
user  = "your_pushover_user_key"
```

> ⚠️ Never commit `keys.py` to version control. Add it to `.gitignore`.

### Initialize `reminder.json`

```bash
echo "[]" > reminder.json
```

### Run the Server

```bash
uvicorn sst:app --host 0.0.0.0 --port 8000
```

### Open the Frontend

Open `news/index.html` directly in a browser, or serve the `news/` folder via any static file server:

```bash
cd news
python -m http.server 3000
# Then visit http://localhost:3000
```



---

## Configuration

| Parameter | Location | Description |
|-----------|----------|-------------|
| WebSocket URL | `news/test.js` | `wss://` tunnel URL for `/ws` connection |
| Fetch URL | `news/test.js` | `https://` tunnel URL for `/ask_voice` POST |
| `model_name` | `model_logic.py` | HuggingFace model ID (`Qwen/Qwen3-4B`) |
| `cache_dir` | `model_logic.py` | Local path to cache model weights |
| `VOICE` | `sst.py` | Edge TTS voice (`en-GB-ThomasNeural`) |
| `city` | `weather.py` | Default city for weather (`Kathmandu`) |
| `REMINDER_JSON` | `sst.py` | Path to reminder storage file |
| `audio_url` | `sst.py` | Public base URL for serving audio files (Cloudflare tunnel) |

---



## Intent Classification

Intent is determined by `user_input_label()` in `model_logic.py` using regex pattern matching (no ML classifier).

```
┌──────────────────────┬──────────────────────────────────────────────────────┐
│ Label                │ Example Phrases                                      │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ EMERGENCY            │ "I can't breathe", "chest pain", "I fell",          │
│                      │ "help me", "dizzy", "I am bleeding"                  │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ REMINDER_SET         │ "remind me to", "set a reminder", "don't forget"     │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ WEATHER              │ "what's the weather", "will it rain",                │
│                      │ "how hot is it", "what is today's weather"           │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ GENERAL              │ Everything else — routed to Qwen3-4B LLM            │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

---

## Reminder System

```
User: "Remind me to take my medicine at 8pm"
                │
                ▼
        extract_task()  →  "take my medicine"
        extract_time()  →  "20:00"
                │
                ▼
        Appended to reminder.json
        (sorted by time)
                │
        Background thread checks every 60 seconds
                │
        When time matches → reminder_notification() via Pushover
```

**`reminder.json` format:**
```json
[
  { "task": "take blood pressure medicine", "time": "08:00" },
  { "task": "drink water",                 "time": "10:00" },
  { "task": "evening walk",                "time": "18:00" }
]
```

---

## Emergency Handling

When an emergency phrase is detected, the system:

1. Immediately returns a calm, pre-written response to the user:
   > *"I am alerting the caretaker now. Please stay calm."*

2. Calls `push_notification()` which sends a high-priority Pushover alert to the registered caretaker device, including the hardcoded location.

> 🔧 **To-do:** Replace the hardcoded location string in `pushnotification.py` with a dynamic value from the user's device or `geocoder`.

---

## Push Notification System

Uses the [Pushover](https://pushover.net) API via HTTPS.

| Function | Trigger | Priority |
|----------|---------|----------|
| `push_notification()` | EMERGENCY intent detected | High (`priority: 1`) |
| `reminder_notification(text)` | Scheduled reminder fires | Normal (default) |

Both functions require `token` and `user` from `keys.py`.

---

## Weather Module

Queries the **OpenWeatherMap** `/data/2.5/weather` endpoint.

- Default city: `Kathmandu`
- Units: metric (°C)
- Returns a plain-English sentence: `"It is 18.5 degree Celsius. The weather is broken clouds."`

> 🔧 The city is currently hardcoded. Consider passing it as a parameter or inferring it from the user's IP using `geocoder`.

---

## LLM Model Details

| Property | Value |
|----------|-------|
| Model | `Qwen/Qwen3-4B` |
| Quantization | 4-bit NF4 (BitsAndBytes) |
| Compute dtype | `float16` |
| Device | `auto` (GPU preferred) |
| Max new tokens | 80 |
| Temperature | 0.3 |
| Top-p | 0.8 |
| Repetition penalty | 1.2 |

The system prompt instructs the model to behave as **HakunaMatata** — a kind, patient virtual caretaker. Responses are limited to 3–5 sentences, free of jargon, emojis, and repeated greetings. A `<think>` tag stripping function (`clean_output()`) removes any chain-of-thought reasoning before returning the response.

---

## Known Limitations

- **Hardcoded location** in `pushnotification.py` — not dynamic per user.
- **Single-user design** — no multi-user session management.
- **City hardcoded** in `weather.py` — no geolocation-based city detection.
- **No authentication** on FastAPI endpoints — any client can POST audio.
- **Reminder time only (no date)** — reminders are daily and reset every minute cycle.
- **Audio files not cleaned up** — `./audio/` will grow indefinitely without a cleanup job.
- **Cloudflare tunnel URL hardcoded** in `news/test.js` — both the WebSocket URL and fetch URL must be updated manually whenever the tunnel restarts.
- **Fixed 5-second recording window** in `news/test.js` — users cannot speak for longer; short or late responses may be cut off.
