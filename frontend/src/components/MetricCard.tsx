export function MetricCard({ label, value, unit, accent = 'slate' }: {
  label: string; value: string | number; unit?: string; accent?: 'amber' | 'cyan' | 'rose' | 'slate'
}) {
  const color = { amber: 'text-amber-400', cyan: 'text-cyan-400', rose: 'text-rose-400', slate: 'text-slate-100' }[accent]
  return (
    <div className="panel px-4 py-3">
      <div className={`font-data text-2xl ${color}`}>
        {value}{unit && <span className="text-sm text-slate-500 ml-1">{unit}</span>}
      </div>
      <div className="text-[12px] text-slate-400 mt-1">{label}</div>
    </div>
  )
}
