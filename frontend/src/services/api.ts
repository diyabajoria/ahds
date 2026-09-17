const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* ignore */ }
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  schedulers: () => request<{ schedulers: string[] }>('/schedulers'),
  presets: () => request<{ presets: Array<{ key: string; description: string; config: any }> }>('/presets'),
  simulate: (cfg: any) => request<any>('/simulate', { method: 'POST', body: JSON.stringify(cfg) }),
  compare: (body: any) => request<any>('/compare', { method: 'POST', body: JSON.stringify(body) }),
  experiment: (body: any) => request<any>('/experiment/run', { method: 'POST', body: JSON.stringify(body) }),
  classifierTrain: (cfg: any) => request<any>('/classifier/train', { method: 'POST', body: JSON.stringify(cfg) }),
  degradation: (cfg: any, baselineSchedulers: string[], loadStart: number, loadEnd: number, loadStep: number) =>
    request<any>(`/experiment/degradation?load_start=${loadStart}&load_end=${loadEnd}&load_step=${loadStep}`, {
      method: 'POST',
      body: JSON.stringify({ cfg, baseline_schedulers: baselineSchedulers }),
    }),
  admissionCheck: (cfg: any, newBitrate: number, reserved: number[]) =>
    request<any>(`/admission/check?new_bitrate_bytes_per_s=${newBitrate}`, {
      method: 'POST',
      body: JSON.stringify({ ...cfg, reserved_bitrates_bytes_per_s: reserved }),
    }),
  resultCsvUrl: (runId: string) => `${BASE}/results/${runId}/csv`,
  resultJsonUrl: (runId: string) => `${BASE}/results/${runId}/json`,
}
