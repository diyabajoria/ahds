export function NumberField({ label, value, onChange, step = 1, min, max }: {
  label: string; value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number
}) {
  return (
    <label className="block text-[12px] text-slate-400 mb-2">
      <span className="block mb-1">{label}</span>
      <input
        type="number" value={value} step={step} min={min} max={max}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full px-2 py-1.5 text-sm font-data"
      />
    </label>
  )
}

export function SelectField({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]
}) {
  return (
    <label className="block text-[12px] text-slate-400 mb-2">
      <span className="block mb-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full px-2 py-1.5 text-sm">
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  )
}

export function ToggleField({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between text-[12px] text-slate-400 mb-2 cursor-pointer">
      <span>{label}</span>
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)}
        className="accent-amber-500 w-4 h-4" />
    </label>
  )
}
