import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  children,
  className = '',
  ...rest
}: {
  variant?: Variant
  size?: 'sm' | 'md'
  icon?: IconName
  children?: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = ['ui-btn', `ui-btn--${variant}`, size === 'sm' ? 'ui-btn--sm' : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <button className={cls} {...rest}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  )
}
