# Module notes (for teammates / judges)

- `src/lib/mediapipe.ts` — Loads Hand Landmarker from files in `/public` and draws 21 landmarks per hand.
- `src/components/CameraPanel.tsx` — Webcam, detect loop, landmark overlay, start/stop.
- `src/App.tsx` — Single-page shell: Translate / Train tabs and placeholder panels.
- `scripts/copy-mediapipe.mjs` — Copies MediaPipe WASM from `node_modules` into `public/mediapipe/wasm` on install.
