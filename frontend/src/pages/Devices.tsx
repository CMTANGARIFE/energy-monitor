import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Device, DeviceInput } from '../api/types'
import { energyApi } from '../api/energy'
import { ConfirmDialog, Modal } from '../components/Modal'
import { EmptyState, ErrorAlert, PageHeader, Spinner } from '../components/ui'

const EMPTY_FORM: DeviceInput = { name: '', description: '', image: '' }

export default function Devices() {
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [editing, setEditing] = useState<Device | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<DeviceInput>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<Device | null>(null)
  const [saving, setSaving] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setDevices(await energyApi.listDevices())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar la lista de dispositivos.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  function openCreate() {
    setForm(EMPTY_FORM)
    setFormError(null)
    setCreating(true)
  }

  function openEdit(device: Device) {
    setForm({ name: device.name, description: device.description ?? '', image: device.image ?? '' })
    setFormError(null)
    setEditing(device)
  }

  async function save() {
    if (!form.name.trim()) {
      setFormError('El nombre del dispositivo es obligatorio.')
      return
    }
    setSaving(true)
    setFormError(null)
    const payload: DeviceInput = {
      name: form.name.trim(),
      description: form.description?.trim() || null,
      image: form.image?.trim() || null,
    }
    try {
      if (editing) {
        await energyApi.updateDevice(editing.id, payload)
        setNotice('Dispositivo actualizado correctamente.')
      } else {
        await energyApi.createDevice(payload)
        setNotice('Dispositivo creado correctamente.')
      }
      setEditing(null)
      setCreating(false)
      await load()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'No se pudo guardar el dispositivo.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleStatus(device: Device) {
    if (device.active) {
      setConfirmDeactivate(device)
      return
    }
    await energyApi.setDeviceStatus(device.id, true)
    setNotice(`Dispositivo "${device.name}" activado.`)
    await load()
  }

  async function deactivate() {
    if (!confirmDeactivate) return
    await energyApi.setDeviceStatus(confirmDeactivate.id, false)
    setNotice(`Dispositivo "${confirmDeactivate.name}" desactivado. Sus datos históricos se conservan.`)
    setConfirmDeactivate(null)
    await load()
  }

  const showForm = creating || editing !== null

  return (
    <>
      <PageHeader title="Dispositivos"
        subtitle="Administra los equipos que monitoreas"
        actions={<button className="btn" onClick={openCreate}>+ Agregar dispositivo</button>} />

      {error && <ErrorAlert message={error} />}
      {notice && !error && (
        <div className="alert info" role="status">{notice}</div>
      )}

      {loading ? (
        <Spinner />
      ) : devices.length === 0 ? (
        <div className="card">
          <EmptyState title="No hay dispositivos registrados"
            description="Crea tu primer dispositivo para poder importar su consumo."
            action={<button className="btn" onClick={openCreate}>Agregar dispositivo</button>} />
        </div>
      ) : (
        <div className="device-grid">
          {devices.map((device) => (
            <div key={device.id} className="card device-card">
              <div className="head">
                <img src={`/assets/${device.image || 'default-device.png'}`} alt={`Imagen de ${device.name}`} />
                <div>
                  <h3><Link to={`/devices/${device.id}`}>{device.name}</Link></h3>
                  <span className={`badge ${device.active ? 'ok' : 'off'}`}>
                    {device.active ? '● Activo' : '○ Desactivado'}
                  </span>
                </div>
              </div>
              <p className="desc">{device.description || <span className="muted">Sin descripción</span>}</p>
              <div className="actions">
                <Link className="btn small secondary" to={`/devices/${device.id}`}>Ver detalle</Link>
                <button className="btn small ghost" onClick={() => openEdit(device)}>Editar</button>
                <button className={`btn small ${device.active ? 'ghost' : 'secondary'}`}
                  onClick={() => void toggleStatus(device)}>
                  {device.active ? 'Desactivar' : 'Activar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <Modal title={editing ? 'Editar dispositivo' : 'Nuevo dispositivo'}
          onClose={() => { setEditing(null); setCreating(false) }}>
          {formError && <ErrorAlert message={formError} />}
          <div className="field">
            <label htmlFor="device-name">Nombre *</label>
            <input id="device-name" type="text" value={form.name} maxLength={120}
              aria-invalid={formError ? true : undefined}
              placeholder="Ej: PC Principal, Nevera, Servidor…"
              onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="device-desc">Descripción</label>
            <textarea id="device-desc" rows={2} value={form.description ?? ''}
              placeholder="Descripción opcional del dispositivo"
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor="device-image">Imagen / icono</label>
            <div className="row">
              <img src={`/assets/${form.image || 'default-device.png'}`} alt=""
                style={{ width: 42, height: 42, borderRadius: 9, background: 'var(--teal-50)', padding: 4 }} />
              <input id="device-image" type="text" value={form.image ?? ''}
                placeholder="default-device.png"
                onChange={(e) => setForm({ ...form, image: e.target.value })} />
            </div>
            <span className="hint">
              Nombre de archivo dentro de la carpeta <code>frontend/assets/</code>.
              Deja vacío para usar la imagen por defecto. Ver Configuración → Assets.
            </span>
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => { setEditing(null); setCreating(false) }}>
              Cancelar
            </button>
            <button className="btn" onClick={() => void save()} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar'}
            </button>
          </div>
        </Modal>
      )}

      {confirmDeactivate && (
        <ConfirmDialog title="Desactivar dispositivo"
          message={`¿Desactivar "${confirmDeactivate.name}"? El dispositivo dejará de aparecer en las selecciones, pero sus datos históricos y su historial de importaciones se conservan íntegros.`}
          confirmLabel="Desactivar" danger
          onConfirm={() => void deactivate()}
          onCancel={() => setConfirmDeactivate(null)} />
      )}
    </>
  )
}
