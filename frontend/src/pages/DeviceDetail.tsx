import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { DeviceConsumptionResponse } from '../api/types'
import { energyApi } from '../api/energy'
import { CumulativeChart, DailyTotalChart } from '../components/charts'
import { applyQuickRange } from '../components/FilterBar'
import { EmptyState, ErrorAlert, PageHeader, Spinner, StatCard, WarningAlert } from '../components/ui'
import { formatCop, formatDate, formatDateTime, formatKwh } from '../utils/format'
import type { ImportHistoryItem, Rate } from '../api/types'
import type { QuickRangeId } from '../utils/dates'

export default function DeviceDetail() {
  const { id } = useParams()
  const deviceId = Number(id)

  const [data, setData] = useState<DeviceConsumptionResponse | null>(null)
  const [imports, setImports] = useState<ImportHistoryItem[]>([])
  const [rates, setRates] = useState<Rate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [rangeId, setRangeId] = useState<QuickRangeId>('last30')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [consumption, history, rateList] = await Promise.all([
        energyApi.deviceConsumption(deviceId, { date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        energyApi.listImports({ device_id: deviceId, limit: 20 }),
        energyApi.listRates(),
      ])
      setData(consumption)
      setImports(history)
      setRates(rateList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el dispositivo.')
    } finally {
      setLoading(false)
    }
  }, [deviceId, dateFrom, dateTo])

  useEffect(() => { void load() }, [load])

  function handleRangeChange(nextId: QuickRangeId) {
    setRangeId(nextId)
    const applied = applyQuickRange(nextId)
    if (nextId !== 'custom') {
      setDateFrom(applied.from)
      setDateTo(applied.to)
    }
  }

  if (error) {
    return (
      <>
        <PageHeader title="Dispositivo" />
        <ErrorAlert message={error} />
        <Link to="/devices" className="btn secondary">← Volver a dispositivos</Link>
      </>
    )
  }
  if (loading || !data) {
    return <Spinner text="Cargando dispositivo…" />
  }

  const { device, stats, series } = data
  const cumulative: { date: string; kwh: number }[] = []
  let running = 0
  for (const point of series) {
    running += point.kwh
    cumulative.push({ date: point.date, kwh: Number(running.toFixed(4)) })
  }

  const applicableRates = rates.filter(
    (r) => (!stats.date_from || r.end_date === null || r.end_date >= stats.date_from)
      && (!stats.date_to || r.start_date <= stats.date_to),
  )

  return (
    <>
      <PageHeader title={device.name}
        subtitle={device.description || 'Detalle de consumo del dispositivo'}
        actions={
          <>
            <span className={`badge ${device.active ? 'ok' : 'off'}`}>
              {device.active ? '● Activo' : '○ Desactivado'}
            </span>
            <img src={`/assets/${device.image || 'default-device.png'}`} alt=""
              style={{ width: 40, height: 40, borderRadius: 9, background: 'var(--teal-50)', padding: 3 }} />
            <Link to="/devices" className="btn ghost">← Dispositivos</Link>
          </>
        } />

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="chip-row" role="group" aria-label="Accesos rápidos de periodo">
          {(['today', 'last7', 'last30', 'thisMonth', 'lastMonth', 'thisYear', 'custom'] as QuickRangeId[]).map((rid) => (
            <button key={rid} type="button" className={`chip${rangeId === rid ? ' active' : ''}`}
              aria-pressed={rangeId === rid} onClick={() => handleRangeChange(rid)}>
              {rid === 'today' ? 'Hoy' : rid === 'last7' ? 'Últimos 7 días' : rid === 'last30' ? 'Últimos 30 días'
                : rid === 'thisMonth' ? 'Este mes' : rid === 'lastMonth' ? 'Mes anterior'
                  : rid === 'thisYear' ? 'Este año' : 'Personalizado'}
            </button>
          ))}
        </div>
        <div className="row mt" style={{ alignItems: 'flex-end' }}>
          <div className="field" style={{ marginBottom: 0 }}>
            <label htmlFor="dev-from">Desde</label>
            <input id="dev-from" type="date" value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setRangeId('custom') }} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label htmlFor="dev-to">Hasta</label>
            <input id="dev-to" type="date" value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setRangeId('custom') }} />
          </div>
          <div className="small muted">
            {stats.days_with_data} días con datos · {stats.days_without_data} sin datos
          </div>
        </div>
      </div>

      {series.length === 0 ? (
        <div className="card">
          <EmptyState title="Sin consumo registrado en este periodo"
            description="Importa un CSV para este dispositivo o amplía el rango de fechas."
            action={<Link className="btn" to="/import">Importar CSV</Link>} />
        </div>
      ) : (
        <>
          {stats.days_without_rate > 0 && (
            <WarningAlert title="Tarifa no configurada para parte del periodo">
              El costo de {stats.days_without_rate} día(s) con consumo no pudo calcularse.
            </WarningAlert>
          )}

          <div className="stat-grid">
            <StatCard label="Consumo total" value={formatKwh(stats.total_kwh)} />
            <StatCard label="Costo estimado" tone="amber" value={formatCop(stats.estimated_cost)}
              sub={stats.cost_incomplete ? 'Cálculo parcial' : undefined} />
            <StatCard label="Promedio diario" value={formatKwh(stats.avg_daily_kwh)} />
            <StatCard label="Máximo diario"
              value={formatKwh(stats.max_daily_kwh, true)}
              sub={stats.max_daily_date ? formatDate(stats.max_daily_date) : undefined} />
            <StatCard label="Mínimo diario"
              value={formatKwh(stats.min_daily_kwh, true)}
              sub={stats.min_daily_date ? formatDate(stats.min_daily_date) : undefined} />
            <StatCard label="Primer / último día registrado"
              value={<span style={{ fontSize: 14 }}>{formatDate(stats.first_recorded_day)}</span>}
              sub={formatDate(stats.last_recorded_day)} />
          </div>

          <DailyTotalChart series={series.map((p) => ({ date: p.date, total: p.kwh, values: {} }))} />
          <div style={{ height: 16 }} />
          <CumulativeChart cumulative={cumulative} />
        </>
      )}

      <div className="card">
        <h2>Historial de importaciones</h2>
        {imports.length === 0 ? (
          <p className="muted">Este dispositivo aún no tiene importaciones registradas.</p>
        ) : (
          <div className="table-wrap mt">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th><th>Archivo</th>
                  <th className="num">Nuevos</th><th className="num">Actualizados</th>
                  <th className="num">Ignorados</th><th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {imports.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateTime(item.imported_at)}</td>
                    <td>{item.filename}</td>
                    <td className="num">{item.records_inserted}</td>
                    <td className="num">{item.records_updated}</td>
                    <td className="num">{item.records_ignored}</td>
                    <td>
                      <span className={`badge ${item.status === 'success' ? 'ok' : 'warn'}`}>
                        {item.status === 'success' ? 'Exitosa' : 'Con errores'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Tarifas aplicables al periodo</h2>
        {applicableRates.length === 0 ? (
          <p className="muted">
            No hay tarifas configuradas para este periodo. <Link to="/rates">Configurar tarifas →</Link>
          </p>
        ) : (
          <div className="table-wrap mt">
            <table>
              <thead>
                <tr><th>Vigencia</th><th className="num">Precio</th></tr>
              </thead>
              <tbody>
                {applicableRates.map((rate) => (
                  <tr key={rate.id}>
                    <td>
                      {formatDate(rate.start_date)} – {rate.end_date ? formatDate(rate.end_date) : 'vigente indefinida'}
                    </td>
                    <td className="num">
                      {Number(rate.price_per_kwh).toLocaleString('es-CO')} COP/kWh
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
