export const SCHEDULERS = ['FCFS', 'SSTF', 'SCAN', 'CSCAN', 'LOOK', 'CLOOK', 'EDF', 'SCAN_EDF', 'DEADLINE', 'HYBRID'] as const
export type SchedulerName = typeof SCHEDULERS[number]

export interface DiskConfig {
  disk_type: 'HDD' | 'SSD'
  cylinders: number
  initial_head: number
  rpm: number
  bytes_per_track: number
  sector_size: number
  seek_model: 'LINEAR' | 'REALISTIC'
  seek_coeff: number
  seek_a: number
  seek_b: number
  ssd_bandwidth: number
}

export interface HybridConfig {
  round_length_ms: number
  rt_fraction: number
  work_conserving: boolean
  control_window_rounds: number
  step: number
  miss_high_threshold: number
  miss_low_threshold: number
  rt_min: number
  rt_max: number
  db_latency_threshold: number | null
  aging_threshold_ms: number
  max_aged_per_round: number
  deadline_tolerance_ms: number
}

export interface WorkloadConfig {
  multimedia: { n_streams: number; bitrate_bytes_per_s: number; request_size_bytes: number; deadline_slack_periods: number; sequentiality: number; arrival_model: string }
  oltp: { n_requests: number; min_size_bytes: number; max_size_bytes: number; zipf_s: number; read_ratio: number; arrival_rate_per_s: number; arrival_model: string }
  olap: { n_scans: number; scan_length_cylinders: number; arrival_rate_per_s: number; arrival_model: string }
  rt_be_mix: number
  load_intensity_pct: number
  seed: number
}

export interface SimulationConfig {
  scheduler: SchedulerName
  disk: DiskConfig
  workload: WorkloadConfig
  hybrid: HybridConfig
  direction: 'LEFT' | 'RIGHT'
}

export const DEFAULT_DISK: DiskConfig = {
  disk_type: 'HDD', cylinders: 500, initial_head: 250, rpm: 7200,
  bytes_per_track: 1048576, sector_size: 4096, seek_model: 'LINEAR',
  seek_coeff: 0.15, seek_a: 1.5, seek_b: 0.6, ssd_bandwidth: 2000,
}

export const DEFAULT_HYBRID: HybridConfig = {
  round_length_ms: 100, rt_fraction: 0.5, work_conserving: true,
  control_window_rounds: 5, step: 0.05, miss_high_threshold: 0.02,
  miss_low_threshold: 0.0, rt_min: 0.1, rt_max: 0.9, db_latency_threshold: null,
  aging_threshold_ms: 200, max_aged_per_round: 1, deadline_tolerance_ms: 5,
}

export const DEFAULT_WORKLOAD: WorkloadConfig = {
  multimedia: { n_streams: 4, bitrate_bytes_per_s: 500000, request_size_bytes: 8192, deadline_slack_periods: 2, sequentiality: 0.85, arrival_model: 'PERIODIC' },
  oltp: { n_requests: 200, min_size_bytes: 4096, max_size_bytes: 16384, zipf_s: 1.1, read_ratio: 0.7, arrival_rate_per_s: 50, arrival_model: 'POISSON' },
  olap: { n_scans: 10, scan_length_cylinders: 40, arrival_rate_per_s: 1, arrival_model: 'POISSON' },
  rt_be_mix: 0.5, load_intensity_pct: 50, seed: 42,
}

export const DEFAULT_CONFIG: SimulationConfig = {
  scheduler: 'HYBRID', disk: DEFAULT_DISK, workload: DEFAULT_WORKLOAD, hybrid: DEFAULT_HYBRID, direction: 'RIGHT',
}
