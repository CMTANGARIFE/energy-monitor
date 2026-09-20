import { describe, expect, it } from 'vitest'
import { formatBytes, formatCop, formatDate, formatDateTime, formatKwh, formatRate } from '../utils/format'

describe('formato es-CO (Colombia)', () => {
  it('formatCop usa punto como separador de miles', () => {
    expect(formatCop(100320)).toMatch(/100\.320/)
    expect(formatCop(100320)).toMatch(/^\$\s?/)
  })

  it('formatCop maneja valores nulos', () => {
    expect(formatCop(null)).toBe('—')
    expect(formatCop(undefined)).toBe('—')
  })

  it('formatKwh usa coma decimal y sufijo kWh', () => {
    expect(formatKwh(3.52)).toBe('3,52 kWh')
    expect(formatKwh(1234.5)).toBe('1.234,50 kWh')
  })

  it('formatRate diferencia la unidad COP/kWh', () => {
    expect(formatRate('850')).toContain('COP/kWh')
    expect(formatRate('850')).toContain('850')
  })

  it('formatDate convierte ISO a DD/MM/YYYY', () => {
    expect(formatDate('2026-03-24')).toBe('24/03/2026')
    expect(formatDate(null)).toBe('—')
  })

  it('formatDateTime produce fecha y hora', () => {
    const result = formatDateTime('2026-03-24T14:30:00Z')
    expect(result).toMatch(/2026/)
    expect(result).toMatch(/\d{2}:\d{2}/)
  })

  it('formatBytes legible', () => {
    expect(formatBytes(500)).toBe('500 B')
    expect(formatBytes(2048)).toContain('KB')
    expect(formatBytes(3 * 1024 * 1024)).toContain('MB')
  })
})
