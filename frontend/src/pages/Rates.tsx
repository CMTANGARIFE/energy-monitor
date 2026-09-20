import { useEffect, useState } from 'react'
import type { Rate, RateInput } from '../api/types'
import { energyApi } from '../api/energy'
import { ConfirmDialog, Modal } from '../components/Modal'
import { EmptyState, ErrorAlert, PageHeader, Spinner } from '../components/ui'
import { formatDate, formatPrice } from '../utils/format'

interface RateForm extends RateInput {
  open_ended: boolean
}

function emptyForm(): RateForm {
  return { start_date: '', end_date: '', price_per_kwh: '', open_ended: true }
}

export default function Rates() {
  const [rates, setRates] = useState<Rate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<Rate | null>(null)
  const [form, setForm] = useState<RateForm>(emptyForm())
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<Rate | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setRates(await energyApi.listRates())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron cargar las tarifas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  function openCreate() {
    setForm(emptyForm())
    setEditing(null)
    setFormError(null)
    setModalOpen(true)
  }

  function openEdit(rate: Rate) {
    setForm({
      start_date: rate.start_date.slice(0, 10),
      end_date: rate.end_date?.slice(0, 10) ?? '',
      price_per_kwh: String(parseFloat(rate.price_per_kwh)),
      open_ended: rate.end_date === null,
    })
    setEditing(rate)
    setFormError(null)
    setModalOpen(true)
  }

  async function save() {
    setFormError(null)
    if (!form.start_date) {
      setFormError('Indica la fecha inicial de la tarifa.')
      return
    }
    const price = parseFloat(form.price_per_kwh)
    if (Number.isNaN(price) || price <= 0) {
      setFormError('El precio por kWh debe ser un número mayor que cero.')
      return
    }
    setSaving(true)
    const payload: RateInput = {
      start_date: form.start_date,
      end_date: form.open_ended ? null : (form.end_date || null),
      price_per_kwh: String(price),
    }
    try {
      if (editing) {
        await energyApi.updateRate(editing.id, payload)
        setNotice('Tarifa actualizada correctamente.')
      } else {
        await energyApi.createRate(payload)
        setNotice('Tarifa creada correctamente.')
      }
      setModalOpen(false)
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'No se pudo guardar la tarifa.')
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelete() {
    if (!deleting) return
    try {
      await energyApi.deleteRate(deleting.id)
      setNotice('Tarifa eliminada.')
      setDeleting(null)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar la tarifa.')
      setDeleting(null)
    }
  }

  return (
    <>
      <PageHeader title="Tarifas"
        subtitle="Precio por kWh vigente por periodos. Sin solapamientos; máximo una tarifa abierta."
        actions={<button className="btn" onClick={openCreate}>+ Nueva tarifa</button>} />

      {error && <ErrorAlert message={error} />}
      {notice && !error && <div className="alert info" role="status">{notice}</div>}

      {loading ? (
        <Spinner />
      ) : rates.length === 0 ? (
        <div className="card">
          <EmptyState title="No hay tarifas configuradas"
            description="Crea al menos una tarifa (COP/kWh) para calcular costos estimados."
            action={<button className="btn" onClick={openCreate}>Crear tarifa</button>} />
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Vigencia</th>
                <th className="num">Precio (COP/kWh)</th>
                <th className="num">Equivalente</th>
                <th>Estado</th>
                <th className="text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rates.map((rate) => (
                <tr key={rate.id}>
                  <td>
                    {formatDate(rate.start_date)} – {rate.end_date ? formatDate(rate.end_date) : '—'}
                  </td>
                  <td className="num">{Number(rate.price_per_kwh).toLocaleString('es-CO')}</td>
                  <td className="num">{formatPrice(rate.price_per_kwh)} /kWh</td>
                  <td>
                    {rate.end_date === null
                      ? <span className="badge ok">Vigente indefinida</span>
                      : <span className="badge off">Cerrada</span>}
                  </td>
                  <td className="text-right">
                    <button className="btn small ghost" onClick={() => openEdit(rate)}>Editar</button>{' '}
                    <button className="btn small ghost" style={{ color: 'var(--danger)' }}
                      onClick={() => setDeleting(rate)}>Eliminar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="alert info small">
        <strong>Cómo funciona el cálculo:</strong> cada día de consumo usa la tarifa vigente en
        SU fecha. Un informe que atraviesa dos tarifas combina ambas correctamente
        (nunca se aplica una sola tarifa al total). Los días sin tarifa configurada
        no tienen costo: se advierte claramente en pantalla y en el PDF.
      </div>

      {modalOpen && (
        <Modal title={editing ? 'Editar tarifa' : 'Nueva tarifa'}
          onClose={() => setModalOpen(false)}>
          {formError && <ErrorAlert message={formError} />}
          <div className="field">
            <label htmlFor="rate-start">Desde *</label>
            <input id="rate-start" type="date" value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="rate-end">Hasta</label>
            <div className="row">
              <input id="rate-end" type="date" value={form.end_date ?? ''}
                disabled={form.open_ended}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
              <label className="small" style={{ display: 'flex', gap: 6, alignItems: 'center', whiteSpace: 'nowrap' }}>
                <input type="checkbox" checked={form.open_ended}
                  onChange={(e) => setForm({ ...form, open_ended: e.target.checked })} />
                Vigente indefinida
              </label>
            </div>
            <span className="hint">
              Una tarifa sin fecha final queda vigente indefinidamente. Solo puede existir una.
            </span>
          </div>
          <div className="field">
            <label htmlFor="rate-price">Precio por kWh (COP) *</label>
            <input id="rate-price" type="number" min="0.0001" step="0.01"
              value={form.price_per_kwh} placeholder="Ej: 850"
              aria-invalid={formError ? true : undefined}
              onChange={(e) => setForm({ ...form, price_per_kwh: e.target.value })} />
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="btn" onClick={() => void save()} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </Modal>
      )}

      {deleting && (
        <ConfirmDialog title="Eliminar tarifa"
          message={`¿Eliminar la tarifa de ${formatDate(deleting.start_date)} a ${deleting.end_date ? formatDate(deleting.end_date) : 'vigente indefinida'} (${Number(deleting.price_per_kwh).toLocaleString('es-CO')} COP/kWh)? Los días que dependan de ella quedarán sin costo calculable.`}
          confirmLabel="Eliminar" danger
          onConfirm={() => void confirmDelete()}
          onCancel={() => setDeleting(null)} />
      )}
    </>
  )
}
