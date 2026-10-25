import { useCallback, useEffect, useRef, useState } from 'react'
import type { HandLandmarker } from '@mediapipe/tasks-vision'
import { createHandLandmarker, drawHands } from '../lib/mediapipe'

type Status = 'idle' | 'loading' | 'running' | 'error'

export function CameraPanel() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const landmarkerRef = useRef<HandLandmarker | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const rafRef = useRef(0)
  const lastTsRef = useRef(0)
  const startGenRef = useRef(0)

  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [handSummary, setHandSummary] = useState('No hands yet')

  const tickRef = useRef<() => void>(() => {})

  const stopLoop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = 0
  }, [])

  useEffect(() => {
    tickRef.current = () => {
      const video = videoRef.current
      const canvas = canvasRef.current
      const landmarker = landmarkerRef.current
      if (!video || !canvas || !landmarker || video.readyState < 2) {
        rafRef.current = requestAnimationFrame(() => tickRef.current())
        return
      }

      const w = video.videoWidth
      const h = video.videoHeight
      if (canvas.width !== w) canvas.width = w
      if (canvas.height !== h) canvas.height = h

      const now = performance.now()
      if (now > lastTsRef.current) {
        lastTsRef.current = now
        try {
          const result = landmarker.detectForVideo(video, now)
          const ctx = canvas.getContext('2d')
          if (ctx) drawHands(ctx, result, w, h)

          if (result.landmarks.length === 0) {
            setHandSummary('No hands')
          } else {
            const parts = result.handedness.map((h, i) => {
              const cat = h[0]
              const label = cat?.displayName || cat?.categoryName || 'Hand'
              const pct = Math.round((cat?.score ?? 0) * 100)
              return `${label} ${pct}% (${result.landmarks[i]?.length ?? 0} pts)`
            })
            setHandSummary(parts.join(' · '))
          }
        } catch {
          // MediaPipe rejects timestamps that do not strictly increase; skip frame.
        }
      }

      rafRef.current = requestAnimationFrame(() => tickRef.current())
    }
  }, [])

  const stopCamera = useCallback(() => {
    startGenRef.current += 1
    stopLoop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    landmarkerRef.current?.close()
    landmarkerRef.current = null
    const video = videoRef.current
    if (video) video.srcObject = null
    setStatus('idle')
    setHandSummary('Camera off')
  }, [stopLoop])

  const startCamera = useCallback(async () => {
    const gen = startGenRef.current + 1
    startGenRef.current = gen
    setError(null)
    setStatus('loading')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      })
      if (startGenRef.current !== gen) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      streamRef.current = stream
      const video = videoRef.current
      if (!video) throw new Error('Video element missing')
      video.srcObject = stream
      await video.play()

      const landmarker = await createHandLandmarker()
      if (startGenRef.current !== gen) {
        landmarker.close()
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      landmarkerRef.current = landmarker
      lastTsRef.current = 0
      setStatus('running')
      rafRef.current = requestAnimationFrame(() => tickRef.current())
    } catch (err) {
      if (startGenRef.current !== gen) return
      stopCamera()
      const message =
        err instanceof Error ? err.message : 'Could not start camera or MediaPipe'
      setError(message)
      setStatus('error')
    }
  }, [stopCamera])

  useEffect(() => () => stopCamera(), [stopCamera])

  return (
    <section className="flex flex-col gap-3 rounded-2xl border-2 border-white/20 bg-[#12151c] p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-white">Camera</h2>
        {status === 'running' ? (
          <button
            type="button"
            onClick={stopCamera}
            className="min-h-12 rounded-xl bg-red-600 px-4 text-base font-semibold text-white hover:bg-red-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-yellow-400"
          >
            Stop
          </button>
        ) : (
          <button
            type="button"
            onClick={startCamera}
            disabled={status === 'loading'}
            className="min-h-12 rounded-xl bg-yellow-400 px-4 text-base font-semibold text-black hover:bg-yellow-300 disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-yellow-400"
          >
            {status === 'loading' ? 'Starting…' : 'Start camera'}
          </button>
        )}
      </div>

      {/* Mirrored so it feels like a mirror; video + overlay share the flip. */}
      <div className="relative aspect-video overflow-hidden rounded-xl bg-black">
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full -scale-x-100 object-cover"
          playsInline
          muted
          aria-label="Webcam preview"
        />
        <canvas
          ref={canvasRef}
          className="pointer-events-none absolute inset-0 h-full w-full -scale-x-100"
          aria-hidden
        />
        {status !== 'running' && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-lg text-white/80">
            {status === 'loading'
              ? 'Loading hand model…'
              : 'Allow camera access to see hand landmarks'}
          </p>
        )}
      </div>

      <p className="rounded-lg bg-black px-3 py-2 font-mono text-sm text-yellow-300" aria-live="polite">
        {handSummary}
      </p>
      {error && (
        <p className="text-base text-red-400" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
