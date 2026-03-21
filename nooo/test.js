// =======================
// AUDIO SETUP (GLOBAL)
// =======================
const audioPlayer = new Audio();
audioPlayer.autoplay = true;

let audioUnlocked = localStorage.getItem("audioUnlocked") === "true";

// =======================
// HARDCODED SERVER (HTTPS)
// =======================
const ws = new WebSocket("wss://shepherd-bedrooms-requires-calibration.trycloudflare.com/ws");

// =======================
// WEBSOCKET
// =======================
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "audio") {
        audioPlayer.src = data.url;

        audioPlayer.play().catch(() => {
            showEnableButton();
        });

        console.log("AI:", data.text);
    }
};

// =======================
// VIDEO
// =======================
const video = document.getElementById("video");

// =======================
// BUTTONS
// =======================
const talkBtn = document.getElementById("button");

const enableBtn = document.createElement("button");
enableBtn.textContent = "🔊 Enable Sound";
enableBtn.style.fontSize = "1.2rem";
enableBtn.style.padding = "12px 30px";
enableBtn.style.display = audioUnlocked ? "none" : "block";

document.querySelector(".container").appendChild(enableBtn);

// =======================
// UNLOCK AUDIO
// =======================
async function unlockAudio() {
    try {
        audioPlayer.src = "";
        await audioPlayer.play();
        audioUnlocked = true;
        localStorage.setItem("audioUnlocked", "true");
        enableBtn.style.display = "none";
    } catch {}
}

enableBtn.onclick = unlockAudio;
talkBtn.addEventListener("click", unlockAudio);

// =======================
// MIC RECORDING
// =======================
let audioStream = null;

talkBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!video.paused) video.pause();

    try {
        if (!audioStream) {
            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        }

        const recorder = new MediaRecorder(audioStream, {
            mimeType: "audio/webm"
        });

        const chunks = [];
        recorder.ondataavailable = e => chunks.push(e.data);

        recorder.onstop = async () => {
            const blob = new Blob(chunks, { type: "audio/webm" });
            const formData = new FormData();
            formData.append("audio", blob, "voice.webm");

            await fetch("https://shepherd-bedrooms-requires-calibration.trycloudflare.com/ask_voice", {
                method: "POST",
                body: formData
            });
        };

        recorder.start();
        talkBtn.disabled = true;
        talkBtn.textContent = "🎙 Listening...";

        setTimeout(() => {
            recorder.stop();
            talkBtn.disabled = false;
            talkBtn.textContent = "▶️ Talk";
        }, 5000);

    } catch (err) {
        console.error(err);
    }
});

// =======================
// HELPERS
// =======================
function showEnableButton() {
    enableBtn.style.display = "block";
}
