"""SignSetu backend: one local process, one job.

  GET  /              serves the front end
  POST /api/predict   landmarks in -> prediction out (shared contract)
  POST /api/predict_word  1-2 hands per frame -> ISL word (trained model, sliding window)
  POST /api/reset     clear a session (called when the camera stops)
  GET  /api/health    status + supported classes (single source of truth)

CAMERA OWNERSHIP: the BROWSER owns the webcam (MediaPipe Hands runs there).
This server never opens a camera, so nothing competes for it. Only 21 hand
points per frame go to localhost - no video ever leaves the browser.
"""
import argparse
import json
import logging
import math
import os
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

from . import recognizer, words
from .stabilizer import Stabilizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")


def load_config(path=None):
    with open(path or os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def _valid_landmarks(lm):
    if not isinstance(lm, list) or len(lm) != 21:
        return False
    for p in lm:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            return False
        for v in p[:3]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                return False
    return True


def create_app(config=None):
    cfg = config or load_config()
    import mimetypes
    mimetypes.add_type("application/wasm", ".wasm")
    app = Flask(__name__, static_folder=None)
    sessions = {}
    wsessions = {}
    lock = threading.Lock()
    try:
        word_model = words.WordModel()
    except (OSError, ValueError, KeyError, AssertionError):  # words are optional: shapes keep working
        word_model = None

    def get_session(sid):  # caller must hold `lock`
        now = time.time()
        for k in [k for k, (_, t) in sessions.items() if now - t > cfg["session_ttl_seconds"]]:
            del sessions[k]
        if sid not in sessions:
            if len(sessions) >= cfg["max_sessions"]:
                del sessions[min(sessions, key=lambda k: sessions[k][1])]
            sessions[sid] = (Stabilizer(cfg["hold_frames"], cfg["cooldown_frames"],
                                        cfg["rearm_no_hand_frames"]), now)
        stab, _ = sessions[sid]
        sessions[sid] = (stab, now)
        return stab

    def error(code, message, status=400):
        return jsonify({"error": code, "message": message}), status

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND, "index.html")

    @app.get("/vendor/<path:name>")
    def vendor(name):  # MediaPipe files, served locally so the camera works without internet
        return send_from_directory(os.path.join(FRONTEND, "vendor"), name)

    @app.get("/api/health")
    def health():
        return jsonify({
            "ok": True,
            "model": recognizer.LABELS["model"],
            "classes": list(recognizer.CLASSES),
            "words": list(word_model.words) if word_model else [],
            "hold_frames": cfg["hold_frames"],
        })

    @app.after_request
    def cors(resp):  # lets the page work if opened from file:// during a demo scramble
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    @app.route("/api/predict", methods=["OPTIONS"])
    @app.route("/api/predict_word", methods=["OPTIONS"])
    @app.route("/api/reset", methods=["OPTIONS"])
    def preflight():
        return ("", 204)

    @app.post("/api/predict")
    def predict():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error("bad_json", "Body must be a JSON object")
        sid = str(body.get("session") or "")[:64]
        if not sid:
            return error("no_session", "Missing 'session'")
        lm = body.get("landmarks")
        if lm is not None and not _valid_landmarks(lm):
            return error("bad_landmarks", "'landmarks' must be null or 21 [x, y, z] points")
        pred = recognizer.predict(lm, cfg["min_confidence"])
        with lock:
            out = get_session(sid).update(pred)
        return jsonify(out)

    def get_word_session(sid):  # caller must hold `lock`
        now = time.time()
        for k in [k for k, (_, t) in wsessions.items() if now - t > cfg["session_ttl_seconds"]]:
            del wsessions[k]
        if sid not in wsessions:
            if len(wsessions) >= cfg["max_sessions"]:
                del wsessions[min(wsessions, key=lambda k: wsessions[k][1])]
            ws = words.WordSession(word_model, cfg["word_window_ms"], cfg["word_min_span_ms"],
                                   cfg["word_max_distance"], cfg["word_min_margin"],
                                   cfg["word_rearm_no_hand_frames"])
            st = Stabilizer(cfg["word_hold_frames"], cfg["word_cooldown_frames"],
                            cfg["word_rearm_no_hand_frames"])
            wsessions[sid] = ((ws, st), now)
        pair, _ = wsessions[sid]
        wsessions[sid] = (pair, now)
        return pair

    @app.post("/api/predict_word")
    def predict_word():
        """{session, t (ms), hands: [landmarks21, ...up to 2] | null} -> same contract as /api/predict."""
        if word_model is None:
            return error("no_word_model", "Word model file is missing on the server", 503)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return error("bad_json", "Body must be a JSON object")
        sid = str(body.get("session") or "")[:64]
        if not sid:
            return error("no_session", "Missing 'session'")
        hands = body.get("hands")
        if hands is not None:
            if not isinstance(hands, list) or len(hands) > 2 or not all(_valid_landmarks(h) for h in hands):
                return error("bad_landmarks", "'hands' must be null or a list of up to 2 hands of 21 [x, y, z] points")
        t = body.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            t = time.time() * 1000.0
        with lock:
            ws, st = get_word_session(sid)
            out = st.update(ws.update(hands, t))
        return jsonify(out)

    @app.post("/api/reset")
    def reset():
        body = request.get_json(silent=True) or {}
        sid = str(body.get("session") or "")[:64]
        if sid:
            with lock:
                get_session(sid).reset()
                if word_model is not None:
                    ws, st = get_word_session(sid)
                    ws.reset()
                    st.reset()
        return jsonify({"ok": True})

    return app


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description="SignSetu backend")
    ap.add_argument("--port", type=int, default=cfg["port"])
    ap.add_argument("--host", default=cfg["host"])
    args = ap.parse_args()
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # no per-frame log spam
    print("\nSignSetu is running.\n  Open  http://localhost:%d  in Chrome\n"
          "  (use 'localhost' - browsers only allow the camera there or on https)\n"
          "  Ctrl+C to stop.\n" % args.port)
    create_app(cfg).run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
