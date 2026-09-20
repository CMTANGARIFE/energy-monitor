// Las 5 gráficas del sistema (secciones 23 y 28 de la especificación).
// Recharts con formato es-CO; los días sin datos aparecen como huecos
// (nunca se asume cero).

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ConsumptionPoint, DevicePeriodCost } from '../api/types'
import { formatCop, formatDate, formatKwh } from '../utils/format'

const COLORS = ['#0f766e', '#d97706', '#7c3aed', '#dc2626', '#2563eb',
  '#059669', '#db2777', '#65a30d', '#9333ea', '#0ea5e9']

const axisStyle = { fontSize: 11, fill: '#6b7280' }

function tickDay(iso: string): string {
  return formatDate(iso).slice(0, 5) // DD/MM
}

const tooltipStyle = {
  borderRadius: 8,
  border: '1px solid #e2e8e8',
  fontSize: 12.5,
  boxShadow: '0 6px 18px rgba(16,40,40,0.12)',
}

function ChartCard({ title, subtitle, height, children }: {
  title: string
  subtitle?: string
  height?: number
  children: React.ReactNode
}) {
  return (
    <div className="card">
      <h2>{title}</h2>
      {subtitle && <p className="muted small" style={{ marginTop: 2 }}>{subtitle}</p>}
      <div className="chart-box" style={height ? { height } : undefined}>
        <ResponsiveContainer width="100%" height="100%">
          {children as never}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/** Gráfica A — consumo diario total (línea). */
export function DailyTotalChart({ series }: { series: ConsumptionPoint[] }) {
  const data = series.map((p) => ({ date: p.date, kwh: p.total }))
  return (
    <ChartCard title="Consumo diario total" subtitle="kWh por día (solo días con registro)">
      <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f2" />
        <XAxis dataKey="date" tickFormatter={tickDay} tick={axisStyle} tickMargin={6} />
        <YAxis tick={axisStyle} tickMargin={4} width={54} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value) => [formatKwh(Number(value)), 'Consumo']}
          labelFormatter={(label) => formatDate(String(label))} />
        <Line isAnimationActive={false} type="monotone" dataKey="kwh" stroke={COLORS[0]} strokeWidth={2}
          dot={data.length <= 40 ? { r: 2.5, fill: COLORS[0] } : false}
          activeDot={{ r: 4 }} connectNulls={false} />
      </LineChart>
    </ChartCard>
  )
}

/** Gráfica B — consumo diario por dispositivo (una serie por dispositivo). */
export function PerDeviceDailyChart({ perDevice, deviceNames }: {
  perDevice: Record<string, { date: string; kwh: number }[]>
  deviceNames: Record<string, string>
}) {
  const deviceIds = Object.keys(perDevice)
  const dates = [...new Set(deviceIds.flatMap((id) => perDevice[id].map((p) => p.date)))].sort()
  const lookup = new Map<string, Map<string, number>>()
  for (const id of deviceIds) {
    for (const point of perDevice[id]) {
      if (!lookup.has(point.date)) lookup.set(point.date, new Map())
      lookup.get(point.date)!.set(id, point.kwh)
    }
  }
  const data = dates.map((date) => {
    const row: Record<string, string | number | null> = { date }
    for (const id of deviceIds) {
      row[`d${id}`] = lookup.get(date)?.get(id) ?? null // sin dato ≠ cero
    }
    return row
  })

  return (
    <ChartCard title="Consumo diario por dispositivo"
      subtitle="Cada línea es un dispositivo; los huecos son días sin registro">
      <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f2" />
        <XAxis dataKey="date" tickFormatter={tickDay} tick={axisStyle} tickMargin={6} />
        <YAxis tick={axisStyle} tickMargin={4} width={54} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value, name) => [formatKwh(Number(value)), deviceNames[String(name).slice(1)] ?? String(name)]}
          labelFormatter={(label) => formatDate(String(label))} />
        <Legend formatter={(value) => deviceNames[String(value).slice(1)] ?? String(value)} wrapperStyle={{ fontSize: 12 }} />
        {deviceIds.map((id, index) => (
          <Line key={id} type="monotone" dataKey={`d${id}`} stroke={COLORS[index % COLORS.length]}
            strokeWidth={1.8} dot={false} connectNulls={false} />
        ))}
      </LineChart>
    </ChartCard>
  )
}

/** Gráfica C — consumo acumulado (área). */
export function CumulativeChart({ cumulative }: { cumulative: { date: string; kwh: number }[] }) {
  return (
    <ChartCard title="Consumo acumulado" subtitle="Acumulado del periodo seleccionado">
      <AreaChart data={cumulative} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f2" />
        <XAxis dataKey="date" tickFormatter={tickDay} tick={axisStyle} tickMargin={6} />
        <YAxis tick={axisStyle} tickMargin={4} width={54} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value) => [formatKwh(Number(value)), 'Acumulado']}
          labelFormatter={(label) => formatDate(String(label))} />
        <Area isAnimationActive={false} type="monotone" dataKey="kwh" stroke={COLORS[0]} fill={COLORS[0]} fillOpacity={0.14} strokeWidth={2} />
      </AreaChart>
    </ChartCard>
  )
}

/** Gráfica D — consumo total por dispositivo en el periodo (barras). */
export function DeviceTotalChart({ byDevice }: { byDevice: DevicePeriodCost[] }) {
  const data = byDevice.map((d) => ({ name: d.device_name, kwh: d.kwh }))
  return (
    <ChartCard title="Consumo por dispositivo" subtitle="Total de cada dispositivo en el periodo">
      <BarChart data={data} margin={{ top: 14, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f2" vertical={false} />
        <XAxis dataKey="name" tick={axisStyle} tickMargin={6} interval={0}
          tickFormatter={(name: string) => (name.length > 11 ? `${name.slice(0, 10)}…` : name)} />
        <YAxis tick={axisStyle} tickMargin={4} width={54} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value) => [formatKwh(Number(value)), 'Total']} />
        <Bar isAnimationActive={false} dataKey="kwh" radius={[6, 6, 0, 0]} maxBarSize={54}>
          {data.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  )
}

/** Gráfica E — costo diario estimado según tarifas configuradas. */
export function CostChart({ costSeries }: { costSeries: { date: string; cost: number | null }[] }) {
  const data = costSeries.map((p) => ({ date: p.date, cost: p.cost }))
  return (
    <ChartCard title="Costo diario estimado"
      subtitle="Cada día usa su tarifa vigente; los huecos son días sin tarifa configurada">
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f2" />
        <XAxis dataKey="date" tickFormatter={tickDay} tick={axisStyle} tickMargin={6} />
        <YAxis tick={axisStyle} tickMargin={4} width={68}
          tickFormatter={(v: number) => formatCop(v).replace(/\s/g, ' ')} />
        <Tooltip contentStyle={tooltipStyle}
          formatter={(value) => [formatCop(Number(value)), 'Costo']}
          labelFormatter={(label) => formatDate(String(label))} />
        <Area isAnimationActive={false} type="monotone" dataKey="cost" stroke={COLORS[1]} fill={COLORS[1]}
          fillOpacity={0.16} strokeWidth={2} connectNulls={false} />
      </AreaChart>
    </ChartCard>
  )
}
