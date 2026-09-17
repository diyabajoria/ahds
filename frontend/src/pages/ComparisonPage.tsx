import { useState } from 'react'
import { api } from '../services/api'
import { DEFAULT_CONFIG, SCHEDULERS, SchedulerName } from '../types'
import { Panel } from '../components/Panel'
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ZAxis,
} from 'recharts'

export default function ComparisonPage() {
  const [selected, setSelected] = useState<SchedulerName[]>(['FCFS', 'SSTF', 'LOOK', 'CLOOK', 'HYBRID'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<Array<{ scheduler: string; metrics: any }>>([])

  const toggle = (s: SchedulerName) => {
    setSelected((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s])
  }

  const run = async () => {
    if (selected.length === 0) { setError('select at least one scheduler'); return }
    setLoading(true); setError(null)
    try {
      const r = await api.compare({
        schedulers: selected,
        disk: DEFAULT_CONFIG.disk,
        workload: DEFAULT_CONFIG.workload,
        hybrid: DEFAULT_CONFIG.hybrid,
        direction: DEFAULT_CONFIG.direction,
      })
      setResults(r.results)
    } catch (e: any) {
      setError(e.message || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const scatterData = results.map((r) => ({
    x: r.metrics.database.response_time.p99,
    y: r.metrics.multimedia.deadline_miss_ratio * 100,
    z: 200,
    name: r.scheduler,
  }))

  return (
    <div className="space-y-6">
      <Panel title="Select schedulers to compare (one shared workload)">
        <div className="flex flex-wrap gap-2 mb-4">
          {SCHEDULERS.map((s) => (
            <button
              key={s}
              onClick={() => toggle(s)}
              className={`px-3 py-1.5 text-[13px] border font-data ${selected.includes(s) ? 'border-amber-500 text-amber-400' : 'hairline text-slate-400'}`}
            >
              {s}
            </button>
          ))}
        </div>
        <button onClick={run} disabled={loading}
          className="px-5 py-2 bg-amber-500 text-ink-950 font-semibold text-sm hover:bg-amber-400 disabled:opacity-50">
          {loading ? 'running…' : 'RUN COMPARISON'}
        </button>
        {error && <div className="text-rose-400 text-[13px] font-data mt-3">{error}</div>}
      </Panel>

      {results.length > 0 && (
        <>
          <Panel title="Trade-off: deadline miss ratio vs database p99 response time">
            <p className="text-[12px] text-slate-500 mb-3">
              Lower-left is better on both axes. HYBRID is marked distinctly — if it lands worse than a
              baseline here, that is the honest result of this run, not an annotation error.
            </p>
            <ResponsiveContainer width="100%" height={340}>
              <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#202b3a" />
                <XAxis type="number" dataKey="x" name="DB p99 response time" unit="ms" stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: 'DB p99 response time (ms)', position: 'insideBottom', offset: -10, fill: '#425065', fontSize: 11 }} />
                <YAxis type="number" dataKey="y" name="Deadline miss ratio" unit="%" stroke="#425065" tick={{ fontSize: 11 }}
                  label={{ value: 'Deadline miss ratio (%)', angle: -90, position: 'insideLeft', fill: '#425065', fontSize: 11 }} />
                <ZAxis dataKey="z" range={[80, 200]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#0f151d', border: '1px solid #202b3a', fontSize: 12 }}
                  formatter={(v: any, n: any) => [v, n]}
                  labelFormatter={() => ''} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {scatterData.map((d) => (
                  <Scatter key={d.name} name={d.name} data={[d]}
                    fill={d.name === 'HYBRID' ? '#ff9e2c' : '#4fd1d9'}
                    shape={d.name === 'HYBRID' ? 'star' : 'circle'} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Metric table">
            <div className="overflow-x-auto">
              <table className="w-full text-[12px] font-data">
                <thead>
                  <tr className="text-slate-500 text-left border-b hairline">
                    <th className="py-1.5 pr-4">scheduler</th>
                    <th className="pr-4">head movement</th>
                    <th className="pr-4">miss ratio</th>
                    <th className="pr-4">DB p95</th>
                    <th className="pr-4">DB p99</th>
                    <th className="pr-4">utilization</th>
                    <th className="pr-4">fairness</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.scheduler} className="border-b hairline/50 text-slate-300">
                      <td className="py-1.5 pr-4 text-amber-400">{r.scheduler}</td>
                      <td className="pr-4">{Math.round(r.metrics.disk.total_head_movement_cylinders)}</td>
                      <td className="pr-4">{(r.metrics.multimedia.deadline_miss_ratio * 100).toFixed(1)}%</td>
                      <td className="pr-4">{r.metrics.database.response_time.p95.toFixed(1)}ms</td>
                      <td className="pr-4">{r.metrics.database.response_time.p99.toFixed(1)}ms</td>
                      <td className="pr-4">{(r.metrics.disk.utilization * 100).toFixed(1)}%</td>
                      <td className="pr-4">{r.metrics.overall.jain_fairness.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  )
}
