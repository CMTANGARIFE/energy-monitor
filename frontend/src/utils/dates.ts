// Utilidades de rangos de fecha para los filtros del Dashboard
// (accesos rápidos según sección 52 de la especificación).

export interface DateRange {
  from: string // yyyy-mm-dd
  to: string
}

function toIso(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function today(): Date {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

export const QUICK_RANGES = [
  { id: 'today', label: 'Hoy' },
  { id: 'last7', label: 'Últimos 7 días' },
  { id: 'last30', label: 'Últimos 30 días' },
  { id: 'thisMonth', label: 'Este mes' },
  { id: 'lastMonth', label: 'Mes anterior' },
  { id: 'thisYear', label: 'Este año' },
  { id: 'custom', label: 'Personalizado' },
] as const

export type QuickRangeId = (typeof QUICK_RANGES)[number]['id']

export function resolveQuickRange(id: QuickRangeId): DateRange | null {
  const now = today()
  switch (id) {
    case 'today': {
      const iso = toIso(now)
      return { from: iso, to: iso }
    }
    case 'last7': {
      const start = new Date(now)
      start.setDate(start.getDate() - 6)
      return { from: toIso(start), to: toIso(now) }
    }
    case 'last30': {
      const start = new Date(now)
      start.setDate(start.getDate() - 29)
      return { from: toIso(start), to: toIso(now) }
    }
    case 'thisMonth': {
      const start = new Date(now.getFullYear(), now.getMonth(), 1)
      return { from: toIso(start), to: toIso(now) }
    }
    case 'lastMonth': {
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const end = new Date(now.getFullYear(), now.getMonth(), 0)
      return { from: toIso(start), to: toIso(end) }
    }
    case 'thisYear': {
      const start = new Date(now.getFullYear(), 0, 1)
      return { from: toIso(start), to: toIso(now) }
    }
    default:
      return null
  }
}

/** Escaneo ligero en el navegador para mostrar info del archivo
 * antes de la vista previa autoritativa del backend. */
export interface CsvScan {
  dailyRows: number
  totalRows: number
  invalidRows: number
  totalKwh: number
  periodFrom: string | null
  periodTo: string | null
}

export function scanCsvText(text: string): CsvScan {
  const lines = text.split(/\r?\n/)
  let dailyRows = 0
  let totalRows = 0
  let invalidRows = 0
  let totalKwh = 0
  let periodFrom: string | null = null
  let periodTo: string | null = null

  for (const line of lines) {
    if (!line.trim()) continue
    const cells = line.split(',')
    const dateCell = (cells[0] || '').trim().toLowerCase()
    if (dateCell === 'date' || dateCell === '') continue
    if (dateCell === 'total') {
      totalRows += 1
      continue
    }
    const kwh = parseFloat((cells[1] || '').trim())
    if (Number.isNaN(kwh) || kwh < 0) {
      invalidRows += 1
      continue
    }
    dailyRows += 1
    totalKwh += kwh
    if (!periodFrom || dateCell < periodFrom) periodFrom = dateCell
    if (!periodTo || dateCell > periodTo) periodTo = dateCell
  }

  return { dailyRows, totalRows, invalidRows, totalKwh, periodFrom, periodTo }
}
