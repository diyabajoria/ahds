import { useState } from 'react'
import { api } from '../services/api'
import { DEFAULT_CONFIG, SCHEDULERS, SchedulerName } from '../types'
import { Panel } from '../components/Panel'
import { NumberField, SelectField } from '../components/NumberField'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

const SWEEPABLE = [
  'workload.load_intensity_pct',
  'workload.multimedia.n_streams',
  'workload.oltp.n_requests',
  'hybrid.aging_threshold_ms',
  'hybrid.rt_fraction',
]

export default function ExperimentsPage() {
  const [param, setParam] = useState(SWEEPABLE[0])
  const [start, setStart] = useState(10)
  const [end, setEnd] = useState(100)
  const [step, setStep] = useState(15)
  const [selected, setSelected] = useState<SchedulerName[]>(['FCFS', 'HYBRID'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<any[]>([])

  const [degBaselines, setDegBaselines] = useState<SchedulerName[]>(['SSTF', 'SCAN'])
  const [degLoading, setDegLoading] = useState(false)
  const [degError, setDegError] = useState<string | null>(null)
  const [degResult, setDegResult] = useState<any>(null)

  const toggleDeg = (s: SchedulerName) =>
    setDegBaselines((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s])

  const runDegradation = async () => {
    if (degBaselines.length === 0) { setDegError('select at least one baseline scheduler'); return }
    setDegLoading(true); setDegError(null)
    try {
      const r = await api.degradation(DEFAULT_CONFIG, degBaselines, 20, 100, 20)
      setDegResult(r)
    } catch (e: any) {
      setDegError(e.message || 'Degradation sweep failed')
    } finally {
      setDegLoading(false)
    }
  }

  const toggle = (s: SchedulerName) =>
    setSelected((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s])

  const run = async () => {
    setLoading(true); setError(null)
    try {
      const r = await api.experiment({
        base: DEFAULT_CONFIG,
        sweep: [{ name: param, start, end, step }],
        schedulers: selected,
      })
      setRows(r.rows)
    } catch (e: any) {
      setError(e.message || 'Experiment failed')
    } finally {
      setLoading(false)
    }
  }

  // reshape rows -> [{sweep_value, FCFS: missRatio, HYBRID: missRatio, ...}]
  const byValue: Record<number, any> = {}
  for (const row of rows) {
    byValue[row.sweep_value] ??= { sweep_value: row.sweep_value }
    byValue[row.sweep_value][row.scheduler] = row.metrics.multimedia.deadline_miss_ratio * 100
  }
  const chartData = Object.values(byValue).sort((a: any, b: any) => a.sweep_value - b.sweep_value)
  const colors = ['#ff9e2c', '#4fd1d9', '#ff6b6b', '#8ad1ff', '#c4a5ff', '#7cd992']

  const csv = () => {
    if (rows.length === 0) return
    const header = 'sweep_param,sweep_value,scheduler,miss_ratio,db_p95,head_movement,utilization\n'
    const lines = rows.map((r) =>
      `${r.sweep_param},${r.sweep_value},${r.scheduler},${r.metrics.multimedia.deadline_miss_ratio},${r.metrics.database.response_time.p95},${r.metrics.disk.total_head_movement_cylinders},${r.metrics.disk.utilization}`
    )
    const blob = new Blob([header + lines.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'experiment.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <Panel title="Parameter sweep">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <SelectField label="parameter" value={param} onChange={setParam} options={SWEEPABLE} />
          <NumberField label="start" value={start} onChange={setStart} />
          <NumberField label="end" value={end} onChange={setEnd} />
          <NumberField label="step" value={step} onChange={setStep} />
        </div>
        <div className="flex flex-wrap gap-2 my-4">
          {SCHEDULERS.map((s) => (
            <button key={s} onClick={() => toggle(s)}
              className={`px-3 py-1.5 text-[13px] border font-data ${selected.includes(s) ? 'border-amber-500 text-amber-400' : 'hairline text-slate-400'}`}>
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-3 items-center">
          <button onClick={run} disabled={loading}
            className="px-5 py-2 bg-amber-500 text-ink-950 font-semibold text-sm hover:bg-amber-400 disabled:opacity-50">
            {loading ? 'running sweep…' : 'RUN EXPERIMENT'}
          </button>
          {rows.length > 0 && (
            <button onClick={csv} className="px-4 py-2 border hairline text-slate-300 text-sm hover:border-amber-500">
              export CSV
            </button>
          )}
        </div>
        {error && <div className="text-rose-400 text-[13px] font-data mt-3">{error}</div>}
      </Panel>

      {rows.length > 0 && (
        <>
          <Panel title={`Deadline miss ratio vs ${param}`}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#202b3a" />
                <XAxis dataKey="sweep_value" stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: param, position: 'insideBottom', offset: -5, fill: '#425065', fontSize: 11 }} />
                <YAxis stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: 'miss ratio (%)', angle: -90, position: 'insideLeft', fill: '#425065', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0f151d', border: '1px solid #202b3a', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {selected.map((s, i) => (
                  <Line key={s} type="monotone" dataKey={s} stroke={colors[i % colors.length]} dot={{ r: 3 }} name={s} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Results table">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px] font-data">
                <thead>
                  <tr className="text-slate-500 text-left border-b hairline">
                    <th className="py-1.5 pr-4">{param}</th><th className="pr-4">scheduler</th>
                    <th className="pr-4">miss ratio</th><th className="pr-4">DB p95</th><th className="pr-4">head movement</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-b hairline/50 text-slate-300">
                      <td className="py-1 pr-4">{r.sweep_value}</td>
                      <td className="pr-4 text-amber-400">{r.scheduler}</td>
                      <td className="pr-4">{(r.metrics.multimedia.deadline_miss_ratio * 100).toFixed(1)}%</td>
                      <td className="pr-4">{r.metrics.database.response_time.p95.toFixed(1)}ms</td>
                      <td className="pr-4">{Math.round(r.metrics.disk.total_head_movement_cylinders)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}

      <Panel title="Lead-time-before-degradation">
        <p className="text-[12px] text-slate-500 mb-3">
          Sweeps load intensity from 20% to 100% and reports the load level where HYBRID's
          deadline-miss-ratio advantage over the best static baseline at that load starts shrinking —
          useful for knowing the practical operating range where HYBRID is worth deploying.
        </p>
        <div className="flex flex-wrap gap-2 mb-4">
          {SCHEDULERS.filter((s) => s !== 'HYBRID').map((s) => (
            <button key={s} onClick={() => toggleDeg(s)}
              className={`px-3 py-1.5 text-[13px] border font-data ${degBaselines.includes(s) ? 'border-cyan-400 text-cyan-300' : 'hairline text-slate-400'}`}>
              {s}
            </button>
          ))}
        </div>
        <button onClick={runDegradation} disabled={degLoading}
          className="px-5 py-2 bg-cyan-400 text-ink-950 font-semibold text-sm hover:bg-cyan-300 disabled:opacity-50">
          {degLoading ? 'sweeping load…' : 'RUN DEGRADATION SWEEP'}
        </button>
        {degError && <div className="text-rose-400 text-[13px] font-data mt-3">{degError}</div>}

        {degResult && (
          <div className="mt-5 space-y-4">
            <div className="text-[13px] font-data text-slate-300">
              {degResult.lead_time_load_pct !== null
                ? <>lead time: <span className="text-amber-400">{degResult.lead_time_load_pct}% load</span> — {degResult.note}</>
                : <span className="text-slate-400">{degResult.note}</span>}
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={degResult.points}>
                <CartesianGrid strokeDasharray="3 3" stroke="#202b3a" />
                <XAxis dataKey="load_pct" stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: 'load intensity (%)', position: 'insideBottom', offset: -5, fill: '#425065', fontSize: 11 }} />
                <YAxis stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: 'HYBRID advantage', angle: -90, position: 'insideLeft', fill: '#425065', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#0f151d', border: '1px solid #202b3a', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="advantage" stroke="#ff9e2c" dot={{ r: 3 }} name="advantage (baseline miss - hybrid miss)" />
              </LineChart>
            </ResponsiveContainer>
            <div className="overflow-x-auto">
              <table className="w-full text-[12px] font-data">
                <thead>
                  <tr className="text-slate-500 text-left border-b hairline">
                    <th className="py-1.5 pr-4">load %</th><th className="pr-4">HYBRID miss</th>
                    <th className="pr-4">best baseline</th><th className="pr-4">baseline miss</th><th className="pr-4">advantage</th>
                  </tr>
                </thead>
                <tbody>
                  {degResult.points.map((p: any, i: number) => (
                    <tr key={i} className="border-b hairline/50 text-slate-300">
                      <td className="py-1 pr-4">{p.load_pct}</td>
                      <td className="pr-4">{(p.hybrid_miss_ratio * 100).toFixed(1)}%</td>
                      <td className="pr-4 text-cyan-300">{p.best_baseline}</td>
                      <td className="pr-4">{(p.best_baseline_miss_ratio * 100).toFixed(1)}%</td>
                      <td className={`pr-4 ${p.advantage >= 0 ? 'text-amber-400' : 'text-rose-400'}`}>{(p.advantage * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>
    </div>
  )
}
