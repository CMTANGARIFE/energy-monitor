import { useEffect, useRef, useState } from 'react'
import type { Device, ImportHistoryItem, ImportPreview, ImportResult } from '../api/types'
import { energyApi } from '../api/energy'
import { ErrorAlert, PageHeader, Spinner } from '../components/ui'
import { formatBytes, formatDate, formatDateTime, formatKwh } from '../utils/format'
import { scanCsvText, type CsvScan } from '../utils/dates'
import { ApiError } from '../api/client'

type Step = 1 | 2 | 3 | 4 | 5

const STEP_LABELS: Record<Step, string> = {
  1: '1 · Archivo',
  2: '2 · Dispositivo',
  3: '3 · Revisar',
  4: '4 · Importar',
  5: '5 · Resultado',
}

export default function ImportPage() {
  const [devices, setDevices] = useState<Device[]>([])
  const [history, setHistory] = useState<ImportHistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)

  const [step, setStep] = useState<Step>(1)
  const [file, setFile] = useState<File | null>(null)
  const [scan, setScan] = useState<CsvScan | null>(null)
  const [deviceId, setDeviceId] = useState<string>('')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rowErrors, setRowErrors] = useState<ImportPreview['errors']>([])
  const [dragOver, setDragOver] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  async function loadHistory() {
    setLoadingHistory(true)
    try {
      setHistory(await energyApi.listImports({ limit: 30 }))
    } catch {
      // silencioso: el historial es complementario
    } finally {
      setLoadingHistory(false)
    }
  }

  useEffect(() => {
    energyApi.listDevices()
      .then(setDevices)
      .catch(() => setDevices([]))
    void loadHistory()
  }, [])

  function acceptFile(selected: File | null) {
    if (!selected) return
    if (!/\.(csv|txt)$/i.test(selected.name)) {
      setError('El archivo debe ser un CSV (.csv).')
      return
    }
    setError(null)
    setFile(selected)
    setPreview(null)
    setResult(null)
    setRowErrors([])
    selected.text().then((text) => setScan(scanCsvText(text))).catch(() => setScan(null))
    setStep(2)
  }

  async function loadPreview() {
    if (!file || !deviceId) return
    setBusy(true)
    setError(null)
    try {
      const resultPreview = await energyApi.previewImport(file, Number(deviceId))
      setPreview(resultPreview)
      setRowErrors(resultPreview.errors)
      setStep(3)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setRowErrors(err.errors)
      } else {
        setError('No se pudo analizar el archivo.')
      }
    } finally {
      setBusy(false)
    }
  }

  async function runImport() {
    if (!file || !deviceId) return
    setBusy(true)
    setError(null)
    try {
      const importResult = await energyApi.runImport(file, Number(deviceId))
      setResult(importResult)
      setStep(5)
      await loadHistory()
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setRowErrors(err.errors)
      } else {
        setError('No se pudo importar el archivo.')
      }
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setStep(1)
    setFile(null)
    setScan(null)
    setDeviceId('')
    setPreview(null)
    setResult(null)
    setRowErrors([])
    setError(null)
  }

  return (
    <>
      <PageHeader title="Importar consumo"
        subtitle="Carga archivos CSV con el consumo diario (UPSERT: lo existente se actualiza, lo nuevo se inserta)" />

      <div className="steps" aria-label="Progreso de importación">
        {([1, 2, 3, 4, 5] as Step[]).map((s) => (
          <span key={s}
            className={`step-pill${step === s ? ' current' : step > s ? ' done' : ''}`}>
            {step > s ? '✓ ' : ''}{STEP_LABELS[s]}
          </span>
        ))}
      </div>

      {error && <ErrorAlert message={error} />}

      {/* ---------------- Paso 1: zona de carga ---------------- */}
      {step === 1 && (
        <div className="card">
          <div className={`dropzone${dragOver ? ' dragover' : ''}`}
            role="button" tabIndex={0}
            aria-label="Zona para arrastrar o seleccionar archivo CSV"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              acceptFile(e.dataTransfer.files?.[0] ?? null)
            }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
              <path d="M12 15V3m0 0 4 4m-4-4L8 7" />
              <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
            </svg>
            <div className="big">Arrastra tu archivo CSV aquí</div>
            <div className="muted">o haz clic para seleccionarlo · formato: date,kwh,cost</div>
          </div>
          <input ref={inputRef} type="file" accept=".csv,.txt,text/csv"
            onChange={(e) => acceptFile(e.target.files?.[0] ?? null)} />
          <p className="small muted" style={{ marginBottom: 0 }}>
            Las filas <code>total</code> se ignoran y la columna <code>cost</code> no se almacena:
            el costo se calcula internamente con las tarifas configuradas.
          </p>
        </div>
      )}

      {/* ---------------- Paso 2: archivo + dispositivo ---------------- */}
      {step === 2 && file && (
        <div className="card">
          <h2>Archivo seleccionado</h2>
          <div className="file-meta">
            <div className="item"><div className="k">Nombre</div><div className="v">{file.name}</div></div>
            <div className="item"><div className="k">Tamaño</div><div className="v">{formatBytes(file.size)}</div></div>
            {scan && (
              <>
                <div className="item"><div className="k">Registros diarios</div><div className="v">{scan.dailyRows}</div></div>
                <div className="item"><div className="k">Filas total ignoradas</div><div className="v">{scan.totalRows}</div></div>
                <div className="item"><div className="k">Periodo detectado</div>
                  <div className="v">{scan.periodFrom ? `${formatDate(scan.periodFrom)} – ${formatDate(scan.periodTo)}` : '—'}</div></div>
                <div className="item"><div className="k">Consumo detectado</div>
                  <div className="v">{formatKwh(scan.totalKwh)}</div></div>
              </>
            )}
          </div>

          <div className="field" style={{ maxWidth: 360 }}>
            <label htmlFor="import-device">Dispositivo *</label>
            <select id="import-device" value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}>
              <option value="">Seleccionar dispositivo…</option>
              {devices.filter((d) => d.active).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
            <span className="hint">El consumo se asociará al dispositivo elegido.</span>
          </div>

          <div className="row">
            <button className="btn" disabled={!deviceId || busy} onClick={() => void loadPreview()}>
              {busy ? 'Analizando…' : 'Continuar'}
            </button>
            <button className="btn ghost" onClick={reset}>Cancelar</button>
          </div>
        </div>
      )}

      {/* ---------------- Paso 3: vista previa ---------------- */}
      {step === 3 && preview && (
        <div className="card">
          <h2>Vista previa</h2>
          <div className="file-meta">
            <div className="item"><div className="k">Registros encontrados</div><div className="v">{preview.records_found}</div></div>
            <div className="item"><div className="k">Registros nuevos</div><div className="v" style={{ color: 'var(--success)' }}>{preview.new_records}</div></div>
            <div className="item"><div className="k">Registros existentes</div><div className="v" style={{ color: 'var(--amber-600)' }}>{preview.existing_records}</div></div>
            <div className="item"><div className="k">Filas total ignoradas</div><div className="v">{preview.ignored_rows}</div></div>
            <div className="item"><div className="k">Consumo total</div><div className="v">{formatKwh(preview.total_kwh)}</div></div>
            <div className="item"><div className="k">Periodo</div>
              <div className="v">{preview.date_from ? `${formatDate(preview.date_from)} – ${formatDate(preview.date_to)}` : '—'}</div></div>
          </div>

          {preview.existing_records > 0 && (
            <div className="alert info">
              Los {preview.existing_records} registro(s) existentes serán <strong>actualizados</strong>
              {' '}(dispositivo + fecha). No se crearán duplicados.
            </div>
          )}

          {rowErrors.length > 0 && (
            <div className="alert error" role="alert">
              <strong>No se pudo procesar el archivo: contiene errores de validación.</strong>
              <ul>
                {rowErrors.slice(0, 10).map((e, i) => (
                  <li key={i}>
                    Fila {e.row ?? '?'}{e.value ? ` — valor "${e.value}"` : ''}: {e.message}
                  </li>
                ))}
                {rowErrors.length > 10 && <li>… y {rowErrors.length - 10} error(es) más.</li>}
              </ul>
              Corrije el archivo y vuelve a intentarlo: <strong>nada se ha guardado</strong>.
            </div>
          )}

          <div className="row">
            <button className="btn" disabled={!preview.valid} onClick={() => setStep(4)}>
              Continuar
            </button>
            <button className="btn ghost" onClick={reset}>Elegir otro archivo</button>
          </div>
        </div>
      )}

      {/* ---------------- Paso 4: confirmación ---------------- */}
      {step === 4 && preview && (
        <div className="card">
          <h2>Confirmar importación</h2>
          <p>
            Dispositivo: <strong>{preview.device_name}</strong> · Archivo: <strong>{preview.filename}</strong>
          </p>
          <p className="muted small">
            Se insertarán {preview.new_records} registro(s) nuevo(s) y se actualizarán{' '}
            {preview.existing_records}. La operación es transaccional: si algo falla, la base de
            datos queda intacta.
          </p>
          <div className="row">
            <button className="btn" disabled={busy} onClick={() => void runImport()}>
              {busy ? 'Importando…' : 'IMPORTAR DATOS'}
            </button>
            <button className="btn ghost" onClick={() => setStep(3)}>Volver a revisar</button>
          </div>
        </div>
      )}

      {/* ---------------- Paso 5: resultado ---------------- */}
      {step === 5 && result && (
        <div className="card">
          <h2 style={{ color: 'var(--success)' }}>✓ {result.message}</h2>
          <div className="file-meta mt">
            <div className="item"><div className="k">Registros nuevos</div><div className="v">{result.records_inserted}</div></div>
            <div className="item"><div className="k">Registros actualizados</div><div className="v">{result.records_updated}</div></div>
            <div className="item"><div className="k">Filas ignoradas</div><div className="v">{result.records_ignored}</div></div>
            <div className="item"><div className="k">Consumo procesado</div><div className="v">{formatKwh(result.total_kwh)}</div></div>
            {result.date_from && (
              <div className="item"><div className="k">Periodo</div>
                <div className="v">{formatDate(result.date_from)} – {formatDate(result.date_to)}</div></div>
            )}
          </div>
          {result.total_kwh > 0 && (
            <p className="small muted">
              El costo estimado se calculará automáticamente con las tarifas configuradas
              en el módulo Tarifas (cada día usa su tarifa vigente).
            </p>
          )}
          <div className="row">
            <button className="btn" onClick={reset}>Importar otro archivo</button>
          </div>
        </div>
      )}

      {/* ---------------- Historial de importaciones ---------------- */}
      <div className="card">
        <h2>Historial de importaciones</h2>
        {loadingHistory ? (
          <Spinner text="Cargando historial…" />
        ) : history.length === 0 ? (
          <p className="muted">Aún no se han realizado importaciones.</p>
        ) : (
          <div className="table-wrap mt">
            <table>
              <thead>
                <tr>
                  <th>Fecha</th><th>Dispositivo</th><th>Archivo</th>
                  <th className="num">Nuevos</th><th className="num">Actualizados</th>
                  <th className="num">Ignorados</th><th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id}>
                    <td>{formatDateTime(item.imported_at)}</td>
                    <td>{item.device_name ?? '—'}</td>
                    <td>{item.filename}</td>
                    <td className="num">{item.records_inserted}</td>
                    <td className="num">{item.records_updated}</td>
                    <td className="num">{item.records_ignored}</td>
                    <td>
                      <span className={`badge ${item.status === 'success' ? 'ok' : 'warn'}`}>
                        {item.status === 'success' ? 'Exitosa' : 'Con errores'}
                      </span>
                      {item.error_summary && (
                        <div className="small muted">{item.error_summary}</div>
                      )}
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
