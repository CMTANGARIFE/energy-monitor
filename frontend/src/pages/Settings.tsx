import { useEffect, useState } from 'react'
import type { HealthInfo, SettingsInfo, SettingsStats } from '../api/types'
import { energyApi } from '../api/energy'
import { saveBlob } from '../api/client'
import { ErrorAlert, PageHeader, Spinner } from '../components/ui'

export default function Settings() {
  const [info, setInfo] = useState<SettingsInfo | null>(null)
  const [stats, setStats] = useState<SettingsStats | null>(null)
  const [health, setHealth] = useState<HealthInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [backupBusy, setBackupBusy] = useState(false)

  useEffect(() => {
    Promise.all([energyApi.settingsInfo(), energyApi.settingsStats(), energyApi.health()])
      .then(([i, s, h]) => {
        setInfo(i)
        setStats(s)
        setHealth(h)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la configuración.'))
      .finally(() => setLoading(false))
  }, [])

  async function downloadBackup() {
    setBackupBusy(true)
    setError(null)
    try {
      const { blob, filename } = await energyApi.downloadBackup()
      saveBlob(blob, filename)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo generar el respaldo.')
    } finally {
      setBackupBusy(false)
    }
  }

  if (loading) return <Spinner text="Cargando configuración…" />

  return (
    <>
      <PageHeader title="Configuración"
        subtitle="Información de la instalación, respaldos y personalización de assets" />

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2>Estado del sistema</h2>
        <div className="row mt" style={{ gap: 14 }}>
          <span className={`badge ${health?.status === 'ok' ? 'ok' : 'warn'}`}>
            Backend: {health?.status === 'ok' ? 'Operativo' : 'Con problemas'}
          </span>
          <span className={`badge ${health?.database === 'ok' ? 'ok' : 'warn'}`}>
            Base de datos: {health?.database === 'ok' ? 'Conectada' : health?.database ?? '—'}
          </span>
        </div>
        {stats && (
          <div className="file-meta mt">
            <div className="item"><div className="k">Dispositivos</div><div className="v">{stats.devices}</div></div>
            <div className="item"><div className="k">Registros de consumo</div><div className="v">{stats.consumption_records.toLocaleString('es-CO')}</div></div>
            <div className="item"><div className="k">Tarifas</div><div className="v">{stats.rates}</div></div>
            <div className="item"><div className="k">Importaciones</div><div className="v">{stats.imports}</div></div>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Respaldo de la base de datos</h2>
        <p className="muted small">
          Descarga un respaldo completo. Los datos también sobreviven a reinicios y recreación
          de contenedores gracias al volumen persistente <code>postgres_data</code>.
          El procedimiento manual y la restauración están documentados en <code>docs/BACKUP.md</code>.
        </p>
        <button className="btn secondary" onClick={() => void downloadBackup()} disabled={backupBusy}>
          {backupBusy ? 'Generando respaldo…' : '⬇ Descargar backup'}
        </button>
      </div>

      {info && (
        <div className="card">
          <h2>Información de la aplicación</h2>
          <div className="table-wrap mt">
            <table style={{ minWidth: 380 }}>
              <tbody>
                <tr><td><strong>Aplicación</strong></td><td>{info.app_name} v{info.version}</td></tr>
                <tr><td><strong>Moneda</strong></td><td>{info.currency} (formato colombiano)</td></tr>
                <tr><td><strong>Unidad de energía</strong></td><td>kWh (consumo diario)</td></tr>
                <tr><td><strong>Motor de base de datos</strong></td><td>{info.database_engine}</td></tr>
                <tr><td><strong>Tamaño máximo de CSV</strong></td><td>{info.max_csv_size_mb} MB</td></tr>
                <tr><td><strong>Logo del PDF</strong></td><td>{info.pdf_logo_available ? 'Personalizado disponible (backend/assets/logo.png)' : 'Sin logo (backend/assets/logo.png)'}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Assets reemplazables</h2>
        <p className="muted small">
          Puedes sustituir las imágenes de la aplicación sin modificar código: reemplaza el
          archivo y refresca el navegador. Detalles en <code>docs/ASSETS.md</code>.
        </p>
        <div className="table-wrap mt">
          <table style={{ minWidth: 480 }}>
            <thead>
              <tr><th>Archivo</th><th>Ubicación</th><th>Formato</th><th>Dimensiones</th><th>Propósito</th></tr>
            </thead>
            <tbody>
              <tr><td><code>logo.png</code></td><td>frontend/assets/ y backend/assets/</td><td>PNG</td><td>512×512, fondo transparente</td><td>Logo principal (interfaz y PDF)</td></tr>
              <tr><td><code>favicon.png</code></td><td>frontend/assets/</td><td>PNG</td><td>64×64, fondo transparente</td><td>Ícono de la pestaña</td></tr>
              <tr><td><code>default-device.png</code></td><td>frontend/assets/</td><td>PNG</td><td>256×256, fondo transparente</td><td>Imagen por defecto de dispositivos</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Datos de demostración</h2>
        <p className="muted small">
          Para explorar la aplicación con datos de ejemplo puedes cargar el seed demo desde el
          backend: <code>python scripts/seed_demo.py</code> (o <code>docker compose exec backend
          python scripts/seed_demo.py</code>). Los dispositivos demo se identifican con el
          prefijo <code>[DEMO]</code> y se pueden eliminar con <code>--force</code> sin tocar
          tus datos reales.
        </p>
      </div>
    </>
  )
}
