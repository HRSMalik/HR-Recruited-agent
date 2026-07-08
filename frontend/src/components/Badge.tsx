import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

export type BadgeVariant = 'strong' | 'yes' | 'review' | 'no' | 'neutral'

export function Badge({
  variant = 'neutral',
  icon,
  children,
}: {
  variant?: BadgeVariant
  icon?: IconName
  children: ReactNode
}) {
  return (
    <span className={`ui-badge ui-badge--${variant}`}>
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  )
}
