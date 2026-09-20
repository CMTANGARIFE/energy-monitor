import { useEffect, useRef, useState } from 'react'
import type { Device } from '../api/types'
import { QUICK_RANGES, resolveQuickRange, type QuickRangeId } from '../utils/dates'

/** Barra de filtros reutilizable: accesos rápidos + fechas + dispositivos. */
export function FilterBar({
  rangeId,
  onRangeChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  devices,
  selectedIds,
  onSelectionChange,
  allowAllDevices = true,
}: {
  rangeId: QuickRangeId
  onRangeChange: (id: QuickRangeId) => void
  dateFrom: string
  dateTo: string
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  devices: Device[]
  selectedIds: number[]
  onSelectionChange: (ids: number[]) => void
  allowAllDevices?: boolean
}) {
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const activeDevices = devices.filter((d) => d.active)
  const allSelected = selectedIds.length === 0 || selectedIds.length === activeDevices.length
  const buttonText = allSelected
    ? 'Todos los dispositivos'
    : selectedIds.length === 1
      ? (devices.find((d) => d.id === selectedIds[0])?.name ?? '1 dispositivo')
      : `${selectedIds.length} dispositivos`

  return (
    <div className="filters">
      <div className="chip-row" role="group" aria-label="Accesos rápidos de periodo">
        {QUICK_RANGES.map((r) => (
          <button key={r.id} type="button"
            className={`chip${rangeId === r.id ? ' active' : ''}`}
            aria-pressed={rangeId === r.id}
            onClick={() => onRangeChange(r.id)}>
            {r.label}
          </button>
        ))}
      </div>

      <div className="field">
        <label htmlFor="filter-from">Desde</label>
        <input id="filter-from" type="date" value={dateFrom}
          onChange={(e) => { onDateFromChange(e.target.value); onRangeChange('custom') }} />
      </div>
      <div className="field">
        <label htmlFor="filter-to">Hasta</label>
        <input id="filter-to" type="date" value={dateTo}
          onChange={(e) => { onDateToChange(e.target.value); onRangeChange('custom') }} />
      </div>

      <div className="field">
        <label id="devices-label">Dispositivo(s)</label>
        <div className="multiselect" ref={panelRef}>
          <button type="button" className="multiselect-btn" aria-haspopup="listbox"
            aria-expanded={open} aria-labelledby="devices-label"
            onClick={() => setOpen((v) => !v)}>
            <span>{buttonText}</span>
            <span aria-hidden="true">▾</span>
          </button>
          {open && (
            <div className="multiselect-panel" role="listbox" aria-multiselectable="true">
              {allowAllDevices && (
                <label>
                  <input type="checkbox" checked={allSelected}
                    onChange={() => onSelectionChange([])} />
                  <strong>Todos los dispositivos</strong>
                </label>
              )}
              {activeDevices.map((device) => {
                const checked = allSelected || selectedIds.includes(device.id)
                return (
                  <label key={device.id}>
                    <input type="checkbox" checked={checked}
                      onChange={() => {
                        if (allSelected) {
                          // Al desmarcar uno partiendo de "todos": seleccionar solo ese como excluido
                          onSelectionChange(activeDevices.map((d) => d.id).filter((id) => id !== device.id))
                        } else if (selectedIds.includes(device.id)) {
                          onSelectionChange(selectedIds.filter((id) => id !== device.id))
                        } else {
                          const next = [...selectedIds, device.id]
                          onSelectionChange(
                            next.length === activeDevices.length ? [] : next,
                          )
                        }
                      }} />
                    {device.name}
                  </label>
                )
              })}
              {activeDevices.length === 0 && (
                <div className="small muted" style={{ padding: '6px 8px' }}>
                  No hay dispositivos activos.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/** Aplica un rango rápido y devuelve también las fechas */
export function applyQuickRange(id: QuickRangeId): { rangeId: QuickRangeId; from: string; to: string } {
  const resolved = resolveQuickRange(id)
  if (!resolved) return { rangeId: id, from: '', to: '' }
  return { rangeId: id, from: resolved.from, to: resolved.to }
}
