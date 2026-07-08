import type { ReactNode } from 'react'

export function PageBanner({
  title,
  subtitle,
  actions,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <div className="ui-page-banner">
      <div>
        <h1 className="ui-page-banner__title">{title}</h1>
        {subtitle && <div className="ui-page-banner__sub">{subtitle}</div>}
      </div>
      {actions && <div className="ui-page-banner__actions">{actions}</div>}
    </div>
  )
}

export function SectionHeader({
  title,
  subtitle,
  right,
}: {
  title: string
  subtitle?: string
  right?: ReactNode
}) {
  return (
    <div className="ui-section-header">
      <div>
        <div className="ui-section-header__title">{title}</div>
        {subtitle && <div className="ui-section-header__sub">{subtitle}</div>}
      </div>
      {right}
    </div>
  )
}
