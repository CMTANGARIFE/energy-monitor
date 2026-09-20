// Formato de números y fechas para Colombia (es-CO).
// Diferenciación clara entre kWh (energía) y COP (moneda).

const copFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
})

const kwhFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const kwhShortFormatter = new Intl.NumberFormat('es-CO', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

/** Formatea COP: $ 1.234.567 */
export function formatCop(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return copFormatter.format(value)
}

/** Formatea energía: 1.234,56 kWh */
export function formatKwh(value: number | null | undefined, short = false): string {
  if (value === null || value === undefined) return '—'
  const fmt = short ? kwhShortFormatter : kwhFormatter
  return `${fmt.format(value)} kWh`
}

/** Formatea tarifa: 850 COP/kWh */
export function formatRate(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return '—'
  return `${kwhShortFormatter.format(num)} COP/kWh`
}

/** Formatea tarifa monetaria del precio: $ 850 */
export function formatPrice(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return '—'
  return copFormatter.format(num)
}

/** ISO yyyy-mm-dd → DD/MM/YYYY */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [year, month, day] = iso.slice(0, 10).split('-')
  if (!year || !month || !day) return iso
  return `${day}/${month}/${year}`
}

/** Fecha y hora local para auditoría (createdAt/imported_at UTC → local). */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('es-CO', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Número de bytes legible: 1,2 MB */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kwhShortFormatter.format(kb)} KB`
  return `${kwhShortFormatter.format(kb / 1024)} MB`
}
