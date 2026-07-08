import type { HTMLAttributes, ReactNode } from 'react'

type DivProps = HTMLAttributes<HTMLDivElement> & { children?: ReactNode }

export function Card({ children, className = '', ...rest }: DivProps) {
  return (
    <div className={`ui-card ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
export function CardHeader({ children, className = '', ...rest }: DivProps) {
  return (
    <div className={`ui-card__header ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
export function CardBody({ children, className = '', ...rest }: DivProps) {
  return (
    <div className={`ui-card__body ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
export function CardFooter({ children, className = '', ...rest }: DivProps) {
  return (
    <div className={`ui-card__footer ${className}`.trim()} {...rest}>
      {children}
    </div>
  )
}
