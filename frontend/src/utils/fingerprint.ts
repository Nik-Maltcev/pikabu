/**
 * Browser fingerprint generator.
 * Combines canvas, WebGL, screen, timezone and other stable signals
 * to produce a consistent hash that persists across sessions (including incognito).
 */

async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message)
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

function getCanvasFingerprint(): string {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 200
    canvas.height = 50
    const ctx = canvas.getContext('2d')
    if (!ctx) return ''

    // Draw text with specific styling
    ctx.textBaseline = 'top'
    ctx.font = '14px Arial'
    ctx.fillStyle = '#f60'
    ctx.fillRect(125, 1, 62, 20)
    ctx.fillStyle = '#069'
    ctx.fillText('NicheFind.fp', 2, 15)
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)'
    ctx.fillText('NicheFind.fp', 4, 17)

    // Add some geometric shapes
    ctx.beginPath()
    ctx.arc(50, 50, 50, 0, Math.PI * 2, true)
    ctx.closePath()
    ctx.fill()

    return canvas.toDataURL()
  } catch {
    return ''
  }
}

function getWebGLFingerprint(): string {
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
    if (!gl) return ''

    const webgl = gl as WebGLRenderingContext
    const debugInfo = webgl.getExtension('WEBGL_debug_renderer_info')
    if (!debugInfo) return ''

    const vendor = webgl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || ''
    const renderer = webgl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || ''
    return `${vendor}~${renderer}`
  } catch {
    return ''
  }
}

function getScreenFingerprint(): string {
  return [
    screen.width,
    screen.height,
    screen.colorDepth,
    window.devicePixelRatio || 1,
  ].join('x')
}

function getTimezoneFingerprint(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
}

function getLanguageFingerprint(): string {
  return navigator.language || ''
}

function getPlatformFingerprint(): string {
  return navigator.platform || ''
}

function getHardwareConcurrency(): string {
  return String(navigator.hardwareConcurrency || '')
}

/**
 * Generate a stable browser fingerprint hash.
 * Returns a hex SHA-256 string (64 chars).
 */
export async function generateFingerprint(): Promise<string> {
  const components = [
    getCanvasFingerprint(),
    getWebGLFingerprint(),
    getScreenFingerprint(),
    getTimezoneFingerprint(),
    getLanguageFingerprint(),
    getPlatformFingerprint(),
    getHardwareConcurrency(),
  ]

  const raw = components.join('|||')
  return sha256(raw)
}
