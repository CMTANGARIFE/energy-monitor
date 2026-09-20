import { useEffect, useState } from 'react'
import type { Device } from '../api/types'
import { energyApi } from '../api/energy'
import { applyQuickRange } from '../components/FilterBar'
import { ErrorAlert, InfoAlert, PageHeader } from '../components/ui'
import { saveBlob } from '../api/client'
import type { QuickRangeId } from '../utils/dates'

const QUICK: { id: QuickRangeId; label: string }[] = [
  { id: 'last7', label: 'Últimos 7 días' },
  { id: 'last30', label: 'Últimos 30 días' },
  { id: 'thisMonth', label: 'Este mes' },
  { id: 'lastMonth', label: 'Mes anterior' },
  { id: 'thisYear', label: 'Este año' },
  { id: 'custom', label: 'Personalizado' },
]

export default function Reports() {
  const [devices, setDevices] = useState<Device[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [rangeId, setRangeId] = useState<QuickRangeId>('thisMonth')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [allDevices, setAllDevices] = useState(true)
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  useEffect(() => {
    const applied = applyQuickRange('thisMonth')
    setDateFrom(applied.from)
    setDateTo(applied.to)
    energyApi.listDevices().then(setDevices).catch(() => setDevices([]))
  }, [])

  function handleRange(id: QuickRangeId) {
    setRangeId(id)
    const applied = applyQuickRange(id)
    if (id !== 'custom') {
      setDateFrom(applied.from)
      setDateTo(applied.to)
    }
  }

  function toggleDevice(id: number) {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    )
  }

  async function generate() {
    setError(null)
    if (!dateFrom || !dateTo) {
      setError('Selecciona la fecha inicial y final del informe.')
      return
    }
    if (!allDevices && selectedIds.length === 0) {
      setError('Selecciona al menos un dispositivo para el informe.')
      return
    }
    setBusy(true)
    try {
      const { blob, filename } = await energyApi.generatePdf({
        date_from: dateFrom,
        date_to: dateTo,
        device_ids: allDevices ? null : selectedIds,
      })
      saveBlob(blob, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo generar el informe PDF.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Informes"
        subtitle="Genera un informe PDF profesional del periodo y dispositivos seleccionados" />

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2>1 · Periodo</h2>
        <div className="chip-row" role="group" aria-label="Accesos rápidos de periodo">
          {QUICK.map((q) => (
            <button key={q.id} type="button"
              className={`chip${rangeId === q.id ? ' active' : ''}`}
              aria-pressed={rangeId === q.id}
              onClick={() => handleRange(q.id)}>
              {q.label}
            </button>
          ))}
        </div>
        <div className="row mt">
          <div className="field" style={{ marginBottom: 0, maxWidth: 200 }}>
            <label htmlFor="report-from">Desde</label>
            <input id="report-from" type="date" value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setRangeId('custom') }} />
          </div>
          <div className="field" style={{ marginBottom: 0, maxWidth: 200 }}>
            <label htmlFor="report-to">Hasta</label>
            <input id="report-to" type="date" value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setRangeId('custom') }} />
          </div>
        </div>
      </div>

      <div className="card">
        <h2>2 · Dispositivos</h2>
        <div className="field">
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600 }}>
            <input type="checkbox" checked={allDevices}
              onChange={(e) => setAllDevices(e.target.checked)} />
            Todos los dispositivos
          </label>
        </div>
        {!allDevices && (
          <div role="group" aria-label="Selección de dispositivos">
            {devices.filter((d) => d.active).map((device) => (
              <label key={device.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '4px 0' }}>
                <input type="checkbox" checked={selectedIds.includes(device.id)}
                  onChange={() => toggleDevice(device.id)} />
                {device.name}
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2>3 · Generar</h2>
        <InfoAlert>
          El PDF incluye: resumen general, tabla por dispositivo con totales, gráfica de consumo
          diario total, gráfica de consumo por dispositivo, gráfica de consumo diario por
          dispositivo, tarifas utilizadas y advertencias si existen días sin tarifa o sin datos.
        </InfoAlert>
        <button className="btn" onClick={() => void generate()} disabled={busy}>
          {busy ? 'Generando PDF…' : 'GENERAR INFORME PDF'}
        </button>
      </div>
    </>
  )
}
