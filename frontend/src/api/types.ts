// Tipos que reflejan los esquemas de la API FastAPI.

export interface Device {
  id: number
  name: string
  description: string | null
  image: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export interface DeviceDetail extends Device {
  first_record_date: string | null
  last_record_date: string | null
  total_records: number
  lifetime_kwh: number | null
}

export interface DeviceInput {
  name: string
  description?: string | null
  image?: string | null
}

export interface CsvRowError {
  row: number | null
  field: string | null
  value: string | null
  message: string
}

export interface ImportPreview {
  filename: string
  device_id: number
  device_name: string | null
  records_found: number
  new_records: number
  existing_records: number
  ignored_rows: number
  total_kwh: number
  date_from: string | null
  date_to: string | null
  errors: CsvRowError[]
  valid: boolean
}

export interface ImportResult {
  message: string
  device_id: number
  device_name: string | null
  records_found: number
  records_inserted: number
  records_updated: number
  records_ignored: number
  total_kwh: number
  date_from: string | null
  date_to: string | null
}

export interface ImportHistoryItem {
  id: number
  device_id: number | null
  device_name: string | null
  filename: string
  imported_at: string
  records_found: number
  records_inserted: number
  records_updated: number
  records_ignored: number
  status: 'success' | 'error'
  error_summary: string | null
}

export interface Rate {
  id: number
  start_date: string
  end_date: string | null
  price_per_kwh: string
  created_at: string
  updated_at: string
}

export interface RateInput {
  start_date: string
  end_date: string | null
  price_per_kwh: string
}

export interface DevicePeriodCost {
  device_id: number
  device_name: string
  kwh: number
  cost: number | null
  cost_incomplete: boolean
  days_without_rate: number
}

export interface ConsumptionPoint {
  date: string
  total: number
  values: Record<string, number>
}

export interface ConsumptionSummary {
  date_from: string
  date_to: string
  days: number
  devices_count: number
  total_kwh: number
  avg_daily_kwh: number | null
  max_daily_kwh: number | null
  max_daily_date: string | null
  min_daily_kwh: number | null
  min_daily_date: string | null
  first_data_date: string | null
  last_data_date: string | null
  days_with_data: number
  days_without_data: number
  total_cost: number | null
  cost_incomplete: boolean
  days_without_rate: number
  missing_rate_ranges: string[]
  by_device: DevicePeriodCost[]
}

export interface ConsumptionResponse {
  summary: ConsumptionSummary | null
  series: ConsumptionPoint[]
  per_device: Record<string, { date: string; kwh: number }[]>
  cumulative: { date: string; kwh: number }[]
  by_device: DevicePeriodCost[]
  cost_series: { date: string; cost: number | null }[]
}

export interface DeviceStats {
  device_id: number
  device_name: string
  date_from: string
  date_to: string
  total_kwh: number
  avg_daily_kwh: number | null
  max_daily_kwh: number | null
  max_daily_date: string | null
  min_daily_kwh: number | null
  min_daily_date: string | null
  estimated_cost: number | null
  cost_incomplete: boolean
  days_without_rate: number
  first_recorded_day: string | null
  last_recorded_day: string | null
  days_with_data: number
  days_without_data: number
}

export interface DeviceConsumptionResponse {
  device: Pick<Device, 'id' | 'name' | 'active' | 'description' | 'image'>
  stats: DeviceStats
  series: { date: string; kwh: number }[]
}

export interface SettingsInfo {
  app_name: string
  version: string
  currency: string
  max_csv_size_mb: number
  database_engine: string
  pdf_logo_available: boolean
  default_device_image: string
}

export interface SettingsStats {
  devices: number
  consumption_records: number
  rates: number
  imports: number
}

export interface HealthInfo {
  status: string
  database: string
  app: string
  version: string
}
