/** Short, locally synthesized bell cue; no downloaded sound asset or network request. */
export function playBell(scene, volume = 35) {
  const AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext
  if (!AudioContextClass) return null
  let context
  try {
    context = new AudioContextClass()
    const strikes = scene === 'day' ? [0, 0.48] : [0]
    const base = scene === 'execution' ? 174.6 : scene === 'night' ? 220 : 329.6
    const strength = Math.max(0, Math.min(1, Number(volume) / 100)) * 0.15
    for (const delay of strikes) {
      for (const [ratio, weight] of [[1, 1], [2, 0.4], [2.41, 0.24], [3.18, 0.11]]) {
        const oscillator = context.createOscillator()
        const gain = context.createGain()
        oscillator.type = 'sine'
        oscillator.frequency.value = base * ratio
        gain.gain.setValueAtTime(Math.max(0.0001, strength * weight), context.currentTime + delay)
        gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + delay + 1.45)
        oscillator.connect(gain).connect(context.destination)
        oscillator.start(context.currentTime + delay)
        oscillator.stop(context.currentTime + delay + 1.5)
      }
    }
    const ready = context.resume
      ? Promise.resolve(context.resume()).then(() => context.state === 'running').catch(() => false)
      : Promise.resolve(context.state === 'running')
    return { ready, durationMs: strikes.length > 1 ? 2050 : 1550,
      stop: () => { void context.close().catch(() => {}) } }
  } catch {
    void context?.close?.().catch(() => {})
    return null
  }
}
