# SignBridge

Sign-to-speech translator for Indian Sign Language (hackathon demo).

**Now:** webcam + MediaPipe hand landmarks (offline model/WASM from `/public`).  
**Next:** in-browser training, gloss buffer, Gemma 4 polish, reverse conversation.

## Run

```bash
npm install
cp .env.example .env
npm run dev
```

Open the local URL, click **Start camera**, allow the webcam. You should see a yellow skeleton on each hand and a live line like `Right 98% (21 pts)`.

Use `localhost` (not a LAN IP) if the browser blocks `getUserMedia`.

## Licenses (partial — full table in later README pass)

| Tool | License |
| --- | --- |
| MediaPipe Tasks Vision + hand_landmarker | Apache-2.0 |
| React, Vite | MIT |
| Tailwind CSS | MIT |
| Gemma 4 via Gemini API | Google terms / Gemma license |
