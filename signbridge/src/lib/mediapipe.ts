import {
  FilesetResolver,
  HandLandmarker,
  type HandLandmarkerResult,
} from '@mediapipe/tasks-vision'

/** Served from /public so the camera path works without a CDN. */
const WASM_PATH = '/mediapipe/wasm'
const MODEL_PATH = '/models/hand_landmarker.task'

/**
 * Load the Hand Landmarker. Try GPU first, then CPU if the device
 * cannot create a WebGL delegate.
 */
export async function createHandLandmarker(): Promise<HandLandmarker> {
  const fileset = await FilesetResolver.forVisionTasks(WASM_PATH)
  try {
    return await HandLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_PATH, delegate: 'GPU' },
      runningMode: 'VIDEO',
      numHands: 2,
    })
  } catch {
    return await HandLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_PATH, delegate: 'CPU' },
      runningMode: 'VIDEO',
      numHands: 2,
    })
  }
}

/** Draw 21-point skeletons onto a canvas the same size as the video. */
export function drawHands(
  ctx: CanvasRenderingContext2D,
  result: HandLandmarkerResult,
  width: number,
  height: number,
): void {
  ctx.clearRect(0, 0, width, height)
  const connections = HandLandmarker.HAND_CONNECTIONS

  result.landmarks.forEach((hand, index) => {
    const score = result.handedness[index]?.[0]?.score ?? 0
    ctx.strokeStyle = score > 0.7 ? '#F5D90A' : '#9CA3AF'
    ctx.lineWidth = 3
    ctx.lineCap = 'round'

    for (const conn of connections) {
      const a = hand[conn.start]
      const b = hand[conn.end]
      if (!a || !b) continue
      ctx.beginPath()
      ctx.moveTo(a.x * width, a.y * height)
      ctx.lineTo(b.x * width, b.y * height)
      ctx.stroke()
    }

    ctx.fillStyle = '#FFFFFF'
    for (const pt of hand) {
      ctx.beginPath()
      ctx.arc(pt.x * width, pt.y * height, 4, 0, Math.PI * 2)
      ctx.fill()
    }
  })
}

export { HandLandmarker }
