// Cliente HTTP central de la API.
// - Errores con mensajes claros para el usuario (sección 46).
// - Soporta errores de validación de importación con detalle por fila.

export class ApiError extends Error {
  status: number
  errors: { row: number | null; field: string | null; value: string | null; message: string }[]

  constructor(status: number, detail: string, errors: ApiError['errors'] = []) {
    super(detail)
    this.status = status
    this.errors = errors
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return undefined as T
    return (await parseBody(response)) as T
  }
  const body = (await parseBody(response)) as { detail?: string; errors?: ApiError['errors'] } | null
  const detail =
    typeof body?.detail === 'string'
      ? body.detail
      : response.status === 404
        ? 'No se encontró el recurso solicitado.'
        : response.status === 413
          ? 'El archivo es demasiado grande.'
          : `Error ${response.status}: no se pudo completar la operación.`
  throw new ApiError(response.status, detail, body?.errors ?? [])
}

function buildUrl(path: string, params?: Record<string, string | number | undefined | null>): string {
  const url = new URL(path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }
  return url.pathname + (url.search || '')
}

export const api = {
  async get<T>(path: string, params?: Record<string, string | number | undefined | null>): Promise<T> {
    const response = await fetch(buildUrl(path, params), { headers: { Accept: 'application/json' } })
    return handleResponse<T>(response)
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    return handleResponse<T>(response)
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
    return handleResponse<T>(response)
  },

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(buildUrl(path), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
    return handleResponse<T>(response)
  },

  async delete(path: string): Promise<void> {
    const response = await fetch(buildUrl(path), { method: 'DELETE' })
    return handleResponse<void>(response)
  },

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const response = await fetch(buildUrl(path), { method: 'POST', body: formData })
    return handleResponse<T>(response)
  },

  async download(path: string, init?: RequestInit): Promise<{ blob: Blob; filename: string }> {
    const response = await fetch(buildUrl(path), init)
    if (!response.ok) await handleResponse(response)
    const blob = await response.blob()
    const disposition = response.headers.get('Content-Disposition') || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    return { blob, filename: match ? match[1] : 'descarga' }
  },
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
