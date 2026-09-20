import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ConsumptionResponse, Device } from '../api/types'
import { energyApi } from '../api/energy'
import { FilterBar, applyQuickRange } from '../components/FilterBar'
import {
  CumulativeChart, CostChart, DailyTotalChart, DeviceTotalChart, PerDeviceDailyChart,
} from '../components/charts'
import { EmptyState, ErrorAlert, PageHeader, Spinner, StatCard, WarningAlert } from '../components/ui'
import { formatCop, formatDate, formatKwh } from '../utils/format'
import type { QuickRangeId } from '../utils/dates'

export default function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([])
  const [data, setData] = useState<ConsumptionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [rangeId, setRangeId] = useState<QuickRangeId>('last30')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  // Carga inicial de dispositivos
  useEffect(() => {
    energyApi.listDevices()
      .then(setDevices)
      .catch((err) => setError(err.message))
  }, [])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await energyApi.consumption({
        device_ids: selectedIds.length ? selectedIds.join(',') : undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar el dashboard.')
    } finally {
      setLoading(false)
    }
  }, [selectedIds, dateFrom, dateTo])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  function handleRangeChange(id: QuickRangeId) {
    setRangeId(id)
    const applied = applyQuickRange(id)
    if (id !== 'custom') {
      setDateFrom(applied.from)
      setDateTo(applied.to)
    }
  }

  // Estado 1: sin dispositivos
  const noDevices = devices.length === 0
  // Estado 2: dispositivos pero sin ningún dato
  const noData = !noDevices && data && data.series.length === 0 && (data.summary?.total_kwh ?? 0) === 0

  const summary = data?.summary
  const deviceNames: Record<string, string> = {}
  for (const d of devices) deviceNames[String(d.id)] = d.name
  for (const d of data?.by_device ?? []) deviceNames[String(d.device_id)] = d.device_name

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Resumen de consumo energético del periodo seleccionado" />

      {error && <ErrorAlert message={error} />}

      {noDevices ? (
        <div className="card">
          <EmptyState title="No hay dispositivos registrados"
            description="Registra tu primer dispositivo para comenzar a monitorear su consumo."
            action={<Link className="btn" to="/devices">Agregar dispositivo</Link>} />
        </div>
      ) : noData ? (
        <div className="card">
          <EmptyState title="No hay datos de consumo"
            description="Importa un archivo CSV con el consumo diario de tus dispositivos."
            action={<Link className="btn" to="/import">Importar CSV</Link>} />
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <FilterBar
              rangeId={rangeId} onRangeChange={handleRangeChange}
              dateFrom={dateFrom} dateTo={dateTo}
              onDateFromChange={setDateFrom} onDateToChange={setDateTo}
              devices={devices} selectedIds={selectedIds} onSelectionChange={setSelectedIds}
            />
            <div className="small muted">
              Periodo: <strong>{formatDate(summary?.date_from)} – {formatDate(summary?.date_to)}</strong>
              {' · '}{summary?.days_with_data ?? 0} días con datos
              {' · '}{summary?.days_without_data ?? 0} días sin datos
            </div>
          </div>

          {loading ? (
            <Spinner text="Cargando datos de consumo…" />
          ) : (
            <>
              {summary && summary.days_without_rate > 0 && (
                <WarningAlert title="Tarifa no configurada para algunas fechas">
                  <div>
                    El costo de {summary.days_without_rate} día(s) no pudo calcularse porque no
                    existe tarifa configurada ({summary.missing_rate_ranges.join(', ')}).
                    Se muestra el consumo, pero no se inventan valores de costo.
                  </div>
                  <Link to="/rates">Configurar tarifas →</Link>
                </WarningAlert>
              )}

              <div className="stat-grid">
                <StatCard label="Consumo total" value={formatKwh(summary?.total_kwh)} />
                <StatCard label="Costo estimado" tone="amber"
                  value={formatCop(summary?.total_cost)}
                  sub={summary?.cost_incomplete ? 'Cálculo parcial (días sin tarifa)' : undefined} />
                <StatCard label="Promedio diario" value={formatKwh(summary?.avg_daily_kwh)}
                  sub="Sobre días con datos" />
                <StatCard label="Dispositivos" value={summary?.devices_count ?? 0} />
                <StatCard label="Periodo" value={`${summary?.days ?? 0} días`}
                  sub={`${formatDate(summary?.date_from)} – ${formatDate(summary?.date_to)}`} />
              </div>

              <DailyTotalChart series={data?.series ?? []} />

              {(data?.per_device && Object.keys(data.per_device).length > 1) && (
                <div style={{ height: 16 }} />
              )}
              {(data?.per_device && Object.keys(data.per_device).length > 1) && (
                <PerDeviceDailyChart perDevice={data.per_device} deviceNames={deviceNames} />
              )}

              <div className="stat-grid" style={{ marginTop: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
                <CumulativeChart cumulative={data?.cumulative ?? []} />
                <DeviceTotalChart byDevice={data?.by_device ?? []} />
              </div>

              <CostChart costSeries={data?.cost_series ?? []} />
            </>
          )}
        </>
      )}
    </>
  )
}
