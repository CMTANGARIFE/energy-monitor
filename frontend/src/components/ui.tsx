import type { ReactNode } from 'react'

export function PageHeader({ title, subtitle, actions }: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  )
}

export function StatCard({ label, value, sub, tone }: {
  label: string
  value: ReactNode
  sub?: ReactNode
  tone?: 'default' | 'amber'
}) {
  return (
    <div className={`stat-card${tone === 'amber' ? ' amber' : ''}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}

export function Spinner({ text = 'Cargando…' }: { text?: string }) {
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      {text}
    </div>
  )
}

export function ErrorAlert({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <div className="alert error" role="alert">
      <strong>{message}</strong>
      {children}
    </div>
  )
}

export function WarningAlert({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="alert warning" role="alert">
      <strong>{title}</strong>
      {children}
    </div>
  )
}

export function InfoAlert({ children }: { children: ReactNode }) {
  return (
    <div className="alert info">{children}</div>
  )
}

export function EmptyState({ title, description, action }: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <img src="/assets/default-device.png" alt="" aria-hidden="true" />
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}
