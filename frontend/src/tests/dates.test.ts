import { describe, expect, it } from 'vitest'
import { resolveQuickRange, scanCsvText } from '../utils/dates'

describe('rangos rápidos de fecha (sección 52)', () => {
  it('Hoy devuelve el mismo día', () => {
    const range = resolveQuickRange('today')
    expect(range).not.toBeNull()
    expect(range!.from).toBe(range!.to)
  })

  it('Últimos 7 días cubre 7 fechas', () => {
    const range = resolveQuickRange('last7')!
    const from = new Date(range.from)
    const to = new Date(range.to)
    const diff = (to.getTime() - from.getTime()) / 86400000
    expect(diff).toBe(6)
  })

  it('Este mes empieza el día 1', () => {
    const range = resolveQuickRange('thisMonth')!
    expect(range.from.endsWith('-01')).toBe(true)
  })

  it('Mes anterior termina el último día del mes previo', () => {
    const range = resolveQuickRange('lastMonth')!
    const end = new Date(range.to)
    const next = new Date(end)
    next.setDate(end.getDate() + 1)
    expect(next.getDate()).toBe(1) // el día siguiente es día 1 → fin de mes correcto
  })

  it('Personalizado devuelve null (el usuario controla las fechas)', () => {
    expect(resolveQuickRange('custom')).toBeNull()
  })
})

describe('escaneo ligero de CSV en el navegador', () => {
  it('cuenta filas diarias, filas total y suma kWh', () => {
    const csv = 'date,kwh,cost\n2026/03/24,2.34,0\n2026/03/25,1.18,0\ntotal,3.52,0\n'
    const scan = scanCsvText(csv)
    expect(scan.dailyRows).toBe(2)
    expect(scan.totalRows).toBe(1)
    expect(scan.totalKwh).toBeCloseTo(3.52)
    expect(scan.periodFrom).toBe('2026/03/24')
    expect(scan.periodTo).toBe('2026/03/25')
  })

  it('cero es un valor válido, no inválido', () => {
    const scan = scanCsvText('date,kwh,cost\n2026/03/15,0,0\n')
    expect(scan.dailyRows).toBe(1)
    expect(scan.invalidRows).toBe(0)
  })
})
