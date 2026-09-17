import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { DEFAULT_CONFIG, SCHEDULERS, SimulationConfig } from '../types'
import { Panel } from '../components/Panel'
import { NumberField, SelectField, ToggleField } from '../components/NumberField'
import { MetricCard } from '../components/MetricCard'
import { HeadTrack } from '../components/HeadTrack'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar,
} from 'recharts'

export default function SimulationPage() {
  const [cfg, setCfg] = useState<SimulationConfig>(DEFAULT_CONFIG)
  const [presets, setPresets] = useState<Array<{ key: string; description: string; config: any }>>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [classifier, setClassifier] = useState<any>(null)
  const [classifierLoading, setClassifierLoading] = useState(false)
  const [classifierError, setClassifierError] = useState<string | null>(null)

  useEffect(() => {
    api.presets().then((r) => setPresets(r.presets)).catch(() => {})
  }, [])

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await api.simulate(cfg)
      setResult(r)
    } catch (e: any) {
      setError(e.message || 'Simulation failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const trainClassifier = async () => {
    setClassifierLoading(true); setClassifierError(null)
    try {
      const r = await api.classifierTrain(cfg)
      setClassifier(r)
    } catch (e: any) {
      setClassifierError(e.message || 'Classifier training failed')
      setClassifier(null)
    } finally {
      setClassifierLoading(false)
    }
  }

  const applyPreset = (key: string) => {
    const p = presets.find((p) => p.key === key)
    if (p) setCfg(p.config)
  }

  const m = result?.metrics

  const feedbackLog: any[] = m?.hybrid?.feedback_log ?? []

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
      <div className="space-y-4">
        <Panel title="Preset">
          <select
            className="w-full px-2 py-1.5 text-sm"
            onChange={(e) => e.target.value && applyPreset(e.target.value)}
            defaultValue=""
          >
            <option value="" disabled>choose a demo configuration…</option>
            {presets.map((p) => <option key={p.key} value={p.key}>{p.key.replace(/_/g, ' ')}</option>)}
          </select>
        </Panel>

        <Panel title="Scheduler">
          <SelectField label="algorithm" value={cfg.scheduler}
            onChange={(v) => setCfg({ ...cfg, scheduler: v as any })} options={[...SCHEDULERS]} />
          <SelectField label="initial sweep direction" value={cfg.direction}
            onChange={(v) => setCfg({ ...cfg, direction: v as any })} options={['LEFT', 'RIGHT']} />
        </Panel>

        <Panel title="Disk">
          <SelectField label="type" value={cfg.disk.disk_type}
            onChange={(v) => setCfg({ ...cfg, disk: { ...cfg.disk, disk_type: v as any } })} options={['HDD', 'SSD']} />
          <NumberField label="cylinders" value={cfg.disk.cylinders}
            onChange={(v) => setCfg({ ...cfg, disk: { ...cfg.disk, cylinders: v } })} />
          <NumberField label="initial head" value={cfg.disk.initial_head}
            onChange={(v) => setCfg({ ...cfg, disk: { ...cfg.disk, initial_head: v } })} />
          <NumberField label="RPM" value={cfg.disk.rpm}
            onChange={(v) => setCfg({ ...cfg, disk: { ...cfg.disk, rpm: v } })} />
        </Panel>

        <Panel title="Workload">
          <NumberField label="multimedia streams" value={cfg.workload.multimedia.n_streams}
            onChange={(v) => setCfg({ ...cfg, workload: { ...cfg.workload, multimedia: { ...cfg.workload.multimedia, n_streams: v } } })} />
          <NumberField label="OLTP requests" value={cfg.workload.oltp.n_requests}
            onChange={(v) => setCfg({ ...cfg, workload: { ...cfg.workload, oltp: { ...cfg.workload.oltp, n_requests: v } } })} />
          <NumberField label="OLAP scans" value={cfg.workload.olap.n_scans}
            onChange={(v) => setCfg({ ...cfg, workload: { ...cfg.workload, olap: { ...cfg.workload.olap, n_scans: v } } })} />
          <NumberField label="load intensity %" value={cfg.workload.load_intensity_pct} min={10} max={100}
            onChange={(v) => setCfg({ ...cfg, workload: { ...cfg.workload, load_intensity_pct: v } })} />
          <NumberField label="seed" value={cfg.workload.seed}
            onChange={(v) => setCfg({ ...cfg, workload: { ...cfg.workload, seed: v } })} />
        </Panel>

        {cfg.scheduler === 'HYBRID' && (
          <Panel title="Hybrid parameters">
            <NumberField label="round length (ms)" value={cfg.hybrid.round_length_ms}
              onChange={(v) => setCfg({ ...cfg, hybrid: { ...cfg.hybrid, round_length_ms: v } })} />
            <NumberField label="initial rt_fraction" value={cfg.hybrid.rt_fraction} step={0.05} min={0} max={1}
              onChange={(v) => setCfg({ ...cfg, hybrid: { ...cfg.hybrid, rt_fraction: v } })} />
            <NumberField label="aging threshold (ms)" value={cfg.hybrid.aging_threshold_ms}
              onChange={(v) => setCfg({ ...cfg, hybrid: { ...cfg.hybrid, aging_threshold_ms: v } })} />
            <ToggleField label="work conserving" value={cfg.hybrid.work_conserving}
              onChange={(v) => setCfg({ ...cfg, hybrid: { ...cfg.hybrid, work_conserving: v } })} />
          </Panel>
        )}

        <button
          onClick={run}
          disabled={loading}
          className="w-full py-2.5 bg-amber-500 text-ink-950 font-semibold text-sm hover:bg-amber-400 disabled:opacity-50 disabled:cursor-wait"
        >
          {loading ? 'running…' : 'RUN'}
        </button>
        {error && <div className="text-rose-400 text-[13px] font-data border border-rose-400/40 bg-rose-400/5 px-3 py-2">{error}</div>}
      </div>

      <div className="space-y-6">
        <Panel title="Head position">
          <HeadTrack events={result?.timeline_sample ?? []} cylinders={cfg.disk.cylinders} />
        </Panel>

        {m && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <MetricCard label="deadline miss ratio" value={(m.multimedia.deadline_miss_ratio * 100).toFixed(1)} unit="%" accent="rose" />
              <MetricCard label="DB p95 response" value={m.database.response_time.p95.toFixed(1)} unit="ms" accent="cyan" />
              <MetricCard label="head movement" value={Math.round(m.disk.total_head_movement_cylinders)} unit="cyl" accent="amber" />
              <MetricCard label="utilization" value={(m.disk.utilization * 100).toFixed(1)} unit="%" />
              <MetricCard label="Jain fairness" value={m.overall.jain_fairness.toFixed(3)} />
              <MetricCard label="completed" value={m.overall.completed} />
              <MetricCard label="IOPS" value={m.database.iops.toFixed(1)} />
              <MetricCard label="mean jitter" value={m.multimedia.mean_jitter.toFixed(2)} unit="ms" accent="cyan" />
            </div>

            <Panel title="Workload classifier (decision tree vs SVM baseline)">
              <p className="text-[12px] text-slate-500 mb-3">
                Trains a real decision tree — benchmarked against an SVM baseline — to label each
                request multimedia or database from observable features alone (size, inter-arrival
                time, LBA delta, sequential flag, burstiness).
              </p>
              <button onClick={trainClassifier} disabled={classifierLoading}
                className="px-4 py-1.5 border hairline text-slate-200 text-[13px] hover:border-cyan-400 hover:text-cyan-300 disabled:opacity-50">
                {classifierLoading ? 'training…' : 'train on current workload'}
              </button>
              {classifierError && <div className="text-rose-400 text-[13px] font-data mt-3">{classifierError}</div>}
              {classifier && (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={['precision', 'recall', 'f1'].map((metric) => ({
                        metric,
                        decision_tree: classifier.models.decision_tree[metric],
                        svm_baseline: classifier.models.svm_baseline[metric],
                      }))}
                      margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#202b3a" />
                      <XAxis dataKey="metric" stroke="#425065" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 1]} stroke="#425065" tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: '#0f151d', border: '1px solid #202b3a', fontSize: 12 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey="decision_tree" fill="#ff9e2c" name="decision tree" />
                      <Bar dataKey="svm_baseline" fill="#4fd1d9" name="SVM baseline" />
                    </BarChart>
                  </ResponsiveContainer>
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    {Object.entries(classifier.models).map(([name, m]: [string, any]) => (
                      <div key={name} className="border hairline p-3">
                        <div className="text-[13px] text-amber-400 font-data mb-2">{name}</div>
                        <div className="text-[12px] text-slate-400 space-y-1 font-data">
                          <div>precision: <span className="text-slate-200">{m.precision.toFixed(3)}</span></div>
                          <div>recall: <span className="text-slate-200">{m.recall.toFixed(3)}</span></div>
                          <div>f1: <span className="text-slate-200">{m.f1.toFixed(3)}</span></div>
                          <div className="pt-1 text-slate-500">
                            confusion: [[{m.confusion_matrix[0][0]},{m.confusion_matrix[0][1]}],[{m.confusion_matrix[1][0]},{m.confusion_matrix[1][1]}]]
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </Panel>

            {feedbackLog.length > 0 && (
              <Panel title="RT budget adaptation over time (HYBRID feedback controller)">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={feedbackLog}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#202b3a" />
                    <XAxis dataKey="time" stroke="#425065" tick={{ fontSize: 11 }} label={{ value: 'time (ms)', position: 'insideBottom', offset: -5, fill: '#425065', fontSize: 11 }} />
                    <YAxis stroke="#425065" tick={{ fontSize: 11 }} domain={[0, 1]} label={{ value: 'rt_fraction', angle: -90, position: 'insideLeft', fill: '#425065', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#0f151d', border: '1px solid #202b3a', fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="stepAfter" dataKey="rt_fraction" stroke="#ff9e2c" dot={false} name="rt_fraction" />
                    <Line type="monotone" dataKey="miss_ratio" stroke="#ff6b6b" dot={false} name="miss_ratio" />
                  </LineChart>
                </ResponsiveContainer>
              </Panel>
            )}

            <Panel title={`Queue table (first ${result.requests_page.length} of ${result.total_requests})`}>
              <div className="overflow-x-auto">
                <table className="w-full text-[12px] font-data">
                  <thead>
                    <tr className="text-slate-500 text-left border-b hairline">
                      <th className="py-1.5 pr-3">id</th><th className="pr-3">type</th><th className="pr-3">cyl</th>
                      <th className="pr-3">arrival</th><th className="pr-3">complete</th><th className="pr-3">status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.requests_page.slice(0, 30).map((r: any) => (
                      <tr key={r.id} className="border-b hairline/50 text-slate-300">
                        <td className="py-1">{r.id}</td>
                        <td className="pr-3">{r.type}</td>
                        <td className="pr-3">{r.cylinder}</td>
                        <td className="pr-3">{r.arrival_time?.toFixed(1)}</td>
                        <td className="pr-3">{r.completion_time?.toFixed(1) ?? '—'}</td>
                        <td className={r.status === 'MISSED' ? 'text-rose-400' : 'text-slate-400'}>{r.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        )}

        {!m && !loading && (
          <div className="text-slate-500 text-sm py-16 text-center border hairline">
            Configure a workload and press RUN, or pick a preset above.
          </div>
        )}
      </div>
    </div>
  )
}
