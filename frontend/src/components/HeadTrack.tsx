import { useEffect, useRef, useState } from 'react'

interface Event { time: number; head: number; request_id: number | null; event_type: string }

export function HeadTrack({ events, cylinders }: { events: Event[]; cylinders: number }) {
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const rafRef = useRef<number>()

  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const step = (t: number) => {
      if (t - last > 30) {
        setIdx((i) => (i + 1 >= events.length ? 0 : i + 1))
        last = t
      }
      rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current!)
  }, [playing, events.length])

  if (events.length === 0) {
    return <div className="text-slate-500 text-sm py-8 text-center">No timeline data yet — run a simulation.</div>
  }

  const current = events[Math.min(idx, events.length - 1)]
  const pct = (current.head / Math.max(1, cylinders - 1)) * 100

  return (
    <div>
      <div className="relative h-16 rounded-none border hairline bg-ink-950 overflow-hidden">
        <div className="absolute inset-0 flex items-center px-2">
          <div className="w-full h-px bg-ink-600" />
        </div>
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 transition-[left] duration-100"
          style={{ left: `${pct}%` }}
        >
          <div className={`w-3 h-3 rounded-full ${current.event_type === 'service' ? 'bg-amber-500' : 'bg-cyan-400'} shadow-[0_0_12px_2px_rgba(255,158,44,0.6)]`} />
        </div>
      </div>
      <div className="flex items-center justify-between mt-3 text-[12px] font-data text-slate-400">
        <span>cyl 0</span>
        <button
          onClick={() => setPlaying((p) => !p)}
          className="px-3 py-1 border hairline text-slate-200 hover:border-amber-500 hover:text-amber-400"
        >
          {playing ? 'pause' : 'play'}
        </button>
        <span>cyl {cylinders - 1}</span>
      </div>
      <div className="mt-2 text-[12px] font-data text-slate-500">
        t={current.time.toFixed(2)}ms head={current.head} {current.request_id !== null ? `req#${current.request_id}` : '(reposition)'}
      </div>
    </div>
  )
}
