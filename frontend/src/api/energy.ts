// Funciones de acceso a la API de Energy Monitor.
import { api } from './client'
import type {
  ConsumptionResponse,
  Device,
  DeviceConsumptionResponse,
  DeviceDetail,
  DeviceInput,
  HealthInfo,
  ImportHistoryItem,
  ImportPreview,
  ImportResult,
  Rate,
  RateInput,
  SettingsInfo,
  SettingsStats,
} from './types'

export const energyApi = {
  // Dispositivos
  listDevices: (activeOnly = false) =>
    api.get<Device[]>('/api/devices', { active_only: activeOnly ? 'true' : 'false' }),
  getDevice: (id: number) => api.get<DeviceDetail>(`/api/devices/${id}`),
  createDevice: (payload: DeviceInput) => api.post<Device>('/api/devices', payload),
  updateDevice: (id: number, payload: Partial<DeviceInput>) =>
    api.put<Device>(`/api/devices/${id}`, payload),
  setDeviceStatus: (id: number, active: boolean) =>
    api.patch<Device>(`/api/devices/${id}/status`, { active }),

  // Importación
  previewImport: (file: File, deviceId: number) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('device_id', String(deviceId))
    return api.upload<ImportPreview>('/api/import/preview', formData)
  },
  runImport: (file: File, deviceId: number) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('device_id', String(deviceId))
    return api.upload<ImportResult>('/api/import', formData)
  },
  listImports: (params?: { device_id?: number; limit?: number; offset?: number }) =>
    api.get<ImportHistoryItem[]>('/api/imports', params),

  // Consumo y dashboard
  consumption: (params: {
    device_ids?: string
    date_from?: string
    date_to?: string
  }) => api.get<ConsumptionResponse>('/api/consumption', params),
  deviceConsumption: (deviceId: number, params: { date_from?: string; date_to?: string }) =>
    api.get<DeviceConsumptionResponse>(`/api/consumption/device/${deviceId}`, params),

  // Tarifas
  listRates: () => api.get<Rate[]>('/api/rates'),
  createRate: (payload: RateInput) => api.post<Rate>('/api/rates', payload),
  updateRate: (id: number, payload: Partial<RateInput>) => api.put<Rate>(`/api/rates/${id}`, payload),
  deleteRate: (id: number) => api.delete(`/api/rates/${id}`),

  // Informes
  generatePdf: (payload: { date_from: string; date_to: string; device_ids: number[] | null }) =>
    api.download('/api/reports/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  // Backup / salud / configuración
  downloadBackup: () => api.download('/api/backup'),
  health: () => api.get<HealthInfo>('/health'),
  settingsInfo: () => api.get<SettingsInfo>('/api/settings/info'),
  settingsStats: () => api.get<SettingsStats>('/api/settings/stats'),
}
