import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

type Variant = 'info' | 'success' | 'warning' | 'danger'
const ICON: Record<Variant, IconName> = {
  info: 'info',
  success: 'check',
  warning: 'alert',
  danger: 'alert',
}

export function AlertBanner({
  variant = 'info',
  children,
}: {
  variant?: Variant
  children: ReactNode
}) {
  return (
    <div className={`ui-alert ui-alert--${variant}`} role={variant === 'danger' ? 'alert' : 'status'}>
      <Icon name={ICON[variant]} />
      <div>{children}</div>
    </div>
  )
}
